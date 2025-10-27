from datetime import datetime, timedelta
import hashlib, secrets
from app.ext.db import db


class PasswordResetToken(db.Model):
    __tablename__ = "password_reset"

    id = db.Column(db.Integer, primary_key=True)
    applicant_id = db.Column(db.Integer, db.ForeignKey("applicant.id", ondelete="CASCADE"), nullable=False)
    token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    applicant = db.relationship("Applicant", backref=db.backref("password_resets", lazy="dynamic"))

    @staticmethod
    def _hash(raw: str) -> str:
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @classmethod
    def issue_for(cls, applicant_id: int, hours: int = 2) -> tuple["PasswordResetToken", str]:
        """
        Crea un token nuevo para el usuario y retorna (instancia, raw_token) donde raw_token
        es el que enviaremos por email (nunca guardamos el raw en DB).
        """
        raw_token = secrets.token_urlsafe(48)         # largo/aleatorio
        token = cls(
            applicant_id=applicant_id,
            token_hash=cls._hash(raw_token),
            expires_at=datetime.utcnow() + timedelta(hours=hours),
        )
        # opcional: invalidar tokens previos no usados
        cls.query.filter_by(applicant_id=applicant_id, used_at=None).delete()
        db.session.add(token)
        return token, raw_token

    @classmethod
    def consume(cls, raw_token: str) -> "PasswordResetToken | None":
        """
        Marca como usado si es válido; retorna la fila o None.
        """
        now = datetime.utcnow()
        token = cls.query.filter_by(token_hash=cls._hash(raw_token), used_at=None).first()
        if not token or token.expires_at < now:
            return None
        token.used_at = now
        return token
