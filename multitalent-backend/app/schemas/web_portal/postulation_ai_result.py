from marshmallow import Schema, fields

class PostulationAIResultSchema(Schema):
    id = fields.Int()
    postulation_id = fields.Int(required=True)
    vacancy_id = fields.Int(allow_none=True)
    score = fields.Int(required=True)
    feedback = fields.Str(required=True)
    created_at = fields.DateTime()
