# app/resources/ai_scoring.py
from __future__ import annotations

from flask_smorest import Blueprint
from flask.views import MethodView
from flask import current_app
import os, requests, logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any
from datetime import datetime

from app.ext.db import db
from app.ext.pdf_reader import extract_text_from_pdf
from app.ext.ai_scorer import (
    summarize_cv_to_json,
    score_candidate_v3,    
    score_candidate_v2,    
    score_candidate,     
)
from app.models.postulation_ai_result import PostulationAIResult
from app.schemas.web_portal.postulation_ai_result import PostulationAIResultSchema

logger = logging.getLogger(__name__)

blp = Blueprint(
    "AIPostulation",
    __name__,
    url_prefix="/ai/postulations",
    description="Consulta de resultados IA (solo lectura)",
)

_executor = ThreadPoolExecutor(max_workers=4)


def trigger_scoring_async(payload: Dict[str, Any]) -> None:
    """
    Encola el scoring en background (no bloquea la petición HTTP) con app context.
    La lógica de negocio y persistencia está en _process_payload().
    """
    app = current_app._get_current_object()

    def job():
        with app.app_context():
            try:
                _process_payload(payload)
                db.session.remove()
            except Exception:
                db.session.remove()
                raise

    _executor.submit(job)
    logger.info("[AI] scoring encolado postulation_id=%s", payload.get("postulation_id"))


def trigger_scoring_sync(payload: Dict[str, Any]) -> None:
    """
    Ejecuta el scoring en este hilo (bloqueante) con app context.
    Útil para pruebas o ejecuciones programadas.
    """
    app = current_app._get_current_object()
    with app.app_context():
        _process_payload(payload)
        db.session.remove()


def _process_payload(data: dict):
    """
    Orquesta:
      1) Descarga/lee el CV y extrae texto.
      2) Pin-Pon: resume a JSON estructurado SOLO con evidencia del CV.
      3) Scoring v3 usando applicant_profile + vacancy_profile + CV_JSON.
      4) Fallbacks: v2 (si faltan perfiles) o legacy (si hay 'position' + lists).
      5) Persiste PostulationAIResult.
    """
    postulation_id = data.get("postulation_id")
    vacancy_id = data.get("vacancy_id")
    logger.info("[AI] procesando postulation_id=%s vacancy_id=%s", postulation_id, vacancy_id)

    cv = data.get("cv") or {}

    try:
        # 1) Extraer texto CV
        text = _fetch_cv_text(cv)
        logger.info("[AI] CV extraído len=%s postulation_id=%s", len(text or ""), postulation_id)

        # 2) Paso Pin-Pon 1: Resumen estructurado (solo evidencia del PDF)
        cv_json = summarize_cv_to_json(text)
        logger.info("[AI] CV JSON listo (keys=%s) postulation_id=%s", list(cv_json.keys()), postulation_id)

        # 3) Elegir scoring según disponibilidad de perfiles
        applicant_profile = data.get("applicant_profile")
        vacancy_profile   = data.get("vacancy_profile")

        if isinstance(applicant_profile, dict) and isinstance(vacancy_profile, dict):
            # v3 (Pin-Pon): usa JSON del CV como fuente de verdad
            result = score_candidate_v3(applicant_profile, vacancy_profile, cv_json)
            logger.info("[AI] v3 OK postulation_id=%s score=%s", postulation_id, result.get("score"))
        elif isinstance(applicant_profile, dict) or isinstance(vacancy_profile, dict):
            # Si solo hay un perfil, v2 con texto crudo (mantener compatibilidad)
            result = score_candidate_v2(applicant_profile or {}, vacancy_profile or {}, text)
            logger.info("[AI] v2 (perfil incompleto) OK postulation_id=%s score=%s", postulation_id, result.get("score"))
        else:
            # Legacy: posición + skills si existen; de lo contrario, v2 con texto crudo
            position         = data.get("position")
            required_skills  = data.get("required_skills", [])
            nice_to_haves    = data.get("nice_to_haves", [])
            min_years        = data.get("min_years_experience", 0)
            applicant_legacy = data.get("applicant", {})

            if position:
                result = score_candidate(position, required_skills, nice_to_haves, min_years, applicant_legacy, text)
                logger.info("[AI] legacy OK postulation_id=%s score=%s", postulation_id, result.get("score"))
            else:
                result = score_candidate_v2({}, {}, text)
                logger.info("[AI] v2 (sin perfiles) OK postulation_id=%s score=%s", postulation_id, result.get("score"))

        # 4) Persistir resultado
        row = PostulationAIResult(
            postulation_id=postulation_id,
            vacancy_id=vacancy_id,
            score=result.get("score"),
            feedback=result.get("feedback"),
            created_at=datetime.utcnow(),
        )
        db.session.add(row)
        db.session.commit()
        logger.info("[AI] guardado OK postulation_id=%s id=%s", postulation_id, row.id)

    except Exception as e:
        db.session.rollback()
        logger.exception("[AI] error scoring postulation_id=%s", postulation_id)
        # Guardar un registro de error (útil para el panel)
        try:
            row = PostulationAIResult(
                postulation_id=postulation_id,
                vacancy_id=vacancy_id,
                score=0,
                feedback=f"Error: {str(e)}",
                created_at=datetime.utcnow(),
            )
            db.session.add(row)
            db.session.commit()
            logger.info("[AI] error registrado en BD postulation_id=%s id=%s", postulation_id, row.id)
        except Exception:
            db.session.rollback()
            logger.exception("[AI] error al registrar el error postulation_id=%s", postulation_id)


def _fetch_cv_text(cv: dict) -> str:
    """
    Soporta lectura por presigned URL (storage='url', presigned_url)
    o descarga directa desde S3 (storage='s3', s3_bucket, s3_key).
    """
    presigned = cv.get("presigned_url")
    if presigned:
        r = requests.get(presigned, timeout=60)
        r.raise_for_status()
        tmp = "/tmp/cv.pdf"
        with open(tmp, "wb") as f:
            f.write(r.content)
        return extract_text_from_pdf(tmp)

    if cv.get("storage") == "s3":
        import boto3
        s3 = boto3.client(
            "s3",
            region_name=os.getenv("AWS_DEFAULT_REGION"),
            aws_access_key_id=os.getenv("AWS_KEY"),
            aws_secret_access_key=os.getenv("AWS_SECRET"),
        )
        tmp = "/tmp/cv.pdf"
        bucket = cv.get("s3_bucket") or os.getenv("AWS_BUCKET")
        if not bucket:
            raise RuntimeError("Falta 's3_bucket' o AWS_BUCKET")
        key = cv.get("s3_key")
        if not key:
            raise RuntimeError("Falta 's3_key'")
        s3.download_file(bucket, key, tmp)
        return extract_text_from_pdf(tmp)

    raise RuntimeError("No se pudo obtener el CV (falta presigned_url o s3_key).")


# ---------- Endpoint de lectura de resultados ----------
@blp.route("/<int:postulation_id>/result")
class AIPostulationResult(MethodView):
    @blp.response(200, PostulationAIResultSchema)
    def get(self, postulation_id):
        """
        Devuelve el último resultado de scoring para una postulación.
        Si no existe, responde estado 'pending'.
        """
        row = PostulationAIResult.query.filter_by(postulation_id=postulation_id).first()
        if not row:
            return {"postulation_id": postulation_id, "vacancy_id": None, "score": None, "feedback": "pending"}, 200
        return row
