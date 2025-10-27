from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from ...ext.db import db
from ...models.admin.admin_user import AdminUser
from ...schemas.admin.admin_user import (
    AdminUserSchema,
    AdminUserCreateSchema,
    AdminUserUpdateSchema,
    AdminUserQuerySchema,
    AdminUserListSchema,
    AdminUserSetPasswordSchema,
)

blp = Blueprint("AdminUsers", __name__, description="CRUD de usuarios del sistema (cPanel)")

def _require_admin():
    identity = get_jwt_identity()
    if not (isinstance(identity, str) and identity.startswith("admin:")):
        abort(403, message="Token no válido para cPanel")

@blp.route("/")
class AdminUsersCollection(MethodView):
    @jwt_required()
    @blp.arguments(AdminUserQuerySchema, location="query")
    @blp.response(200, AdminUserListSchema)
    def get(self, args):
        _require_admin()
        q = args.get("q")
        is_active = args.get("is_active")
        page = max(args.get("page", 1), 1)
        per_page = max(min(args.get("per_page", 10), 100), 1)

        query = AdminUser.query
        if q:
            like = f"%{q.strip().lower()}%"
            query = query.filter(
                or_(
                    AdminUser.email.ilike(like),
                    AdminUser.nombre.ilike(like),
                    AdminUser.apellido.ilike(like),
                )
            )
        if is_active is not None:
            query = query.filter(AdminUser.is_active == bool(is_active))

        total = query.count()
        items = (
            query.order_by(AdminUser.created_at.desc())
                 .offset((page - 1) * per_page)
                 .limit(per_page)
                 .all()
        )
        return {"items": items, "total": total, "page": page, "per_page": per_page}

    @jwt_required()
    @blp.arguments(AdminUserCreateSchema)
    @blp.response(201, AdminUserSchema)
    def post(self, payload):
        _require_admin()
        user = AdminUser(
            nombre=payload["nombre"],
            apellido=payload["apellido"],
            email=payload["email"],
        )
        user.normalize()
        user.set_password(payload["password"])

        try:
            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            abort(409, message="El email ya está registrado")

        return user

@blp.route("/<int:user_id>")
class AdminUsersItem(MethodView):
    @jwt_required()
    @blp.response(200, AdminUserSchema)
    def get(self, user_id):
        _require_admin()
        return AdminUser.query.get_or_404(user_id)

    @jwt_required()
    @blp.arguments(AdminUserUpdateSchema)
    @blp.response(200, AdminUserSchema)
    def patch(self, payload, user_id):
        _require_admin()
        user = AdminUser.query.get_or_404(user_id)

        if "email" in payload and payload["email"]:
            user.email = payload["email"]
            user.normalize()
        if "nombre" in payload:
            user.nombre = payload["nombre"]
        if "apellido" in payload:
            user.apellido = payload["apellido"]
        if "is_active" in payload:
            user.is_active = bool(payload["is_active"])
        if "is_superuser" in payload:
            user.is_superuser = bool(payload["is_superuser"])

        try:
            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            abort(409, message="El email ya está registrado por otro usuario")

        return user

    @jwt_required()
    @blp.response(204)
    def delete(self, user_id):
        _require_admin()
        user = AdminUser.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        return None

@blp.route("/<int:user_id>/password")
class AdminUsersPassword(MethodView):
    @jwt_required()
    @blp.arguments(AdminUserSetPasswordSchema)
    @blp.response(204)
    def post(self, payload, user_id):
        _require_admin()
        user = AdminUser.query.get_or_404(user_id)
        user.set_password(payload["password"])
        db.session.add(user)
        db.session.commit()
        return None
