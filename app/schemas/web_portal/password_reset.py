from marshmallow import Schema, fields, validate

class ForgotPasswordSchema(Schema):
    email = fields.Email(required=True)

class ResetPasswordSchema(Schema):
    token = fields.Str(required=True, validate=validate.Length(min=16))
    password = fields.Str(required=True, load_only=True, validate=validate.Length(min=6))

class MessageSchema(Schema):
    message = fields.Str()
