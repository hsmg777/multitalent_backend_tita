# app/resources/guards.py
from flask import request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from werkzeug.routing import Rule
from app.models.terms_acceptance import TermsAcceptance

DOC_PATH_REQUIRED = "/archives/Terminos_y_Condiciones_Multiapoyo.pdf"

def init_terms_guard(app):
    @app.before_request
    def require_terms_for_postulation():
        # Solo aplica a POST /api/postulations (tu colección)
        if request.method != "POST":
            return

        # Resuelve endpoint/rule de forma segura
        rule: Rule | None = request.url_rule
        if not rule:
            return

        # Ajusta si tu prefijo es distinto
        is_postulation_create = rule.rule == "/api/postulations"
        if not is_postulation_create:
            return

        # Auth requerida para chequear applicant
        try:
            verify_jwt_in_request()
        except Exception:
            return  # tu endpoint ya valida JWT; no duplicamos

        applicant_id = int(get_jwt_identity())

        # ¿Aceptó ya este doc?
        exists = TermsAcceptance.query.filter_by(
            user_id=applicant_id,
            doc_path=DOC_PATH_REQUIRED
        ).first()

        if not exists:
            # 428 Precondition Required (semánticamente correcto)
            from flask_smorest import abort
            abort(
                428,
                message="Debes aceptar los Términos y Condiciones antes de postular.",
                extra={"doc_path_required": DOC_PATH_REQUIRED}
            )
