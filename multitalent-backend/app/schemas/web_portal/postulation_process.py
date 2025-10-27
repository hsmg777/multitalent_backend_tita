# app/schemas/web_portal/postulation_process.py
from marshmallow import Schema, fields

class VacancyLiteSchema(Schema):
    id = fields.Int()
    title = fields.Str()
    location = fields.Str(allow_none=True)
    modality = fields.Str(allow_none=True)

class PostulationLiteSchema(Schema):
    id = fields.Int()
    status = fields.Str()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
    # Exponer posibles campos de motivo
    cancel_reason = fields.Str(allow_none=True)
    status_reason = fields.Str(allow_none=True)
    rejection_reason = fields.Str(allow_none=True)
    vacancy = fields.Nested(VacancyLiteSchema)

class StepInterviewSchema(Schema):
    starts_at = fields.DateTime(allow_none=True)
    modality = fields.Str(allow_none=True)
    location = fields.Str(allow_none=True)
    meet_url = fields.Str(allow_none=True)

class StepPersonalitySchema(Schema):
    test_url = fields.Str(allow_none=True)
    state = fields.Str()
    overall_score = fields.Int(allow_none=True)
    report_url = fields.Str(allow_none=True)

class ProcessStepSchema(Schema):
    key = fields.Str()
    label = fields.Str()
    state = fields.Str()
    date = fields.DateTime(allow_none=True)
    interview = fields.Nested(StepInterviewSchema, allow_none=True)
    personality = fields.Nested(StepPersonalitySchema, allow_none=True)
    result = fields.Str(allow_none=True)
    message = fields.Str(allow_none=True)
    reason = fields.Str(allow_none=True)  # motivo a nivel del step terminal

class PostulationProcessSchema(Schema):
    postulation = fields.Nested(PostulationLiteSchema)
    steps = fields.List(fields.Nested(ProcessStepSchema))
