from marshmallow import Schema, fields

class ChargesSchema(Schema):
    id = fields.Int(dump_only=True)
    title = fields.Str(required=True)
    area = fields.Str(required=False, allow_none=True)
    description = fields.Str(required=True)
