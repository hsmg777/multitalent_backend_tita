# app/resources/web_portal/applicant.py
from datetime import timedelta
from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from sqlalchemy.exc import IntegrityError
from flask import current_app

from ...ext.db import db
from ...ext.mail import send_mail
from ...models.web_portal.applicant import Applicant
from ...models.web_portal.password_reset import PasswordResetToken
from ...schemas.web_portal.applicant import (
    ApplicantCreateSchema,
    ApplicantLoginSchema,
    ApplicantGoogleSchema,
    ApplicantSchema,
)
from ...schemas.web_portal.password_reset import (
    ForgotPasswordSchema, ResetPasswordSchema, MessageSchema
)

blp = Blueprint("ApplicantsAuth", __name__, description="Auth de Applicant")


@blp.route("/register")
class RegisterApplicant(MethodView):
    @blp.arguments(ApplicantCreateSchema, location="json")
    @blp.response(201, ApplicantSchema)
    def post(self, payload):
        # normaliza y valida unicidad
        applicant = Applicant(
            username=payload["username"],
            email=payload["email"].lower(),
            nombre=payload["nombre"],
            apellido=payload["apellido"],
            numero=payload["numero"],
        )
        applicant.normalize()
        applicant.set_password(payload["password"])

        try:
            db.session.add(applicant)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            abort(409, message="El email o username ya existe")

        return applicant


@blp.route("/login")
class LoginApplicant(MethodView):
    @blp.arguments(ApplicantLoginSchema, location="json")
    def post(self, payload):
        applicant = Applicant.query.filter_by(email=payload["email"].lower()).first()

        if not applicant:
            return {"message": "Credenciales incorrectas"}, 401

        if applicant.password_hash is None:
            return {"message": "Tu cuenta está registrada con Google. Usa el login de Google."}, 400

        if not applicant.check_password(payload["password"]):
            return {"message": "Credenciales incorrectas"}, 401

        # PyJWT v2 exige sub como string
        token = create_access_token(identity=str(applicant.id),  # <— string
                                    expires_delta=timedelta(hours=3))
        return {
            "access_token": token,
            "user": ApplicantSchema().dump(applicant),
        }, 200


@blp.route("/profile")
class ProfileApplicant(MethodView):
    @blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    @blp.response(200, ApplicantSchema)
    def get(self):
        # leer y castear a int para consultas
        applicant_id = int(get_jwt_identity())
        applicant = Applicant.query.get_or_404(applicant_id)
        return applicant


@blp.route("/google")
class GoogleLoginApplicant(MethodView):
    @blp.arguments(ApplicantGoogleSchema, location="json")
    def post(self, payload):
        email = payload["email"].lower()
        applicant = Applicant.query.filter_by(email=email).first()

        if not applicant:
            applicant = Applicant(
                username=payload["username"],
                email=email,
                nombre=payload["nombre"],
                apellido=payload["apellido"],
                numero="",
                password_hash=None,
                is_google=True,
            )
            applicant.normalize()
            try:
                db.session.add(applicant)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                # Si choca por username, generamos uno alterno simple
                base = payload["username"]
                suffix = 1
                while Applicant.query.filter_by(username=f"{base}{suffix}").first():
                    suffix += 1
                applicant.username = f"{base}{suffix}"
                db.session.add(applicant)
                db.session.commit()

        token = create_access_token(identity=str(applicant.id),  # <— string
                                    expires_delta=timedelta(hours=3))
        return {
            "access_token": token,
            "user": ApplicantSchema().dump(applicant),
        }, 200


@blp.route("/password/forgot")
class ForgotPassword(MethodView):
    @blp.arguments(ForgotPasswordSchema, location="json")
    @blp.response(200, MessageSchema)
    def post(self, payload):
        """
        Envía email con link para resetear contraseña.
        """
        email = payload["email"].strip().lower()
        applicant = Applicant.query.filter_by(email=email).first()

        if applicant and applicant.password_hash:
            token, raw = PasswordResetToken.issue_for(
                applicant_id=applicant.id,
                hours=current_app.config["RESET_TOKEN_HOURS"],
            )
            db.session.commit()

            link = f'{current_app.config["FRONTEND_URL"]}/reset-password?token={raw}'
            html = f"""
              <p>Hola {applicant.nombre},</p>
              <p>Recibimos una solicitud para restablecer tu contraseña.</p>
              <p><a href="{link}">Haz clic aquí para continuar</a> (expira en {current_app.config["RESET_TOKEN_HOURS"]} horas).</p>
              <p>Si no solicitaste este cambio, ignora este mensaje.</p>
            """
            try:
                send_mail(to=email, subject="Restablecer contraseña - Multitalent", html=html)
            except Exception as e:
                current_app.logger.exception("Error enviando email de reset: %s", e)

        return {"message": "Si el email existe, enviaremos instrucciones para restablecer la contraseña."}


@blp.route("/password/reset")
class ResetPassword(MethodView):
    @blp.arguments(ResetPasswordSchema, location="json")
    @blp.response(200, MessageSchema)
    def post(self, payload):
        """
        Consume el token y cambia la contraseña.
        """
        token = PasswordResetToken.consume(payload["token"])
        if not token:
            abort(400, message="Token inválido o expirado")

        applicant = Applicant.query.get(token.applicant_id)
        if not applicant:
            abort(400, message="Token inválido")

        applicant.set_password(payload["password"])
        # opcional: invalidar otros tokens activos
        PasswordResetToken.query.filter(
            PasswordResetToken.applicant_id == applicant.id,
            PasswordResetToken.used_at.is_(None)
        ).update({"used_at": db.func.now()})

        db.session.commit()
        return {"message": "Contraseña actualizada correctamente"}
