# app/models/personality/answer.py
from datetime import datetime
from sqlalchemy import UniqueConstraint, CheckConstraint
from app.ext.db import db

class PersonalityAnswer(db.Model):
    __tablename__ = "personality_answer"

    id = db.Column(db.Integer, primary_key=True)

    attempt_id = db.Column(
        db.Integer, db.ForeignKey("personality_attempt.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    question_code = db.Column(db.String(20),     nullable=False)
    option_value  = db.Column(db.SmallInteger,   nullable=False)
    answered_at   = db.Column(db.DateTime,       nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("attempt_id", "question_code", name="uq_answer_attempt_question"),
        CheckConstraint("option_value >= 0", name="ck_answer_option_non_negative"),
    )

    attempt = db.relationship("PersonalityAttempt", backref=db.backref("answers", cascade="all, delete-orphan", lazy="dynamic"))
