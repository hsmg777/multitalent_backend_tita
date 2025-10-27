from marshmallow import Schema, fields, validate


class ApplicantCreateSchema(Schema):
    username = fields.Str(required=True, validate=validate.Length(min=3, max=80))
    email = fields.Email(required=True)
    nombre = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    apellido = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    numero = fields.Str(required=True, validate=validate.Length(min=5, max=20))
    password = fields.Str(load_only=True, required=True, validate=validate.Length(min=6))


class ApplicantLoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(load_only=True, required=True)


class ApplicantGoogleSchema(Schema):
    email = fields.Email(required=True)
    nombre = fields.Str(required=True)
    apellido = fields.Str(required=True)
    username = fields.Str(required=True)


class ApplicantSchema(Schema):
    id = fields.Int(dump_only=True)
    username = fields.Str()
    email = fields.Email()
    nombre = fields.Str()
    apellido = fields.Str()
    numero = fields.Str()
    is_google = fields.Bool()
    created_at = fields.DateTime()
