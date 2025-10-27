# app/schemas/recruitment/interview.py
from marshmallow import Schema, fields, validate
from .skill_grade import SkillGradeSchema, SkillGradeCreateSchema, SkillGradeUpdateSchema

MODALITY_CHOICES = ("online", "onsite", "hybrid")

class InterviewSchema(Schema):
    id = fields.Int(dump_only=True)
    postulation_id = fields.Int(required=True)
    starts_at = fields.DateTime(required=True)

    modality = fields.Str(allow_none=True, validate=validate.OneOf(MODALITY_CHOICES))
    location = fields.Str(allow_none=True)
    meet_url = fields.Str(allow_none=True)
    notes = fields.Str(allow_none=True)

    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    skill_grades = fields.List(fields.Nested(SkillGradeSchema), dump_only=True)

class InterviewCreateSchema(Schema):
    postulation_id = fields.Int(required=True)
    starts_at = fields.DateTime(required=True)

    modality = fields.Str(allow_none=True, validate=validate.OneOf(MODALITY_CHOICES))
    location = fields.Str(allow_none=True)
    meet_url = fields.Str(allow_none=True)
    notes = fields.Str(allow_none=True)
    grades = fields.List(fields.Nested(SkillGradeCreateSchema))

class InterviewUpdateSchema(Schema):
    starts_at = fields.DateTime()
    modality = fields.Str(validate=validate.OneOf(MODALITY_CHOICES))
    location = fields.Str()
    meet_url = fields.Str(allow_none=True)
    notes = fields.Str(allow_none=True)
    grades = fields.List(fields.Nested(SkillGradeUpdateSchema))
