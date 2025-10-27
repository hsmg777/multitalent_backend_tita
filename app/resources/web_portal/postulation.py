# app/resources/web_portal/postulation.py
import os
from datetime import datetime
import datetime as _dt
from decimal import Decimal
import logging

from flask import request
from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError

from ...ext.db import db
from ...ext.s3 import delete_cv_key, extract_key_from_cv_path, make_presigned_url
from ...models.web_portal.postulation import Postulation
from ...models.admin.vacancy import Vacancy
from ...schemas.web_portal.postulation import (
    PostulationCreateSchema,
    PostulationUpdateSchema,
    PostulationSchema,
    PostulationWithVacancySchema,
)
from app.resources.ai_scoring import trigger_scoring_async

logger = logging.getLogger(__name__)

blp = Blueprint("Postulations", __name__, description="CRUD de postulaciones (Applicant)")

# ----------------------- Utils -----------------------
def _to_jsonable(x):
    if isinstance(x, Decimal):
        return int(x) if x == int(x) else float(x)
    if isinstance(x, (_dt.datetime, _dt.date)):
        return x.isoformat()
    if isinstance(x, dict):
        return {k: _to_jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, set)):
        return [_to_jsonable(v) for v in x]
    return x


# ----------------------- Collection -----------------------
@blp.route("/postulations")
class PostulationCollection(MethodView):
    @blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    @blp.arguments(PostulationCreateSchema, location="json")
    @blp.response(201, PostulationSchema)
    def post(self, payload):
        applicant_id = int(get_jwt_identity())
        vacancy_id = payload["vacancy_id"]

        vac = Vacancy.query.get_or_404(vacancy_id)
        if not vac.is_active or vac.status not in ("published",):
            abort(400, message="La vacante no está disponible para postulación.")
        if vac.publish_at and datetime.utcnow() < vac.publish_at:
            abort(400, message="La postulación aún no está habilitada para esta vacante.")
        if datetime.utcnow().date() > vac.apply_until:
            abort(400, message="La vacante ya no acepta postulaciones (fuera de fecha).")

        exists = Postulation.query.filter(
            and_(Postulation.applicant_id == applicant_id, Postulation.vacancy_id == vacancy_id)
        ).first()
        if exists:
            abort(409, message="Ya has postulado a esta vacante.")

        post = Postulation(
            applicant_id=applicant_id,
            vacancy_id=vacancy_id,
            residence_addr=payload.get("residence_addr"),
            credential=payload.get("credential"),
            number=payload.get("number"),
            age=payload.get("age"),
            role_exp_years=payload.get("role_exp_years"),
            expected_salary=payload.get("expected_salary"),
            cv_path=payload["cv_path"],
            status=payload.get("status") or "submitted",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        try:
            db.session.add(post)
            db.session.commit()

            try:
                logger.info("[AI] Preparando scoring para postulation_id=%s vacancy_id=%s", post.id, post.vacancy_id)
                cv_key = post.cv_path
                try:
                    presigned = make_presigned_url(cv_key, expires_seconds=1200)
                    cv_payload = {"storage": "url", "presigned_url": presigned}
                except Exception:
                    cv_payload = {"storage": "s3", "s3_bucket": os.getenv("AWS_BUCKET"), "s3_key": cv_key}

                applicant_profile = {
                    "residence_addr": post.residence_addr,
                    "age": post.age,
                    "role_exp_years": post.role_exp_years,
                    "expected_salary": post.expected_salary,
                    "name": None, "email": None, "phone": post.number, "credential": post.credential,
                }
                vacancy_profile = {
                    "location": getattr(vac, "location", None),
                    "modality": getattr(vac, "modality", None),
                    "role_objective": getattr(vac, "role_objective", None),
                    "responsibilities": getattr(vac, "responsibilities", None),
                    "req_education": getattr(vac, "req_education", None),
                    "req_experience": getattr(vac, "req_experience", None),
                    "req_knowledge": getattr(vac, "req_knowledge", None),
                    "charge_title": getattr(vac, "title", None),
                    "charge_description": getattr(vac, "description", None),
                    "charge_area": getattr(vac, "area", None),
                }
                trigger_scoring_async(_to_jsonable({
                    "postulation_id": post.id,
                    "vacancy_id": post.vacancy_id,
                    "position": vacancy_profile["charge_title"] or getattr(vac, "title", None),
                    "cv": cv_payload,
                    "applicant_profile": applicant_profile,
                    "vacancy_profile": vacancy_profile,
                }))
                logger.info("[AI] scoring interno encolado postulation_id=%s", post.id)
            except Exception as e:
                logger.exception("[AI] Error al preparar/enviar scoring: %s", e)

        except IntegrityError:
            db.session.rollback()
            abort(409, message="Ya existe una postulación para esta vacante.")

        return post

    @blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    @blp.response(200, PostulationWithVacancySchema(many=True))
    def get(self):
        """Listar las postulaciones del usuario autenticado (con datos básicos de la vacante)."""
        applicant_id = int(get_jwt_identity())
        page = max(int(request.args.get("page", 1) or 1), 1)
        per_page = min(max(int(request.args.get("per_page", 20) or 20), 1), 100)

        q = (Postulation.query
            .filter_by(applicant_id=applicant_id)
            .order_by(Postulation.created_at.desc())
            .join(Vacancy)
            .add_entity(Vacancy))

        items = q.paginate(page=page, per_page=per_page, error_out=False).items
        results = []
        for post, vac in items:
            results.append({
                "id": post.id,
                "vacancy_id": post.vacancy_id, 
                "status": post.status,
                "created_at": post.created_at,
                "updated_at": post.updated_at,
                "vacancy": {
                    "id": vac.id,
                    "title": vac.title,
                    "location": vac.location,
                    "modality": vac.modality,
                }
            })
        return results


# ----------------------- Item (Applicant) -----------------------
@blp.route("/postulations/<int:postulation_id>")
class PostulationItem(MethodView):
    @blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    @blp.response(200, PostulationSchema)
    def get(self, postulation_id: int):
        applicant_id = int(get_jwt_identity())
        post = Postulation.query.get_or_404(postulation_id)
        if post.applicant_id != applicant_id:
            abort(403, message="No autorizado.")
        return post

    @blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    @blp.arguments(PostulationUpdateSchema, location="json")
    @blp.response(200, PostulationSchema)
    def patch(self, payload, postulation_id: int):
        post = Postulation.query.get_or_404(postulation_id)
        editable = {"residence_addr", "age", "role_exp_years", "expected_salary", "cv_path", "status", "number", "credential"}
        for k, v in payload.items():
            if k in editable:
                setattr(post, k, v)
        post.updated_at = datetime.utcnow()
        db.session.commit()
        return post

    @blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    @blp.response(204)
    def delete(self, postulation_id: int):
        applicant_id = int(get_jwt_identity())
        post = Postulation.query.get_or_404(postulation_id)
        if post.applicant_id != applicant_id:
            abort(403, message="No autorizado.")
        cv_key = extract_key_from_cv_path(post.cv_path)
        db.session.delete(post)
        db.session.commit()
        if cv_key and cv_key.startswith("curriculums/"):
            delete_cv_key(cv_key)
        return "", 204


# ----------------------- Helper: ya postulé -----------------------
@blp.route("/postulations/by-vacancy/<int:vacancy_id>/me")
class PostulationByVacancyMe(MethodView):
    @blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    @blp.response(200, PostulationSchema)
    def get(self, vacancy_id: int):
        applicant_id = int(get_jwt_identity())
        post = Postulation.query.filter_by(applicant_id=applicant_id, vacancy_id=vacancy_id).first()
        if not post:
            abort(404, message="No has postulado a esta vacante.")
        return post
