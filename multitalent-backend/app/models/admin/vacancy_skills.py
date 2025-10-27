from app.ext.db import db


class VacancySkill(db.Model):
    __tablename__ = "vacancy_skills"

    id = db.Column(db.Integer, primary_key=True)

    vacancy_id = db.Column(
        db.Integer,
        db.ForeignKey("vacancies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_id = db.Column(
        db.Integer,
        db.ForeignKey("skills.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Metadatos por requisito
    required_score = db.Column(db.Integer, nullable=True)  # recomendado 0..100
    weight = db.Column(db.Float, nullable=True)            # ponderación para ranking

    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    # Relaciones
    vacancy = db.relationship("Vacancy", back_populates="requirements")
    skill = db.relationship("Skill")

    __table_args__ = (
        db.UniqueConstraint("vacancy_id", "skill_id", name="uq_vacancy_skill"),
        db.CheckConstraint(
            "(required_score IS NULL) OR (required_score BETWEEN 0 AND 100)",
            name="ck_vacancy_skill_required_score",
        ),
        db.CheckConstraint(
            "(weight IS NULL) OR (weight >= 0)",
            name="ck_vacancy_skill_weight_nonnegative",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<VacancySkill v={self.vacancy_id} skill={self.skill_id} "
            f"req={self.required_score} w={self.weight}>"
        )
