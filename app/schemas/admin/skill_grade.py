# app/schemas/recruitment/skill_grade.py
from marshmallow import Schema, fields, validate

class SkillGradeSchema(Schema):
    id = fields.Int(dump_only=True)
    interview_id = fields.Int(required=True)
    skill_id = fields.Int(required=True)
    score = fields.Int(required=True, validate=validate.Range(min=0, max=100))
    comment = fields.Str(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

class SkillGradeCreateSchema(Schema):
    skill_id = fields.Int(required=True)
    score = fields.Int(required=True, validate=validate.Range(min=0, max=100))
    comment = fields.Str(allow_none=True)

class SkillGradeUpdateSchema(Schema):
    score = fields.Int(validate=validate.Range(min=0, max=100))
    comment = fields.Str(allow_none=True)
