# app/resources/admin/courses.py
from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from ...ext.db import db
from ...models.admin.course import Course
from ...schemas.admin.course import (
    CourseSchema,
    CourseCreateSchema,
    CourseUpdateSchema,
    CourseQuerySchema,
    CourseListSchema,
)

blp = Blueprint("AdminCourses", __name__, description="CRUD de cursos (cPanel)")


def _require_admin():
    identity = get_jwt_identity()
    if not (isinstance(identity, str) and identity.startswith("admin:")):
        abort(403, message="Token no válido para cPanel")


@blp.route("/")
class AdminCoursesCollection(MethodView):
    @jwt_required()
    @blp.arguments(CourseQuerySchema, location="query")
    @blp.response(200, CourseListSchema)
    def get(self, args):
        """Listar cursos con filtros y paginación"""
        _require_admin()
        q = args.get("q")
        is_active = args.get("is_active")
        page = max(args.get("page", 1), 1)
        per_page = max(min(args.get("per_page", 10), 100), 1)

        query = Course.query
        if q:
            like = f"%{q.strip().lower()}%"
            query = query.filter(
                or_(
                    Course.nombre.ilike(like),
                    Course.descripcion.ilike(like),
                    Course.url.ilike(like),  # incluir url en búsqueda
                )
            )
        if is_active is not None:
            query = query.filter(Course.is_active == bool(is_active))

        total = query.count()
        items = (
            query.order_by(Course.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return {"items": items, "total": total, "page": page, "per_page": per_page}

    @jwt_required()
    @blp.arguments(CourseCreateSchema)
    @blp.response(201, CourseSchema)
    def post(self, payload):
        """Crear un curso"""
        _require_admin()
        course = Course(
            nombre=payload["nombre"],
            descripcion=payload.get("descripcion"),
            is_active=payload.get("is_active", True),
            url=payload.get("url"),
        )
        course.normalize()

        try:
            db.session.add(course)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            abort(409, message="El nombre del curso ya está registrado")

        return course


@blp.route("/<int:course_id>")
class AdminCoursesItem(MethodView):
    @jwt_required()
    @blp.response(200, CourseSchema)
    def get(self, course_id):
        """Obtener curso por ID"""
        _require_admin()
        return Course.query.get_or_404(course_id)

    @jwt_required()
    @blp.arguments(CourseUpdateSchema)
    @blp.response(200, CourseSchema)
    def patch(self, payload, course_id):
        """Actualizar curso por ID"""
        _require_admin()
        course = Course.query.get_or_404(course_id)

        if "nombre" in payload and payload["nombre"]:
            course.nombre = payload["nombre"]
            course.normalize()
        if "descripcion" in payload:
            course.descripcion = payload["descripcion"]
        if "is_active" in payload:
            course.is_active = bool(payload["is_active"])
        if "url" in payload:
            course.url = payload["url"]

        try:
            db.session.add(course)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            abort(409, message="El nombre del curso ya está registrado")

        return course

    @jwt_required()
    @blp.response(204)
    def delete(self, course_id):
        """Eliminar curso por ID"""
        _require_admin()
        course = Course.query.get_or_404(course_id)
        db.session.delete(course)
        db.session.commit()
        return None
