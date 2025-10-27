# app/schemas/admin/vacancy_stats.py
from marshmallow import Schema, fields

class VacancyWithCountSchema(Schema):
    id = fields.Int(required=True)
    title = fields.Str(required=True)
    apply_until = fields.Date(required=True)
    status = fields.Str(required=True)
    is_active = fields.Bool(required=True)
    postulations_count = fields.Int(required=True)


class AdminPostulationRowSchema(Schema):
    id = fields.Int()
    vacancy_id = fields.Int()
    applicant_id = fields.Int()

    credential = fields.Str(allow_none=True)   
    number = fields.Str(allow_none=True)     
    residence_addr = fields.Str(allow_none=True)
    age = fields.Int(allow_none=True)
    role_exp_years = fields.Int(allow_none=True)
    expected_salary = fields.Int(allow_none=True)
    cv_path = fields.Str()
    status = fields.Str()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()

    applicant_name = fields.Str(allow_none=True)
    applicant_email = fields.Str(allow_none=True)


