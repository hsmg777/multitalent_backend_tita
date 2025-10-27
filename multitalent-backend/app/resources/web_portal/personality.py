# app/resources/web_portal/personality.py
from datetime import datetime
from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import current_app
from marshmallow import Schema, fields, validate
from app.ext.db import db
from app.models.web_portal.postulation import Postulation
from app.models.personality.attempt import PersonalityAttempt
from app.schemas.personality.personality import (
    AnswersPayloadSchema,
    OptionSchema,
    QuestionSchema,
    BootstrapWithQuestionsSchema, 
    OkSchema

)
from app.services.personality.attempt_service import PersonalityAttemptService
from app.services.personality.questions import QUESTIONS
from app.services.postulation_service import transition_to

blp = Blueprint(
    "WebPortalPersonality",
    __name__,
    description="Examen de personalidad para Applicants (bootstrap/answer/finish)",
)



def _get_my_postulation_or_403(pid: int, applicant_id: int) -> Postulation:
    p = Postulation.query.get(pid)
    if not p:
        abort(404, message="Postulación no encontrada")
    if p.applicant_id != applicant_id:
        abort(403, message="No autorizado")
    return p

def _require_ready_status(p: Postulation) -> None:
    if (p.status or "").lower() != "personality_test_ready":
        abort(400, message="La prueba de personalidad no está habilitada para esta postulación.")

def _validate_answers_payload(payload: dict) -> list[dict]:
    """
    Espera 4 respuestas por pregunta con subcódigos "Qnn_A".."Qnn_D".
    Valida que por cada Qnn, los valores sean una permutación exacta {1,2,3,4}.
    """
    answers = payload.get("answers") or []
    if not isinstance(answers, list) or not answers:
        abort(400, message="Debes enviar 'answers' como lista con al menos un ítem.")

    valid_qcodes = {q["code"] for q in QUESTIONS}
    per_question: dict[str, dict[str, int]] = {}  

    cleaned: list[dict] = []
    for item in answers:
        try:
            qcode_full = str(item["question_code"]).strip()  
            val = int(item["option_value"])
        except Exception:
            abort(400, message="Cada answer debe tener 'question_code' (str) y 'option_value' (int).")

        if "_" not in qcode_full or len(qcode_full.split("_")) != 2:
            abort(400, message=f"Formato de 'question_code' inválido: {qcode_full} (usa Qnn_A..D)")
        qbase, letter = qcode_full.split("_")
        letter = letter.upper()
        if qbase not in valid_qcodes:
            abort(400, message=f"Pregunta inválida: {qbase}")
        if letter not in ("A", "B", "C", "D"):
            abort(400, message=f"Letra inválida en {qcode_full} (usa A/B/C/D)")

        if val < 1 or val > 4:
            abort(400, message=f"Respuesta fuera de rango (1..4) en {qcode_full}")

        per_question.setdefault(qbase, {})
        if letter in per_question[qbase]:
            abort(400, message=f"Letra duplicada en {qbase}: {letter}")
        per_question[qbase][letter] = val

        cleaned.append({"question_code": qcode_full, "option_value": val})

    for qbase, mapping in per_question.items():
        if set(mapping.keys()) != {"A", "B", "C", "D"}:
            faltan = {"A","B","C","D"} - set(mapping.keys())
            abort(400, message=f"Faltan letras en {qbase}: {', '.join(sorted(faltan))}")
        valores = set(mapping.values())
        if valores != {1, 2, 3, 4}:
            abort(400, message=f"Los valores en {qbase} deben ser 1,2,3 y 4 sin repetirse.")

    return cleaned


# ===================================== Rutas =====================================

@blp.route("/postulations/<int:pid>/personality/bootstrap", methods=["GET"])
class Bootstrap(MethodView):
    @jwt_required()
    @blp.response(200, BootstrapWithQuestionsSchema)
    def get(self, pid: int):
        applicant_id = int(get_jwt_identity())
        p = _get_my_postulation_or_403(pid, applicant_id)
        _require_ready_status(p)

        time_limit = current_app.config.get("PERSONALITY_TIME_LIMIT_SEC", 1800)
        svc = PersonalityAttemptService()
        data = svc.bootstrap(postulation=p, default_time_limit_sec=time_limit)

        return {**data, "questions": QUESTIONS}

@blp.route("/postulations/<int:pid>/personality/answer", methods=["POST"])
class SaveAnswers(MethodView):
    @jwt_required()
    @blp.arguments(AnswersPayloadSchema)
    def post(self, payload: dict, pid: int):
        applicant_id = int(get_jwt_identity())
        p = _get_my_postulation_or_403(pid, applicant_id)
        _require_ready_status(p)

        attempt = PersonalityAttempt.query.filter_by(postulation_id=p.id).one_or_none()
        if not attempt:
            abort(400, message="No hay intento iniciado. Llama a /bootstrap primero.")
        if attempt.status in ("finished", "expired", "canceled"):
            abort(409, message=f"El intento ya no acepta respuestas (status={attempt.status}).")

        now = datetime.utcnow()
        if attempt.expires_at and now >= attempt.expires_at:
            attempt.status = "expired"
            attempt.finished_at = now
            if attempt.started_at:
                attempt.duration_sec = int((now - attempt.started_at).total_seconds())
            db.session.commit()
            abort(409, message="El tiempo del examen expiró.")

        cleaned = _validate_answers_payload(payload)
        svc = PersonalityAttemptService()
        svc.save_answers(attempt_id=attempt.id, answers=cleaned)
        return {"ok": True, "message": "Respuestas guardadas."}, 200

@blp.route("/postulations/<int:pid>/personality/finish", methods=["POST"])
class Finish(MethodView):
    @jwt_required()
    @blp.response(200, OkSchema)  
    def post(self, pid: int):
        applicant_id = int(get_jwt_identity())
        p = _get_my_postulation_or_403(pid, applicant_id)
        _require_ready_status(p)

        attempt = PersonalityAttempt.query.filter_by(postulation_id=p.id).one_or_none()
        if not attempt:
            abort(400, message="No hay intento iniciado. Llama a /bootstrap primero.")

        svc = PersonalityAttemptService()
        svc.finish(attempt_id=attempt.id)  

        if current_app.config.get("AUTO_TRANSITION_ON_FINISH", True):
            try:
                transition_to(p, "interview_scheduled", send_email=False)
            except Exception as ex:
                current_app.logger.warning("transition_to fallo: %s", ex)

        return {"ok": True, "message": "Prueba finalizada correctamente."}, 200


