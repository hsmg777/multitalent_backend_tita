# app/schemas/admin/course.py
from marshmallow import Schema, fields, validate

class SkillCompactSchema(Schema):
    id = fields.Int(dump_only=True)
    nombre = fields.Str(dump_only=True)

class CourseCreateSchema(Schema):
    nombre = fields.Str(required=True, validate=validate.Length(min=1, max=150))
    descripcion = fields.Str(validate=validate.Length(max=1000))
    is_active = fields.Bool(load_default=True)
    url = fields.Url(allow_none=True)  # 👈 nuevo (opcional)

class CourseUpdateSchema(Schema):
    nombre = fields.Str(validate=validate.Length(min=1, max=150))
    descripcion = fields.Str(validate=validate.Length(max=1000))
    is_active = fields.Bool()
    url = fields.Url(allow_none=True)  # 👈 nuevo (opcional)

class CourseSchema(Schema):
    id = fields.Int(dump_only=True)
    nombre = fields.Str()
    descripcion = fields.Str()
    is_active = fields.Bool()
    url = fields.Url(allow_none=True)  # 👈 incluir en respuesta
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    skills = fields.List(fields.Nested(SkillCompactSchema), dump_only=True)

class CourseQuerySchema(Schema):
    q = fields.Str()
    is_active = fields.Bool()
    page = fields.Int(load_default=1)
    per_page = fields.Int(load_default=10)

class CourseListSchema(Schema):
    items = fields.List(fields.Nested(CourseSchema))
    total = fields.Int()
    page = fields.Int()
    per_page = fields.Int()
