from datetime import datetime
from app.ext.db import db

class PostulationAIResult(db.Model):
    __tablename__ = "postulation_ai_results"

    id = db.Column(db.Integer, primary_key=True)
    postulation_id = db.Column(db.Integer, nullable=False, index=True)
    vacancy_id     = db.Column(db.Integer, nullable=True, index=True)
    score          = db.Column(db.Integer, nullable=False)   # 0..100
    feedback       = db.Column(db.Text, nullable=False)

    created_at     = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
