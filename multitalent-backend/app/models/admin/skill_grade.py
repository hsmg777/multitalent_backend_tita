# app/models/recruitment/skill_grade.py
from datetime import datetime
from app.ext.db import db

class SkillGrade(db.Model):
    __tablename__ = "skills_grades"

    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer,db.ForeignKey("interviews.id", ondelete="CASCADE"),nullable=False,index=True,)
    skill_id = db.Column(db.Integer,db.ForeignKey("skills.id", ondelete="RESTRICT"),nullable=False,index=True,)
    score = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("interview_id", "skill_id", name="uq_skills_grades_interview_skill"),
        db.CheckConstraint("score >= 0 AND score <= 100", name="ck_skills_grades_score_0_100"),
    )

    # Relaciones
    interview = db.relationship(
        "Interview",
        back_populates="skill_grades",
        lazy="selectin",
        passive_deletes=True,
    )
    skill = db.relationship(
        "Skill",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<SkillGrade interview={self.interview_id} skill={self.skill_id} score={self.score}>"
