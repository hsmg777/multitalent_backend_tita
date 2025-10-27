# app/resources/web_portal/postulation_process.py
from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import select

from ...ext.db import db
from ...models.web_portal.postulation import Postulation
from ...models.admin.vacancy import Vacancy
from ...models.admin.interview import Interview
from ...schemas.web_portal.postulation_process import PostulationProcessSchema

blp = Blueprint(
    "PostulationProcess",
    __name__,
    description="Proceso de selección (Applicant)"
)

# Etiquetas en español (incluye variantes solo para mostrar el label correcto si llegan)
STATUS_LABELS_ES = {
    "submitted": "Postulación enviada",
    "accepted": "Aceptada por RR. HH.",
    "prescreen_call": "Llamada de preselección",
    "personality_test_ready": "Prueba de personalidad",
    "interview_scheduled": "Entrevista agendada",
    "selection_pending": "En revisión final",
    "hired": "Contratado",
    "rejected": "Rechazado",
    "cancelled": "Cancelado",
    "canceled": "Cancelado",
    "not_selected": "No seleccionado",
    "no_continues": "No continúa",
}

# Flujo REAL (8 pasos)
BASE_FLOW = [
    "submitted",
    "accepted",
    "prescreen_call",
    "personality_test_ready",
    "interview_scheduled",
    "selection_pending",
    "hired",
    "rejected",   # ← paso terminal único (placeholder)
]

# Variantes que mapean a "rejected" en el timeline
CANCEL_VARIANTS = {"cancelled", "canceled", "not_selected", "no_continues"}


def _get_reason_from_postulation(postulation: Postulation) -> str | None:
    return (
        getattr(postulation, "status_reason", None)
        or getattr(postulation, "cancel_reason", None)
        or getattr(postulation, "rejection_reason", None)
        or None
    )


def _build_steps(postulation: Postulation, interview: Interview | None):
    raw_status = (postulation.status or "").lower()
    # Para el índice, las variantes terminales se tratan como "rejected"
    normalized_status = "rejected" if raw_status in CANCEL_VARIANTS else raw_status
    reason = _get_reason_from_postulation(postulation)

    # Índice del estado actual dentro del flujo base
    try:
        cur_idx = BASE_FLOW.index(normalized_status)
    except ValueError:
        cur_idx = BASE_FLOW.index("selection_pending")  # fallback defensivo

    steps = []
    for idx, st in enumerate(BASE_FLOW):
        # Estado visual base
        if idx < cur_idx:
            state = "done"
        elif idx == cur_idx:
            state = "current"
        else:
            state = "pending"

        # ⬇️ FIX: si NO estamos en 'hired', el paso 'hired' no puede aparecer como 'done'
        if normalized_status != "hired" and st == "hired":
            state = "pending"

        key_for_step = st
        label_for_step = STATUS_LABELS_ES.get(st, st)

        # Si estamos en el paso terminal y el estado real fue una variante, cambiamos key/label
        if st == "rejected" and raw_status in CANCEL_VARIANTS:
            key_for_step = raw_status
            label_for_step = STATUS_LABELS_ES.get(raw_status, raw_status)

        step = {
            "key": key_for_step,
            "state": state,
            "label": label_for_step,
        }

        # Fecha de creación en el primer paso
        if st == "submitted":
            step["date"] = postulation.created_at

        # Resultado final + mensajes
        if st == "hired" and normalized_status == "hired":
            step["result"] = "hired"
            step["message"] = "¡Felicitaciones, fuiste contratado!"

        if st == "rejected" and normalized_status == "rejected":
            step["result"] = key_for_step  # puede ser 'rejected' o una variante
            step["message"] = "Tu proceso ha finalizado."
            if reason:
                step["reason"] = reason

        # Datos de entrevista
        if st == "interview_scheduled" and interview:
            step["interview"] = {
                "starts_at": interview.starts_at,
                "modality": interview.modality,
                "location": interview.location,
                "meet_url": interview.meet_url,
            }

        # CTA de personalidad
        if st == "personality_test_ready":
            step["personality"] = {
                "test_url": f"/my-applications/{postulation.id}/personality-test",
                "state": "pending",
                "overall_score": None,
                "report_url": None,
            }

        steps.append(step)

    return steps


@blp.route("/postulations/<int:pid>/process")
class PostulationProcessView(MethodView):
    @jwt_required()
    @blp.response(200, PostulationProcessSchema)
    def get(self, pid: int):
        applicant_id = int(get_jwt_identity())

        post = db.session.get(Postulation, pid)
        if not post:
            abort(404, message="Postulación no encontrada")
        if post.applicant_id != applicant_id:
            abort(403, message="No autorizado.")

        vac = db.session.execute(
            select(Vacancy.id, Vacancy.title, Vacancy.location, Vacancy.modality)
            .where(Vacancy.id == post.vacancy_id)
        ).first()

        interview = db.session.execute(
            select(Interview).where(Interview.postulation_id == pid)
        ).scalar_one_or_none()

        steps = _build_steps(post, interview=interview)

        return {
            "postulation": {
                "id": post.id,
                "status": post.status,
                "created_at": post.created_at,
                "updated_at": post.updated_at,
                # Exponemos posibles motivos si existieran en el modelo
                "status_reason": getattr(post, "status_reason", None),
                "cancel_reason": getattr(post, "cancel_reason", None),
                "rejection_reason": getattr(post, "rejection_reason", None),
                "vacancy": {
                    "id": vac.id if vac else post.vacancy_id,
                    "title": vac.title if vac else None,
                    "location": vac.location if vac else None,
                    "modality": vac.modality if vac else None,
                },
            },
            "steps": steps,
        }
