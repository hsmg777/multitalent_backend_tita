# app/models/admin/vacancy.py
from datetime import datetime

from sqlalchemy import JSON as SA_JSON
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.types import TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB

from app.ext.db import db


# === JSONB en Postgres, JSON genérico en SQLite/otros (para tests) ===
class JSONBCompat(TypeDecorator):
    """Usa JSONB en PostgreSQL y JSON en otros dialectos (p.ej. SQLite en tests)."""
    impl = SA_JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_JSONB())
        return dialect.type_descriptor(SA_JSON())


# === MutableList que acepta CSV en str y lo normaliza a list ===
class CSVCoercibleList(MutableList):
    @classmethod
    def coerce(cls, key, value):
        # None -> None
        if value is None:
            return None
        # str CSV -> lista normalizada
        if isinstance(value, str):
            parts = [t.strip() for t in value.split(",") if t.strip()]
            return cls(parts)
        # tuple/set/list -> list
        if isinstance(value, (tuple, set, list)):
            return cls(list(value))
        # fallback (levantará ValueError si no corresponde)
        return super().coerce(key, value)


class Vacancy(db.Model):
    __tablename__ = "vacancies"

    id = db.Column(db.Integer, primary_key=True)

    # Relación: muchas Vacancies -> un Charge
    charge_id = db.Column(
        db.Integer,
        db.ForeignKey("charges.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Datos visibles/funcionales
    title = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(120), nullable=True, index=True)   # ciudad/país o “remoto/híbrido”
    modality = db.Column(db.String(20), nullable=True, index=True)    # onsite | hybrid | remote

    # Publicación y ventana de postulación
    apply_until = db.Column(db.Date, nullable=False, index=True)
    publish_at = db.Column(db.DateTime, nullable=True, index=True)

    # Estado/visibilidad
    is_active = db.Column(db.Boolean, nullable=False, default=False, index=True)
    status = db.Column(  # draft | published | closed | archived
        db.String(20),
        nullable=False,
        default="draft",
        index=True,
    )

    # Operación
    headcount = db.Column(db.Integer, nullable=False, default=1)

    # Auditoría simple (ids de admin u operador)
    created_by = db.Column(db.Integer, nullable=True)
    updated_by = db.Column(db.Integer, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Párrafo “¿Cuál es el objetivo del rol?”
    role_objective = db.Column(db.Text, nullable=True)

    # Listas de bullets (arrays de strings) — mutable para detectar cambios in-place
    responsibilities = db.Column(MutableList.as_mutable(JSONBCompat()), nullable=False, default=list)
    req_education   = db.Column(MutableList.as_mutable(JSONBCompat()), nullable=False, default=list)
    req_experience  = db.Column(MutableList.as_mutable(JSONBCompat()), nullable=False, default=list)
    req_knowledge   = db.Column(MutableList.as_mutable(JSONBCompat()), nullable=False, default=list)
    benefits        = db.Column(MutableList.as_mutable(JSONBCompat()), nullable=False, default=list)

    # Párrafo de “Nosotros” (sobre la empresa)
    company_about   = db.Column(db.Text, nullable=True)

    # Chips/etiquetas -> usa la clase que convierte CSV<->list
    tags            = db.Column(CSVCoercibleList.as_mutable(JSONBCompat()), nullable=False, default=list)

    # Imagen/cover opcional para la vacante
    hero_image_url  = db.Column(db.Text, nullable=True)

    # Relaciones
    charge = db.relationship(
        "Charges",
        backref=db.backref("vacancies", lazy="dynamic"),
        lazy="joined",
    )

    # Requisitos (skills) por vacante; relación definida en VacancySkill
    # Cambiado a lazy="selectin" para permitir eager loading eficiente (y evitar N+1)
    requirements = db.relationship(
        "VacancySkill",
        back_populates="vacancy",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        db.CheckConstraint("headcount >= 1", name="ck_vacancies_headcount_positive"),
        db.Index("ix_vacancies_public", "is_active", "apply_until", "status"),
    )

    def __repr__(self) -> str:
        return f"<Vacancy {self.id} {self.title!r} charge={self.charge_id}>"
