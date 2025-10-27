from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask_jwt_extended import jwt_required

from ....models.web_portal.postulation import Postulation
from ....schemas.web_portal.postulation import PostulationSchema
from ....services.postulation_service import transition_to

blp = Blueprint(
    "AdminStep2Prescreen",
    __name__,
    description="Step 2: Prescreen (llamada de aceptación)",
)

def _get_postulation_or_404(postulation_id: int) -> Postulation:
    p = Postulation.query.get(postulation_id)
    if not p:
        abort(404, message="Postulación no encontrada")
    return p


@blp.route("/<int:postulation_id>/complete", methods=["POST"])
class Step2Complete(MethodView):
    @jwt_required()
    def post(self, postulation_id: int):
        p = _get_postulation_or_404(postulation_id)
        prev = (p.status or "").strip().lower()

        if prev not in {"accepted", "prescreen_call"}:
            abort(400, message=f"Transición no permitida desde '{prev}' para completar prescreen")

        try:
            if prev == "accepted":
                transition_to(p, "prescreen_call", send_email=False)

            transition_to(p, "personality_test_ready", send_email=False)

        except ValueError as e:
            abort(400, message=str(e))

        return PostulationSchema().dump(p), 200
