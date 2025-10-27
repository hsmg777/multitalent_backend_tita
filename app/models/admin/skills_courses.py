# app/models/admin/skills_courses.py
from app.ext.db import db

# Tabla de asociación N:N entre skills y courses.
# Se definen FKs con ondelete="CASCADE" para limpiar vínculos al eliminar
# una skill o un course. La PK compuesta evita duplicados del par (skill, course).

skills_courses = db.Table(
    "skills_courses",
    db.Column(
        "skill_id",
        db.Integer,
        db.ForeignKey("skills.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    db.Column(
        "course_id",
        db.Integer,
        db.ForeignKey("courses.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    # Índices útiles para consultas por cualquiera de las dos columnas
    db.Index("ix_skills_courses_skill_id", "skill_id"),
    db.Index("ix_skills_courses_course_id", "course_id"),
)
