# app/resources/admin/auth.py
from datetime import timedelta
from flask_smorest import Blueprint, abort   
from flask.views import MethodView
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from sqlalchemy.exc import IntegrityError

from ...ext.db import db
from ...models.admin.admin_user import AdminUser
from ...schemas.admin.admin_user import (
    AdminUserCreateSchema,
    AdminLoginSchema,
    AdminUserSchema,
    AdminAuthResponseSchema,
)

blp = Blueprint("AdminAuth", __name__, description="Autenticación cPanel Admin")



@blp.route("/login")
class AdminLogin(MethodView):
    @blp.arguments(AdminLoginSchema, location="json")
    @blp.response(200, AdminAuthResponseSchema)
    def post(self, payload):
        email = payload["email"].strip().lower()
        user = AdminUser.query.filter_by(email=email).first()

        if not user or not user.is_active or not user.check_password(payload["password"]):
            abort(401, message="Credenciales inválidas")  
        token = create_access_token(identity=f"admin:{user.id}", expires_delta=timedelta(hours=4))
        return {"access_token": token, "user": user}

@blp.route("/profile")
class AdminProfile(MethodView):
    @blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    @blp.response(200, AdminUserSchema)
    def get(self):
        identity = get_jwt_identity()
        if not (isinstance(identity, str) and identity.startswith("admin:")):
            abort(403, message="Token no válido para cPanel") 
        admin_id = int(identity.split(":", 1)[1])
        user = AdminUser.query.get_or_404(admin_id)
        return user
