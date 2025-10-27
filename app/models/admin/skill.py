from datetime import datetime
from app.ext.db import db
# Tabla de unión N:N (crear en app/models/admin/skills_courses.py)
from .skills_courses import skills_courses


class Skill(db.Model):
    __tablename__ = "skills"

    id = db.Column(db.Integer, primary_key=True)

    # Catálogo básico de la skill
    nombre = db.Column(db.String(150), unique=True, nullable=False, index=True)
    descripcion = db.Column(db.Text, nullable=True)

    # Niveles aceptados (US-31): guardamos el mínimo aceptado como entero.
    # La validación de rango (p.ej. 1..100) se realiza en los Schemas.
    nivel_minimo = db.Column(db.Integer, nullable=False, default=1)

    # Gestión
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relaciones (US-33): asociación N:N con cursos
    # Nota: requiere que exista la tabla de unión `skills_courses`
    # definida en app/models/admin/skills_courses.py y que sea importada
    # en app/models/__init__.py para que Alembic la detecte en migraciones.
    courses = db.relationship(
        "Course",
        secondary=skills_courses,
        back_populates="skills",
        lazy="selectin",        # carga eficiente de colecciones
        passive_deletes=True,   # respeta ON DELETE CASCADE en FKs
    )

    # ---- helpers ----
    def normalize(self) -> None:
        if self.nombre:
            self.nombre = self.nombre.strip()

    def __repr__(self) -> str:
        return f"<Skill {self.id} {self.nombre} (min:{self.nivel_minimo})>"
