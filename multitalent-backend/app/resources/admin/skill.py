from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from ...ext.db import db
from ...models.admin.skill import Skill
from ...models.admin.course import Course
from ...schemas.admin.skill import (
    SkillSchema,
    SkillCreateSchema,
    SkillUpdateSchema,
    SkillQuerySchema,
    SkillListSchema,
)
from marshmallow import Schema, fields


blp = Blueprint("AdminSkills", __name__, description="CRUD de skills (cPanel)")


def _require_admin():
    identity = get_jwt_identity()
    if not (isinstance(identity, str) and identity.startswith("admin:")):
        abort(403, message="Token no válido para cPanel")


# Schema simple para listas compactas (id, nombre)
class CourseCompactSchema(Schema):
    id = fields.Int()
    nombre = fields.Str()


@blp.route("/")
class AdminSkillsCollection(MethodView):
    @jwt_required()
    @blp.arguments(SkillQuerySchema, location="query")
    @blp.response(200, SkillListSchema)
    def get(self, args):
        """Listar skills con filtros y paginación"""
        _require_admin()
        q = args.get("q")
        is_active = args.get("is_active")
        page = max(args.get("page", 1), 1)
        per_page = max(min(args.get("per_page", 10), 100), 1)

        query = Skill.query
        if q:
            like = f"%{q.strip().lower()}%"
            query = query.filter(
                or_(
                    Skill.nombre.ilike(like),
                    Skill.descripcion.ilike(like),
                )
            )
        if is_active is not None:
            query = query.filter(Skill.is_active == bool(is_active))

        total = query.count()
        items = (
            query.order_by(Skill.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return {"items": items, "total": total, "page": page, "per_page": per_page}

    @jwt_required()
    @blp.arguments(SkillCreateSchema)
    @blp.response(201, SkillSchema)
    def post(self, payload):
        """Crear una skill"""
        _require_admin()
        skill = Skill(
            nombre=payload["nombre"],
            descripcion=payload.get("descripcion"),
            nivel_minimo=payload["nivel_minimo"],
            is_active=payload.get("is_active", True),
        )
        skill.normalize()

        try:
            db.session.add(skill)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            abort(409, message="El nombre de la skill ya está registrado")

        return skill


@blp.route("/<int:skill_id>")
class AdminSkillsItem(MethodView):
    @jwt_required()
    @blp.response(200, SkillSchema)
    def get(self, skill_id):
        """Obtener skill por ID"""
        _require_admin()
        return Skill.query.get_or_404(skill_id)

    @jwt_required()
    @blp.arguments(SkillUpdateSchema)
    @blp.response(200, SkillSchema)
    def patch(self, payload, skill_id):
        """Actualizar skill por ID"""
        _require_admin()
        skill = Skill.query.get_or_404(skill_id)

        if "nombre" in payload and payload["nombre"]:
            skill.nombre = payload["nombre"]
            skill.normalize()
        if "descripcion" in payload:
            skill.descripcion = payload["descripcion"]
        if "nivel_minimo" in payload:
            skill.nivel_minimo = payload["nivel_minimo"]
        if "is_active" in payload:
            skill.is_active = bool(payload["is_active"])

        try:
            db.session.add(skill)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            abort(409, message="El nombre de la skill ya está registrado")

        return skill

    @jwt_required()
    @blp.response(204)
    def delete(self, skill_id):
        """Eliminar skill por ID"""
        _require_admin()
        skill = Skill.query.get_or_404(skill_id)
        db.session.delete(skill)
        db.session.commit()
        return None


# -------------------------
# US-33: Cursos asociados a una skill
# -------------------------

@blp.route("/<int:skill_id>/courses")
class AdminSkillCoursesCollection(MethodView):
    @jwt_required()
    @blp.response(200, CourseCompactSchema(many=True))
    def get(self, skill_id):
        """Listar cursos asociados a una skill"""
        _require_admin()
        skill = Skill.query.get_or_404(skill_id)
        return skill.courses

    @jwt_required()
    @blp.arguments(Schema.from_dict({"course_ids": fields.List(fields.Int(), required=True)})())
    @blp.response(201, CourseCompactSchema(many=True))
    def post(self, payload, skill_id):
        """Asociar uno o varios cursos a una skill"""
        _require_admin()
        skill = Skill.query.get_or_404(skill_id)

        added = []
        for course_id in payload["course_ids"]:
            course = Course.query.get(course_id)
            if not course:
                abort(404, message=f"Curso {course_id} no encontrado")
            if course in skill.courses:
                abort(409, message=f"Curso {course_id} ya está asociado")
            skill.courses.append(course)
            added.append(course)

        db.session.add(skill)
        db.session.commit()
        return added


@blp.route("/<int:skill_id>/courses/<int:course_id>")
class AdminSkillCoursesItem(MethodView):
    @jwt_required()
    @blp.response(204)
    def delete(self, skill_id, course_id):
        """Desasociar un curso de una skill"""
        _require_admin()
        skill = Skill.query.get_or_404(skill_id)
        course = Course.query.get_or_404(course_id)

        if course not in skill.courses:
            abort(404, message="El curso no está asociado a la skill")

        skill.courses.remove(course)
        db.session.add(skill)
        db.session.commit()
        return None
