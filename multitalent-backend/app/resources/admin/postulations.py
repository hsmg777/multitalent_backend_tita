# app/resources/admin/postulations.py
from datetime import datetime
from flask_smorest import Blueprint
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from ...ext.db import db
from ...ext.s3 import delete_cv_key, extract_key_from_cv_path
from ...models.web_portal.postulation import Postulation
from ...schemas.web_portal.postulation import PostulationSchema, PostulationUpdateSchema

blp_admin = Blueprint("AdminPostulations", __name__, description="Admin: Postulations")

@blp_admin.route("/<int:postulation_id>")
class AdminPostulationItem(MethodView):
    @blp_admin.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    @blp_admin.response(200, PostulationSchema)
    def get(self, postulation_id: int):
        """Obtener una postulación (admin)."""
        post = Postulation.query.get_or_404(postulation_id)
        return post

    @blp_admin.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    @blp_admin.arguments(PostulationUpdateSchema, location="json")
    @blp_admin.response(200, PostulationSchema)
    def patch(self, payload, postulation_id: int):
        """Actualizar campos editables de una postulación (admin)."""
        post = Postulation.query.get_or_404(postulation_id)
        editable = {
            "residence_addr",
            "age",
            "role_exp_years",
            "expected_salary",
            "cv_path",
            "status",       
            "number",
            "credential",
        }
        for k, v in payload.items():
            if k in editable:
                setattr(post, k, v)
        post.updated_at = datetime.utcnow()
        db.session.commit()
        return post

    @blp_admin.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    @blp_admin.response(204)
    def delete(self, postulation_id: int):
        """Eliminar una postulación y su CV (admin)."""
        post = Postulation.query.get_or_404(postulation_id)
        cv_key = extract_key_from_cv_path(post.cv_path)
        db.session.delete(post)
        db.session.commit()
        if cv_key and cv_key.startswith("curriculums/"):
            delete_cv_key(cv_key)
        return "", 204
