from marshmallow import Schema, fields

class HealthOut(Schema):
    status = fields.Str(required=True, example="ok")
