# app/models/terms_acceptance.py
from datetime import datetime
from sqlalchemy import ForeignKey
from app.ext.db import db  # <- igual que en Applicant


class TermsAcceptance(db.Model):
    __tablename__ = "terms_acceptances"

    id = db.Column(db.Integer, primary_key=True)

    # FK al postulante (no a users)
    user_id = db.Column(
        db.Integer,
        ForeignKey("applicant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    doc_path = db.Column(db.String(512), nullable=False)

    # mismos estilos de timestamp que usas en Applicant
    accepted_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at  = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # opcional: relación de conveniencia
    applicant = db.relationship("Applicant", backref="terms_acceptances")

    def __repr__(self) -> str:
        return f"<TermsAcceptance id={self.id} user_id={self.user_id} doc_path='{self.doc_path}'>"
