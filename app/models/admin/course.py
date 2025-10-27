# app/models/admin/course.py
from datetime import datetime
from app.ext.db import db
from .skills_courses import skills_courses


class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)

    nombre = db.Column(db.String(150), unique=True, nullable=False, index=True)
    descripcion = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    url = db.Column(db.String(255), nullable=True)  # 👈 nuevo

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    skills = db.relationship(
        "Skill",
        secondary=skills_courses,
        back_populates="courses",
        lazy="selectin",
        passive_deletes=True,
    )

    def normalize(self) -> None:
        if self.nombre:
            self.nombre = self.nombre.strip()

    def __repr__(self) -> str:
        return f"<Course {self.id} {self.nombre}>"
