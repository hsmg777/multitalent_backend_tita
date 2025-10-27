from marshmallow import Schema, fields, validate

class AdminUserCreateSchema(Schema):
    nombre = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    apellido = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True, validate=validate.Length(min=6))

class AdminLoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True)

class AdminUserSchema(Schema):
    id = fields.Int(dump_only=True)
    nombre = fields.Str()
    apellido = fields.Str()
    email = fields.Email()
    is_active = fields.Bool()
    is_superuser = fields.Bool()
    created_at = fields.DateTime(dump_only=True)


class AdminAuthResponseSchema(Schema):
    access_token = fields.Str(required=True)
    user = fields.Nested(AdminUserSchema, required=True)




class AdminUserUpdateSchema(Schema):
    nombre = fields.Str(validate=validate.Length(min=1, max=100))
    apellido = fields.Str(validate=validate.Length(min=1, max=100))
    email = fields.Email()
    is_active = fields.Bool()
    is_superuser = fields.Bool()

class AdminUserSetPasswordSchema(Schema):
    password = fields.Str(required=True, load_only=True, validate=validate.Length(min=6))

class AdminUserQuerySchema(Schema):
    q = fields.Str()            
    is_active = fields.Bool()     
    page = fields.Int(load_default=1)
    per_page = fields.Int(load_default=10)

class AdminUserListSchema(Schema):
    items = fields.List(fields.Nested(AdminUserSchema))
    total = fields.Int()
    page = fields.Int()
    per_page = fields.Int()
