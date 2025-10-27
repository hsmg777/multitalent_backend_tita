from app.ext.db import db

class Charges(db.Model):
    __tablename__ = "charges"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    area = db.Column(db.String(120), nullable=True, index=True)
    description = db.Column(db.Text, nullable=False)

    def __repr__(self) -> str:
        return f"<Charges {self.id} {self.title!r}>"