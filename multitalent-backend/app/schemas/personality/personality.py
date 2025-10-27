# app/schemas/personality/personality.py
from marshmallow import Schema, fields, validate


class OkSchema(Schema):
    ok = fields.Boolean(required=True)
    message = fields.String()


class AnswerSchema(Schema):
    question_code = fields.String(required=True, validate=validate.Length(min=1, max=20))
    option_value  = fields.Integer(required=True)

class AnswersPayloadSchema(Schema):
    answers = fields.List(fields.Nested(AnswerSchema), required=True)


class AttemptResultSchema(Schema):
    provider         = fields.String(allow_none=True)
    attempt_id       = fields.Integer(allow_none=True)
    started_at       = fields.String(allow_none=True)
    finished_at      = fields.String(allow_none=True)
    duration_minutes = fields.Integer(allow_none=True)
    overall_score    = fields.Integer(allow_none=True)
    traits           = fields.Dict(keys=fields.String(), values=fields.Float(), allow_none=True)
    notes            = fields.List(fields.String(), allow_none=True)
    recommendation   = fields.String(allow_none=True)
    status           = fields.String(allow_none=True)

class BootstrapResponseSchema(Schema):
    attempt_id     = fields.Integer(required=True)
    status         = fields.String(required=True)
    time_limit_sec = fields.Integer(allow_none=True)
    expires_at     = fields.String(allow_none=True)
    started_at     = fields.String(allow_none=True)

class AdminStep3ResponseSchema(Schema):
    postulation_id = fields.Integer(required=True)
    status         = fields.String(required=True)
    view_state     = fields.String(required=True)
    message        = fields.String(required=True)
    results        = fields.Nested(AttemptResultSchema, allow_none=True)

class OptionSchema(Schema):
    value = fields.Integer(required=True)
    label = fields.String(required=True)

class QuestionSchema(Schema):
    code       = fields.String(required=True, validate=validate.Length(min=1, max=20))
    text       = fields.String(required=True)
    scale_type = fields.String(required=True)
    min_value  = fields.Integer(required=True)
    max_value  = fields.Integer(required=True)
    order      = fields.Integer(required=True)
    options    = fields.List(fields.Nested(OptionSchema), required=True)

class BootstrapWithQuestionsSchema(Schema):
    attempt_id     = fields.Integer(required=True)
    status         = fields.String(required=True)
    time_limit_sec = fields.Integer(allow_none=True)
    expires_at     = fields.String(allow_none=True)
    started_at     = fields.String(allow_none=True)
    questions      = fields.List(fields.Nested(QuestionSchema), required=True)
