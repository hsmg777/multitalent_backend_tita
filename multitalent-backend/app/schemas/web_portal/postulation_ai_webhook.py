from marshmallow import Schema, fields

class CVSchema(Schema):
    storage = fields.Str(required=False)          # "url" | "s3"
    presigned_url = fields.Str(required=False)
    s3_bucket = fields.Str(required=False)
    s3_key = fields.Str(required=False)

class ApplicantProfileSchema(Schema):
    residence_addr = fields.Str(allow_none=True)
    age = fields.Int(allow_none=True)
    role_exp_years = fields.Int(allow_none=True)
    expected_salary = fields.Float(allow_none=True)
    name = fields.Str(allow_none=True)
    email = fields.Str(allow_none=True)
    phone = fields.Str(allow_none=True)
    credential = fields.Str(allow_none=True)

class VacancyProfileSchema(Schema):
    location = fields.Str(allow_none=True)
    modality = fields.Str(allow_none=True)
    role_objective = fields.Str(allow_none=True)
    responsibilities = fields.Str(allow_none=True)
    req_education = fields.Str(allow_none=True)
    req_experience = fields.Str(allow_none=True)
    req_knowledge = fields.Str(allow_none=True)
    charge_title = fields.Str(allow_none=True)
    charge_description = fields.Str(allow_none=True)
    charge_area = fields.Str(allow_none=True)

class PostulationAIScoreWebhookSchema(Schema):
    postulation_id = fields.Int(required=True)
    vacancy_id = fields.Int(allow_none=True)
    position = fields.Str(allow_none=True)
    cv = fields.Nested(CVSchema, required=True)

    # NUEVO
    applicant_profile = fields.Nested(ApplicantProfileSchema, required=True)
    vacancy_profile = fields.Nested(VacancyProfileSchema, required=True)
