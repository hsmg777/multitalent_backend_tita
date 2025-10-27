# app/resources/admin/postulations_by_vacancy.py
from flask_smorest import Blueprint
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from ...models.web_portal.postulation import Postulation
from ...schemas.web_portal.postulation import PostulationSchema

blp = Blueprint("AdminVacancyPostulations", __name__, description="Postulaciones por vacante (Admin)")

@blp.route("/<int:vacancy_id>/postulations")
class AdminPostulationsByVacancy(MethodView):
    @blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    @blp.response(200, PostulationSchema(many=True))
    def get(self, vacancy_id: int):
        q = (Postulation.query
             .filter_by(vacancy_id=vacancy_id)
             .order_by(Postulation.created_at.desc()))
        return q.all()
