# app/resources/admin/steps/step1_accept.py
from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from sqlalchemy.orm import joinedload  # <-- eager loading
from ....models.web_portal.postulation import Postulation
from ....schemas.web_portal.postulation import PostulationSchema
from ....services.postulation_service import transition_to

blp_admin_step1 = Blueprint(
    "AdminPostulationsStep1",
    __name__,
    description="Admin: Step 1 (Aceptar)"
)

@blp_admin_step1.route("/<int:postulation_id>/steps/1/start")
class AdminStep1Start(MethodView):
    @blp_admin_step1.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    @blp_admin_step1.response(200, PostulationSchema)
    def post(self, postulation_id: int):
        """
        STEP 1 — Iniciar proceso:
        - Transiciona a 'accepted'
        - Dispara correo al candidato (usando applicant.email)
        """
        post = (
            Postulation.query
            .options(joinedload(Postulation.applicant))
            .get_or_404(postulation_id)
        )

        # (Opcional) Validación explícita si no hay applicant
        if not getattr(post, "applicant", None):
            abort(400, message="La postulación no tiene applicant asociado.")

        try:
            # Transición + side-effect de email (en el servicio)
            post = transition_to(post, "accepted", send_email=True)
        except ValueError as e:
            abort(400, message=str(e))

        return post
