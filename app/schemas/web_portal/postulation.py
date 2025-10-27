# app/schemas/web_portal/postulation.py
from marshmallow import Schema, fields, validate

class PostulationCreateSchema(Schema):
    vacancy_id = fields.Int(required=True)
    residence_addr = fields.Str(required=False, validate=validate.Length(min=3))
    credential = fields.Str(required=False, validate=validate.Length(max=20))
    number = fields.Str(required=False, validate=validate.Length(max=20))
    age = fields.Int(required=False, validate=validate.Range(min=15, max=100))
    role_exp_years = fields.Float(required=False, validate=validate.Range(min=0))
    expected_salary = fields.Float(required=False, validate=validate.Range(min=0))
    cv_path = fields.Str(required=True)
    status = fields.Str(required=False, validate=validate.Length(max=32))

class PostulationSchema(Schema):
    """Schema básico: solo los campos propios de la postulación"""
    id = fields.Int(dump_only=True)
    vacancy_id = fields.Int()
    applicant_id = fields.Int()
    residence_addr = fields.Str()
    credential = fields.Str()
    number = fields.Str()
    age = fields.Int()
    role_exp_years = fields.Float()
    expected_salary = fields.Float()
    cv_path = fields.Str()
    status = fields.Str()
    # ⬇️ NUEVO: exponer el motivo
    status_reason = fields.Str(allow_none=True)
    created_at = fields.DateTime()
    updated_at = fields.DateTime()

class PostulationUpdateSchema(Schema):
    residence_addr = fields.Str(validate=validate.Length(min=1, max=255))
    credential = fields.Str(required=False, validate=validate.Length(max=20))
    number = fields.Str(required=False, validate=validate.Length(max=20))
    age = fields.Int(validate=validate.Range(min=14, max=100))
    role_exp_years = fields.Int(validate=validate.Range(min=0, max=70))
    expected_salary = fields.Int(validate=validate.Range(min=0))
    cv_path = fields.Str(validate=validate.Length(min=1, max=512))
    status = fields.Str(validate=validate.Length(min=1, max=32))

class PostulationStatusSchema(Schema):
    id = fields.Int(required=True)
    status = fields.Str(required=True)

# 🔹 Schema básico para la vacante (solo campos útiles para el portal)
class VacancyBasicSchema(Schema):
    id = fields.Int()
    title = fields.Str()
    location = fields.Str()
    modality = fields.Str()

# 🔹 Schema extendido de Postulación con datos de la vacante
class PostulationWithVacancySchema(Schema):
    id = fields.Int(dump_only=True)
    status = fields.Str()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
    vacancy_id = fields.Int()
    status_reason = fields.Str(allow_none=True)
    vacancy = fields.Nested(VacancyBasicSchema, dump_only=True)
