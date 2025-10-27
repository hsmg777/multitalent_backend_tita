 # app/schemas/terms.py
from marshmallow import Schema, fields

class TermsAcceptanceCreateSchema(Schema):
    doc_path = fields.String(required=True)

class TermsAcceptanceOutSchema(Schema):
    id = fields.Integer()
    user_id = fields.Integer()
    doc_path = fields.String()
    accepted_at = fields.DateTime()
    created_at = fields.DateTime()
