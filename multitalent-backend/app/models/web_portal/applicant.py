from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app.ext.db import db


class Applicant(db.Model):
    __tablename__ = "applicant"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    numero = db.Column(db.String(20), nullable=False)

    password_hash = db.Column(db.Text, nullable=True)
    is_google = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    postulations = db.relationship("Postulation", back_populates="applicant")


    # ---- helpers de seguridad ----
    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if self.password_hash is None:
            return False
        return check_password_hash(self.password_hash, password)

    # ---- normalizaciones ----
    def normalize(self):
        if self.email:
            self.email = self.email.strip().lower()
        if self.username:
            self.username = self.username.strip()

    def __repr__(self) -> str:
        return f"<Applicant {self.id} {self.email}>"
    
