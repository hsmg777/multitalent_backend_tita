# app/models/personality/attempt.py
from datetime import datetime
from sqlalchemy import CheckConstraint
from app.ext.db import db
from app.ext.db_types import JSONBCompat_for

JSONBCompat = JSONBCompat_for(db)

class PersonalityAttempt(db.Model):
    __tablename__ = "personality_attempt"

    id = db.Column(db.Integer, primary_key=True)

    postulation_id = db.Column(
        db.Integer, db.ForeignKey("postulation.id", ondelete="CASCADE"),
        nullable=False, index=True, unique=True
    )
    applicant_id = db.Column(
        db.Integer, db.ForeignKey("applicant.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    vacancy_id = db.Column(
        db.Integer, db.ForeignKey("vacancies.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    status = db.Column(db.String(20), nullable=False, default="created", index=True)

    started_at   = db.Column(db.DateTime, nullable=True, index=True)
    finished_at  = db.Column(db.DateTime, nullable=True, index=True)
    duration_sec = db.Column(db.Integer,   nullable=True)

    time_limit_sec = db.Column(db.Integer,   nullable=True)
    expires_at     = db.Column(db.DateTime,  nullable=True, index=True)

    overall_score   = db.Column(db.SmallInteger, nullable=True)
    recommendation  = db.Column(db.String(16),   nullable=True)
    traits_json     = db.Column(JSONBCompat,     nullable=True)
    pdf_report_path = db.Column(db.Text,         nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "(finished_at IS NULL) OR (started_at IS NOT NULL AND finished_at >= started_at)",
            name="ck_attempt_times_make_sense",
        ),
    )

    # Relaciones (solo mapping; nada de reglas)
    postulation = db.relationship("Postulation", backref=db.backref("personality_attempt", uselist=False, cascade="all, delete-orphan"))
    applicant   = db.relationship("Applicant",   backref=db.backref("personality_attempts", lazy="dynamic"))
    vacancy     = db.relationship("Vacancy",     backref=db.backref("personality_attempts", lazy="dynamic"))
