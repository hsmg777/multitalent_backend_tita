from datetime import datetime
from app.ext.db import db


class Postulation(db.Model):
    __tablename__ = "postulation"

    id = db.Column(db.Integer, primary_key=True)

    vacancy_id = db.Column(
        db.Integer,
        db.ForeignKey("vacancies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    applicant_id = db.Column(
        db.Integer,
        db.ForeignKey("applicant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Datos del formulario
    residence_addr = db.Column(db.Text, nullable=True)
    age = db.Column(db.SmallInteger, nullable=True)
    role_exp_years = db.Column(db.Numeric(4, 1), nullable=True)
    expected_salary = db.Column(db.Numeric(12, 2), nullable=True)
    credential = db.Column(db.String(20), nullable=True)
    number = db.Column(db.String(20), nullable=True)

    # Ruta del CV en S3
    cv_path = db.Column(db.Text, nullable=False)

    # Estado del proceso (submitted, accepted, rejected, hired, etc.)
    status = db.Column(db.String(32), nullable=False, default="submitted", index=True)

    # Motivo del estado (p.ej. por qué se canceló/rechazó)
    status_reason = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    __table_args__ = (
        db.UniqueConstraint("applicant_id", "vacancy_id", name="uq_postulation_applicant_vacancy"),
    )

    # Relaciones
    applicant = db.relationship("Applicant", back_populates="postulations")

    vacancy = db.relationship(
        "Vacancy",
        backref=db.backref("postulations", cascade="all, delete-orphan"),
    )

    interview = db.relationship(
        "Interview",
        back_populates="postulation",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return (
            f"<Postulation {self.id} applicant={self.applicant_id} "
            f"vacancy={self.vacancy_id} status={self.status}>"
        )
