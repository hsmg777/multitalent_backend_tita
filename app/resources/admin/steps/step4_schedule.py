# app/resources/admin/steps/step4_interview.py
from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from marshmallow import ValidationError, Schema, fields
from sqlalchemy import text, select
from sqlalchemy.orm import selectinload
from app.services.postulation_service import transition_to

from app.ext.db import db
from app.models.admin.interview import Interview
from app.models.admin.skill_grade import SkillGrade
from app.models.web_portal.postulation import Postulation

from ....schemas.admin.skill import SkillCompactSchema
from app.schemas.admin.interview import InterviewCreateSchema, InterviewSchema
from app.schemas.admin.skill_grade import SkillGradeCreateSchema, SkillGradeSchema
from ....schemas.web_portal.postulation import PostulationStatusSchema

blp = Blueprint(
    "AdminStep4Interview",
    __name__,
    description="Admin: Step 4 - Agendar entrevista técnica y calificar skills"
)

# --------------------- Helpers ---------------------

def _load_postulation_or_404(pid: int) -> Postulation:
    p = db.session.get(Postulation, pid)
    if not p:
        abort(404, message="Postulación no encontrada")
    return p

def _ensure_status_for_schedule(p: Postulation) -> None:
    if (p.status or "").lower() not in ("interview_scheduled",):
        abort(400, message="La postulación no está en estado 'interview_scheduled'.")

def _allowed_skill_ids_for_postulation(p: Postulation) -> set[int]:
    # FIX: tabla correcta: vacancy_skills (sin 'es')
    q = text("SELECT skill_id FROM vacancy_skills WHERE vacancy_id = :vid")
    rows = db.session.execute(q, {"vid": p.vacancy_id}).fetchall()
    return {r[0] for r in rows}

def _get_or_create_interview_for_postulation(pid: int) -> Interview:
    itv = db.session.execute(
        select(Interview).where(Interview.postulation_id == pid)
    ).scalar_one_or_none()
    if itv:
        return itv
    itv = Interview(postulation_id=pid)
    db.session.add(itv)
    return itv

def _get_interview_or_404(pid: int) -> Interview:
    itv = db.session.execute(
        select(Interview)
        .options(selectinload(Interview.skill_grades))
        .where(Interview.postulation_id == pid)
    ).scalar_one_or_none()
    if not itv:
        abort(404, message="No hay entrevista agendada para esta postulación.")
    return itv

# --------------------- Rutas ---------------------

@blp.route("interview/<int:pid>", methods=["GET"])
class GetInterview(MethodView):
    @jwt_required()
    @blp.response(200, InterviewSchema)
    def get(self, pid: int):
        itv = db.session.execute(
            select(Interview)
            .options(selectinload(Interview.skill_grades))
            .where(Interview.postulation_id == pid)
        ).scalar_one_or_none()
        if not itv:
            abort(404, message="No hay entrevista agendada para esta postulación.")
        return itv

@blp.route("interview/<int:pid>/schedule", methods=["POST"])
class ScheduleInterview(MethodView):
    @jwt_required()
    @blp.arguments(InterviewCreateSchema)
    @blp.response(200, InterviewSchema)
    def post(self, payload: dict, pid: int):
        p = _load_postulation_or_404(pid)
        _ensure_status_for_schedule(p)

        itv = _get_or_create_interview_for_postulation(pid)
        itv.starts_at = payload["starts_at"]
        itv.modality  = payload.get("modality")
        itv.location  = payload.get("location")
        itv.meet_url  = payload.get("meet_url")

        db.session.commit()
        db.session.refresh(itv)
        itv = _get_interview_or_404(pid)
        return itv

@blp.route("interview/<int:pid>/grades", methods=["POST"])
class UpsertOneGrade(MethodView):
    @jwt_required()
    @blp.arguments(SkillGradeCreateSchema)
    @blp.response(200, SkillGradeSchema)
    def post(self, payload: dict, pid: int):
        p = _load_postulation_or_404(pid)
        _ensure_status_for_schedule(p)

        itv = _get_interview_or_404(pid)

        skill_id = payload["skill_id"]
        score = payload["score"]

        allowed = _allowed_skill_ids_for_postulation(p)
        if skill_id not in allowed:
            abort(400, message="La skill no pertenece a la vacante de esta postulación.")

        sg = db.session.execute(
            select(SkillGrade).where(
                SkillGrade.interview_id == itv.id,
                SkillGrade.skill_id == skill_id,
            )
        ).scalar_one_or_none()

        if sg:
            sg.score = score
        else:
            sg = SkillGrade(interview_id=itv.id, skill_id=skill_id, score=score)
            db.session.add(sg)

        db.session.commit()
        db.session.refresh(sg)
        return sg

class GradesBulkSchema(Schema):
    grades = fields.List(fields.Nested(SkillGradeCreateSchema), required=True)

class GradesBulkResponseSchema(Schema):
    updated = fields.Int()
    items = fields.List(fields.Nested(SkillGradeSchema))

@blp.route("interview/<int:pid>/grades/bulk", methods=["POST"])
class UpsertGradesBulk(MethodView):
    @jwt_required()
    @blp.arguments(GradesBulkSchema)
    @blp.response(200, GradesBulkResponseSchema)
    def post(self, payload: dict, pid: int):
        p = _load_postulation_or_404(pid)
        _ensure_status_for_schedule(p)

        itv = _get_interview_or_404(pid)
        allowed = _allowed_skill_ids_for_postulation(p)

        items_out = []
        updated_count = 0

        for item in payload["grades"]:
            skill_id = item["skill_id"]
            score = item["score"]

            if skill_id not in allowed:
                abort(400, message=f"La skill {skill_id} no pertenece a la vacante de esta postulación.")

            sg = db.session.execute(
                select(SkillGrade).where(
                    SkillGrade.interview_id == itv.id,
                    SkillGrade.skill_id == skill_id,
                )
            ).scalar_one_or_none()

            if sg:
                sg.score = score
            else:
                sg = SkillGrade(interview_id=itv.id, skill_id=skill_id, score=score)
                db.session.add(sg)

            items_out.append(sg)
            updated_count += 1

        db.session.commit()
        for sg in items_out:
            db.session.refresh(sg)

        return {"updated": updated_count, "items": items_out}

class NotesSchema(Schema):
    notes = fields.Str(allow_none=True)

@blp.route("interview/<int:pid>/notes", methods=["PATCH"])
class UpdateInterviewNotes(MethodView):
    @jwt_required()
    @blp.arguments(NotesSchema)
    @blp.response(200, InterviewSchema)
    def patch(self, payload: dict, pid: int):
        p = _load_postulation_or_404(pid)
        _ensure_status_for_schedule(p)

        itv = _get_interview_or_404(pid)
        itv.notes = payload.get("notes")

        db.session.commit()
        db.session.refresh(itv)
        itv = _get_interview_or_404(pid)
        return itv

@blp.route("interview/<int:pid>/allowed-skills", methods=["GET"])
class AllowedSkillsForPostulation(MethodView):
    @jwt_required()
    @blp.response(200, SkillCompactSchema(many=True))
    def get(self, pid: int):
        p = _load_postulation_or_404(pid)

        # FIX: tabla correcta: postulations (plural)
        rows = db.session.execute(text("""
            SELECT s.id, s.nombre
            FROM postulation p
            INNER JOIN vacancies v       ON v.id = p.vacancy_id
            INNER JOIN vacancy_skills vs ON vs.vacancy_id = v.id
            INNER JOIN skills s          ON s.id = vs.skill_id
            WHERE p.id = :pid
            ORDER BY s.nombre
        """), {"pid": p.id}).mappings().all()

        return [{"id": r["id"], "nombre": r["nombre"]} for r in rows]
    

@blp.route("interview/<int:pid>/complete", methods=["POST"])
class CompleteStep4(MethodView):
    """
    Valida que haya entrevista y al menos 1 calificación,
    y transiciona la postulación a 'selection_pending'.
    """
    @jwt_required()
    @blp.response(200, PostulationStatusSchema)
    def post(self, pid: int):
        p = _load_postulation_or_404(pid)
        # Debe venir desde interview_scheduled
        _ensure_status_for_schedule(p)

        # Debe existir entrevista con al menos 1 calificación
        itv = db.session.execute(
            select(Interview)
            .options(selectinload(Interview.skill_grades))
            .where(Interview.postulation_id == pid)
        ).scalar_one_or_none()
        if not itv:
            abort(400, message="Primero agenda la entrevista.")
        if not itv.skill_grades or len(itv.skill_grades) == 0:
            abort(400, message="Registra al menos una calificación antes de continuar.")

        # Transición
        transition_to(p, "selection_pending", send_email=False)

        return {"id": p.id, "status": p.status}
