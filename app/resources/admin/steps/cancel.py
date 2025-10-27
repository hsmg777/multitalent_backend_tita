from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask import request, current_app

from ....ext.db import db
from ....models.web_portal.postulation import Postulation
from ....schemas.web_portal.postulation import PostulationSchema
from ....services.postulation_service import transition_to

blp = Blueprint(
    "AdminStepCancel",
    __name__,
    description="Cancelar proceso de postulación (mover a 'rejected')",
)

def _get_postulation_or_404(postulation_id: int) -> Postulation:
    p = Postulation.query.get(postulation_id)
    if not p:
        abort(404, message="Postulación no encontrada")
    return p

# POST /api/admin/postulations/<id>/cancel
@blp.route("/<int:postulation_id>/cancel", methods=["POST"])
class CancelStep(MethodView):
    @jwt_required()
    def post(self, postulation_id: int):
        p = _get_postulation_or_404(postulation_id)
        prev = (p.status or "").strip().lower()

        allowed_prev = {
            "submitted", "accepted", "prescreen_call",
            "personality_test_ready", "interview_scheduled",
            "selection_pending",
        }
        if prev not in allowed_prev:
            abort(400, message=f"No se puede cancelar desde el estado '{prev}'")

        data = request.get_json(silent=True) or {}
        reason = (data.get("reason") or "").strip()

        # Guarda la razón si vino en el body
        if reason:
            current_app.logger.info(
                "[CANCEL] postulation_id=%s prev=%s reason=%s",
                postulation_id, prev, reason
            )
            if hasattr(p, "status_reason"):
                p.status_reason = reason
            elif hasattr(p, "cancel_reason"):
                p.cancel_reason = reason
            elif hasattr(p, "rejection_reason"):
                p.rejection_reason = reason

        try:
            transition_to(p, "rejected", send_email=False)
            db.session.commit()  # Persistir motivo + estado
        except ValueError as e:
            db.session.rollback()
            abort(400, message=str(e))

        return PostulationSchema().dump(p), 200
