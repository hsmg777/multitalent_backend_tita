from flask_smorest import Blueprint
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from sqlalchemy import desc, func

from ...ext.db import db
from ...models.admin.vacancy import Vacancy
from ...models.web_portal.postulation import Postulation
from ...models.web_portal.applicant import Applicant 
from ...schemas.admin.vacancy_stats import (VacancyWithCountSchema, AdminPostulationRowSchema,)
blp = Blueprint("AdminVacancyStats", __name__, description="Stats de Vacantes (Admin)")

@blp.route("/active-with-counts")
class AdminVacanciesActiveWithCounts(MethodView):
    @blp.doc(security=[{"BearerAuth": []}])
    @jwt_required() 
    @blp.response(200, VacancyWithCountSchema(many=True))
    def get(self):
        """
        Lista de vacantes activas/publicadas con conteo de postulaciones.
        """
        q = (
            db.session.query(
                Vacancy.id.label("id"),
                Vacancy.title.label("title"),
                Vacancy.apply_until.label("apply_until"),
                Vacancy.status.label("status"),
                Vacancy.is_active.label("is_active"),
                func.count(Postulation.id).label("postulations_count"),
            )
            .outerjoin(Postulation, Postulation.vacancy_id == Vacancy.id)
            .filter(Vacancy.is_active.is_(True))
            .filter(Vacancy.status == "published")
            .group_by(Vacancy.id)
            .order_by(Vacancy.created_at.desc())
        )
        rows = q.all()
        return [
            dict(
                id=r.id,
                title=r.title,
                apply_until=r.apply_until,
                status=r.status,
                is_active=r.is_active,
                postulations_count=int(r.postulations_count or 0),
            )
            for r in rows
        ]
    

@blp.route("/<int:vacancy_id>/postulations")
class AdminPostulationsByVacancy(MethodView):
    @blp.doc(security=[{"BearerAuth": []}])
    # @jwt_required()
    @blp.response(200, AdminPostulationRowSchema(many=True))
    def get(self, vacancy_id: int):
        """
        Postulaciones de la vacante con nombre/email del applicant + credential/number.
        """
        q = (
            db.session.query(
                Postulation.id.label("id"),
                Postulation.vacancy_id.label("vacancy_id"),
                Postulation.applicant_id.label("applicant_id"),
                Postulation.credential.label("credential"),
                Postulation.number.label("number"),
                Postulation.residence_addr.label("residence_addr"),
                Postulation.age.label("age"),
                Postulation.role_exp_years.label("role_exp_years"),
                Postulation.expected_salary.label("expected_salary"),
                Postulation.cv_path.label("cv_path"),
                Postulation.status.label("status"),
                Postulation.created_at.label("created_at"),
                Postulation.updated_at.label("updated_at"),

                func.trim(
                    func.concat(
                        func.coalesce(Applicant.nombre, ""),
                        " ",
                        func.coalesce(Applicant.apellido, "")
                    )
                ).label("applicant_name"),

                Applicant.email.label("applicant_email"),
            )
            .join(Applicant, Applicant.id == Postulation.applicant_id) 
            .filter(Postulation.vacancy_id == vacancy_id)
            .order_by(desc(Postulation.created_at))
        )
        rows = q.all()
        return [dict(r._mapping) for r in rows]