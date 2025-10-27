# app/resources/admin/vacancies.py
from datetime import date, datetime

from flask import request
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload

from ...ext.db import db
from ...models.admin.charges import Charges
from ...models.admin.vacancy import Vacancy
from ...models.admin.vacancy_skills import VacancySkill
from ...schemas.admin.vacancy import VacancySchema, VacancySkillSchema

blp = Blueprint("AdminVacancies", __name__, description="CRUD de vacantes para cPanel")

# Schemas
vacancy_list_schema = VacancySchema(many=True)
vacancy_item_schema = VacancySchema()
vacancy_skill_item_schema = VacancySkillSchema()
vacancy_skill_list_schema = VacancySkillSchema(many=True)


# Helpers
def _require_admin():
    identity = get_jwt_identity()
    if not (isinstance(identity, str) and identity.startswith("admin:")):
        abort(403, message="Token no válido para cPanel")


def _paginate_query(query, page: int, per_page: int):
    total = query.count()
    items = (
        query.order_by(Vacancy.id.desc())
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
class VacanciesCollection(MethodView):
    @jwt_required()
    @blp.response(200)
    def get(self):
        """Listado con filtros y paginación"""
        _require_admin()

        q = (request.args.get("q") or "").strip()
        area = (request.args.get("area") or "").strip()
        modality = (request.args.get("modality") or "").strip()
        location = (request.args.get("location") or "").strip()
        status = (request.args.get("status") or "").strip()
        is_active = request.args.get("is_active")
        charge_id = request.args.get("charge_id")
        open_only = request.args.get("open_only")  # si está presente y es true => solo vigentes

        page, per_page = _parse_pagination()

        query = Vacancy.query.join(Charges, Vacancy.charge_id == Charges.id)

        if charge_id:
            try:
                cid = int(charge_id)
                query = query.filter(Vacancy.charge_id == cid)
            except ValueError:
                abort(400, message="charge_id inválido")

        if area:
            query = query.filter(Charges.area == area)

        if modality:
            query = query.filter(Vacancy.modality == modality)

        if location:
            query = query.filter(Vacancy.location.ilike(f"%{location}%"))

        if status:
            query = query.filter(Vacancy.status == status)

        if is_active is not None:
            # aceptar "true"/"false"/"1"/"0"
            val = (is_active or "").lower()
            if val in ("true", "1", "yes", "y"):
                query = query.filter(Vacancy.is_active.is_(True))
            elif val in ("false", "0", "no", "n"):
                query = query.filter(Vacancy.is_active.is_(False))
            else:
                abort(400, message="is_active debe ser true/false")

        if open_only:
            today = date.today()
            query = query.filter(Vacancy.apply_until >= today)

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
        data = vacancy_list_schema.dump(items)
        meta = {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page,
        }
        return {"items": data, "meta": meta}

    @jwt_required()
    @blp.arguments(VacancySchema)
    @blp.response(201, VacancySchema)
    def post(self, payload):
        """Crear nueva vacante (estado inicial: draft)"""
        _require_admin()

        # Validaciones de negocio básicas
        charge = Charges.query.get(payload["charge_id"])
        if not charge:
            abort(404, message="Charge no encontrado")

        apply_until = payload.get("apply_until")
        if apply_until and isinstance(apply_until, datetime):
            # si viniera como datetime, tomar solo la fecha
            payload["apply_until"] = apply_until.date()

        if not apply_until:
            abort(400, message="apply_until es requerido")

        # Estado inicial
        payload.setdefault("status", "draft")
        payload.setdefault("is_active", False)
        payload.setdefault("headcount", 1)

        vacancy = Vacancy(**payload)
        db.session.add(vacancy)
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            abort(400, message="Error de integridad al crear vacante", extra=str(e))
        return vacancy


@blp.route("/<int:vacancy_id>")
class VacanciesItem(MethodView):
    @jwt_required()
    @blp.response(200, VacancySchema)
    def get(self, vacancy_id: int):
        """
        Obtener una vacante por ID, incluyendo sus requisitos (requirements)
        con objeto `skill` embebido, en una sola llamada.
        """
        _require_admin()
        vacancy = (
            Vacancy.query
            .options(
                selectinload(Vacancy.requirements).joinedload(VacancySkill.skill)
            )
            .get_or_404(vacancy_id)
        )
        return vacancy

    @jwt_required()
    @blp.arguments(VacancySchema(partial=True))
    @blp.response(200, VacancySchema)
    def patch(self, payload, vacancy_id: int):
        _require_admin()
        vacancy = Vacancy.query.get_or_404(vacancy_id)

        # No permitir cambiar a pasado en apply_until si ya está publicada
        if "apply_until" in payload and vacancy.status == "published":
            new_date = payload["apply_until"]
            if isinstance(new_date, datetime):
                new_date = new_date.date()
            if new_date < date.today():
                abort(400, message="apply_until no puede ser en el pasado para publicadas")

        for k, v in payload.items():
            setattr(vacancy, k, v)

        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            abort(400, message="Error de integridad al actualizar vacante", extra=str(e))
        return vacancy

    @jwt_required()
    @blp.response(204)
    def delete(self, vacancy_id: int):
        _require_admin()
        vacancy = Vacancy.query.get_or_404(vacancy_id)

        # Nota: en fase posterior, bloquear borrado si existen postulaciones asociadas.
        db.session.delete(vacancy)
        db.session.commit()
        return None


@blp.route("/<int:vacancy_id>/publish")
class VacanciesPublish(MethodView):
    @jwt_required()
    @blp.response(200, VacancySchema)
    def post(self, vacancy_id: int):
        """Publicar una vacante (is_active=True, status=published)"""
        _require_admin()
        vacancy = Vacancy.query.get_or_404(vacancy_id)

        # Reglas mínimas de publicación
        if not vacancy.title or not vacancy.description:
            abort(400, message="title y description son obligatorios para publicar")

        if not vacancy.apply_until or vacancy.apply_until < date.today():
            abort(400, message="apply_until inválido o en el pasado")

        vacancy.is_active = True
        vacancy.status = "published"
        if vacancy.publish_at is None:
            vacancy.publish_at = datetime.utcnow()

        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            abort(400, message="No se pudo publicar la vacante", extra=str(e))

        return vacancy


@blp.route("/<int:vacancy_id>/close")
class VacanciesClose(MethodView):
    @jwt_required()
    @blp.response(200, VacancySchema)
    def post(self, vacancy_id: int):
        """Cerrar una vacante (is_active=False, status=closed)"""
        _require_admin()
        vacancy = Vacancy.query.get_or_404(vacancy_id)

        vacancy.is_active = False
        vacancy.status = "closed"

        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            abort(400, message="No se pudo cerrar la vacante", extra=str(e))

        return vacancy


@blp.route("/<int:vacancy_id>/skills")
class VacancySkillsCollection(MethodView):
    @jwt_required()
    @blp.response(200)
    def get(self, vacancy_id: int):
        """Listar skills asociadas a la vacante (enriquecidas con objeto skill)"""
        _require_admin()
        vacancy = Vacancy.query.get_or_404(vacancy_id)
        skills = (
            VacancySkill.query
            .options(joinedload(VacancySkill.skill))  # carga la relación para embebido
            .filter_by(vacancy_id=vacancy.id)
            .all()
        )
        return {"items": vacancy_skill_list_schema.dump(skills)}

    @jwt_required()
    @blp.arguments(VacancySkillSchema(many=True))
    @blp.response(200)
    def put(self, payload, vacancy_id: int):
        """
        Reemplazar el set completo de skills de una vacante.
        Recibe: [{skill_id, required_score?, weight?}, ...]
        Devuelve: items enriquecidos con objeto `skill`.
        """
        _require_admin()
        vacancy = Vacancy.query.get_or_404(vacancy_id)

        # Limpiar actuales
        VacancySkill.query.filter_by(vacancy_id=vacancy.id).delete(synchronize_session=False)

        # Insertar nuevas asociaciones
        for item in payload:
            vs = VacancySkill(
                vacancy_id=vacancy.id,
                skill_id=item["skill_id"],
                required_score=item.get("required_score"),
                weight=item.get("weight"),
            )
            db.session.add(vs)

        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            abort(400, message="Error al asociar skills a la vacante", extra=str(e))

        # Reconsultar con eager loading para devolver ya enriquecido
        skills = (
            VacancySkill.query
            .options(joinedload(VacancySkill.skill))
            .filter_by(vacancy_id=vacancy.id)
            .all()
        )
        return {"items": vacancy_skill_list_schema.dump(skills)}
