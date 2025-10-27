from marshmallow import Schema, fields, validate


# --- Esquemas auxiliares (US-33) ---

class CourseCompactSchema(Schema):
    """Representación compacta de Course para anidar en Skill."""
    id = fields.Int(dump_only=True)
    nombre = fields.Str(dump_only=True)


class SkillCoursesAttachSchema(Schema):
    """Payload para asociar uno o varios cursos a una skill."""
    course_ids = fields.List(
        fields.Int(),
        required=True,
        validate=validate.Length(min=1),
    )


# --- Esquemas principales de Skill ---

class SkillCreateSchema(Schema):
    nombre = fields.Str(required=True, validate=validate.Length(min=1, max=150))
    descripcion = fields.Str(required=False, allow_none=True)
    nivel_minimo = fields.Int(
        required=True,
        validate=validate.Range(min=1, max=100),  # ajusta el rango según la escala que definan
    )
    is_active = fields.Bool(load_default=True)


class SkillUpdateSchema(Schema):
    nombre = fields.Str(validate=validate.Length(min=1, max=150))
    descripcion = fields.Str(allow_none=True)
    nivel_minimo = fields.Int(validate=validate.Range(min=1, max=100))
    is_active = fields.Bool()


class SkillSchema(Schema):
    id = fields.Int(dump_only=True)
    nombre = fields.Str()
    descripcion = fields.Str(allow_none=True)
    nivel_minimo = fields.Int()
    is_active = fields.Bool()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    # US-33: cursos asociados (solo lectura, forma compacta)
    courses = fields.List(
        fields.Nested(CourseCompactSchema),
        dump_only=True,
    )


class SkillQuerySchema(Schema):
    q = fields.Str()  # búsqueda por nombre
    is_active = fields.Bool()
    page = fields.Int(load_default=1)
    per_page = fields.Int(load_default=10)


class SkillListSchema(Schema):
    items = fields.List(fields.Nested(SkillSchema))
    total = fields.Int()
    page = fields.Int()
    per_page = fields.Int()


class SkillCompactSchema(Schema):
    id = fields.Int()
    nombre = fields.Str()