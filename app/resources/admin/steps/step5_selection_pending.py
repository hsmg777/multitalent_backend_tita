# app/resources/admin/steps/step5_selection_pending.py
from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from marshmallow import Schema, fields
from sqlalchemy import select

from app.ext.db import db
from app.models.web_portal.postulation import Postulation
from app.services.postulation_service import transition_to
from ....schemas.web_portal.postulation import PostulationStatusSchema

blp = Blueprint(
    "AdminStep5SelectionPending",
    __name__,
    description="Admin: Step 5 - Contratar desde selection_pending"
)

# ------- Helpers -------
def _load_postulation_or_404(pid: int) -> Postulation:
    p = db.session.get(Postulation, pid)
    if not p:
        abort(404, message="Postulación no encontrada")
    return p

def _ensure_status_selection(p: Postulation) -> None:
    if (p.status or "").lower() != "selection_pending":
        abort(400, message="Esta acción requiere estado 'selection_pending'.")


# ------- Route -------
@blp.route("/<int:pid>/hire", methods=["POST"])
class HireFromSelection(MethodView):
    """
    Cambia la postulación a 'hired'.
            """
    @jwt_required()
    @blp.response(200, PostulationStatusSchema)
    def post(self, pid: int):
        p = _load_postulation_or_404(pid)
        _ensure_status_selection(p)

        # Solo transición; sin otras validaciones
        transition_to(p, "hired", send_email=False)
        return {"id": p.id, "status": p.status}
