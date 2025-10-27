# app/resources/web_portal/vacancies.py
from datetime import date
from flask import request
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from sqlalchemy import or_

from ...models.admin.charges import Charges
from ...models.admin.vacancy import Vacancy
from ...schemas.web_portal.vacancy import PublicVacancySchema

blp = Blueprint("PublicVacancies", __name__, description="Vacantes públicas (portal)")

# Exporta todo lo definido en el schema (incluye modality/location en inglés y alias ES)
public_list_schema = PublicVacancySchema(many=True)
public_item_schema = PublicVacancySchema()


def _paginate_query(query, page: int, per_page: int):
    total = query.count()
    items = (
        query.order_by(Vacancy.publish_at.desc().nullslast(), Vacancy.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return items, total


def _parse_pagination():
    try:
        page = max(int(request.args.get("page", 1)), 1)
        per_page = max(min(int(request.args.get("per_page", 10)), 100), 1)
    except ValueError:
        abort(400, message="Parámetros de paginación inválidos")
    return page, per_page


@blp.route("/")
class PublicVacanciesCollection(MethodView):
    @blp.response(200)
    def get(self):
        """
        Listar vacantes visibles al público:
        - status = published
        - is_active = True
        - apply_until >= hoy
        Soporta filtros: q, area, modality, location
        """
        q = (request.args.get("q") or "").strip()
        area = (request.args.get("area") or "").strip()
        modality = (request.args.get("modality") or "").strip()
        location = (request.args.get("location") or "").strip()

        page, per_page = _parse_pagination()
        today = date.today()

        query = (
            Vacancy.query.join(Charges, Vacancy.charge_id == Charges.id)
            .filter(Vacancy.status == "published")
            .filter(Vacancy.is_active.is_(True))
            .filter(Vacancy.apply_until >= today)
        )

        if area:
            query = query.filter(Charges.area == area)

        if modality:
            query = query.filter(Vacancy.modality == modality)

        if location:
            query = query.filter(Vacancy.location.ilike(f"%{location}%"))

        if q:
            like = f"%{q.lower()}%"
            query = query.filter(
                or_(
                    Vacancy.title.ilike(like),
                    Vacancy.description.ilike(like),
                    Charges.title.ilike(like),
                )
            )

        items, total = _paginate_query(query, page, per_page)
        data = public_list_schema.dump(items)
        meta = {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page,
        }
        return {"items": data, "meta": meta}


@blp.route("/<int:vacancy_id>")
class PublicVacanciesItem(MethodView):
    @blp.response(200, PublicVacancySchema)
    def get(self, vacancy_id: int):
        """
        Detalle público de una vacante.
        Solo retornará si cumple visibilidad pública.
        """
        today = date.today()
        query = (
            Vacancy.query.filter(Vacancy.id == vacancy_id)
            .filter(Vacancy.status == "published")
            .filter(Vacancy.is_active.is_(True))
            .filter(Vacancy.apply_until >= today)
        )
        vacancy = query.first()
        if not vacancy:
            abort(404, message="Vacante no encontrada")
        return vacancy
