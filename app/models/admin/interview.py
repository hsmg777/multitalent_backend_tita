# app/models/admin/interview.py
from sqlalchemy import func
from ...ext.db import db

class Interview(db.Model):
    __tablename__ = "interviews"

    id = db.Column(db.Integer, primary_key=True)

    postulation_id = db.Column(
        db.Integer,
        db.ForeignKey("postulation.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Fecha/hora de la reunión (UTC recomendado)
    starts_at = db.Column(db.DateTime, nullable=False)

    modality  = db.Column(db.String(20), nullable=True)   
    location  = db.Column(db.String(255), nullable=True)  
    meet_url  = db.Column(db.String(512), nullable=True)  
    notes     = db.Column(db.Text, nullable=True)        

    created_at = db.Column(db.DateTime, nullable=False, server_default=func.now())
    updated_at = db.Column(db.DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Relaciones
    postulation = db.relationship(
        "Postulation",
        back_populates="interview",
        uselist=False,
        passive_deletes=True,
    )

    skill_grades = db.relationship(
        "SkillGrade",
        back_populates="interview",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
