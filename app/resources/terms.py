# app/resources/terms.py
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.ext.db import db
from app.models.terms_acceptance import TermsAcceptance
from ..schemas.terms import TermsAcceptanceCreateSchema, TermsAcceptanceOutSchema

from ..feature_flags import is_feature_enabled

# app/resources/terms.py

blp = Blueprint("Terms", __name__ , description="Términos & Condiciones")

@blp.route("/acceptances")
class TermsAcceptances(MethodView):
    @blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    @blp.arguments(TermsAcceptanceCreateSchema, location="json")
    @blp.response(201, TermsAcceptanceOutSchema)
    def post(self, payload):
        user_id = int(get_jwt_identity())
        doc_path = payload["doc_path"].strip()

        # Launch habilitar/deshabilitar esta funcionalidad
        if not is_feature_enabled("terms-acceptance-enabled", str(user_id)):
            abort(
                403,
                message="La aceptación de términos está temporalmente deshabilitadesss. Intenta más tarde.",
            )

        # Comportamiento normal cuando el flag está ON
        rec = TermsAcceptance(user_id=user_id, doc_path=doc_path)
        db.session.add(rec)
        db.session.commit()
        return rec

