from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app.ext.db import db

class AdminUser(db.Model):
    __tablename__ = "admin_users"  

    id = db.Column(db.Integer, primary_key=True)

    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)

    # TEXT para evitar truncado de hashes
    password_hash = db.Column(db.Text, nullable=False)

    # extras útiles para el panel
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_superuser = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # helpers
    def set_password(self, raw: str) -> None:
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password_hash, raw)

    def normalize(self) -> None:
        if self.email:
            self.email = self.email.strip().lower()

    def __repr__(self) -> str:
        return f"<AdminUser {self.id} {self.email}>"
