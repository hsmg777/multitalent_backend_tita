# app/schemas/admin/vacancy.py
from marshmallow import Schema, fields, validate, EXCLUDE
from ..common.fields import BulletsField, TagsListField


# =========================
#  Sub-schema: Skill compacta
# =========================
class SkillCompactSchema(Schema):
    id = fields.Int(dump_only=True)
    nombre = fields.Str(dump_only=True)


# =========================
#  Sub-schema: Skill link
# =========================
class VacancySkillSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int(dump_only=True)
    skill_id = fields.Int(required=True)

    required_score = fields.Int(
        required=False,
        allow_none=True,
        validate=validate.Range(min=0, max=100),
        metadata={"description": "Puntaje mínimo requerido para la skill (0-100)"},
    )
    weight = fields.Float(
        required=False,
        allow_none=True,
        validate=validate.Range(min=0),
        metadata={"description": "Ponderación opcional para ranking"},
    )

    created_at = fields.DateTime(dump_only=True)

    # Objeto skill embebido para enriquecer la respuesta
    skill = fields.Nested(SkillCompactSchema, dump_only=True)


# =========================
#  Schema principal (Admin)
# =========================
class VacancySchema(Schema):
    """
    Esquema de Vacantes para el panel Admin (CRUD).
    Mantiene compatibilidad con los tests y agrega
    campos opcionales de contenido estructurado para render
    “bonito” en el portal público (HiringRoom-like).

    NOTA:
    - Las listas enriquecidas usan BulletsField (acepta string con viñetas,
      listas de strings, objetos {text|label|value|insert}, y Quill delta).
    - `tags` usa TagsListField (acepta lista/objetos/string y almacena CSV).
    """
    class Meta:
        unknown = EXCLUDE  # Ignora silenciosamente campos desconocidos

    id = fields.Int(dump_only=True)

    # Relación con cargo
    charge_id = fields.Int(required=True)

    # Datos básicos
    title = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    description = fields.Str(required=True)  # texto libre (coexiste con secciones abajo)
    location = fields.Str(required=False, allow_none=True, validate=validate.Length(max=120))
    modality = fields.Str(
        required=False,
        allow_none=True,
        validate=validate.OneOf(["onsite", "hybrid", "remote"]),
    )

    # Publicación
    apply_until = fields.Date(required=True)
    publish_at = fields.DateTime(required=False, allow_none=True)

    # Estado/visibilidad (solo lectura aquí; se cambian con endpoints publish/close)
    is_active = fields.Bool(dump_only=True)
    status = fields.Str(
        dump_only=True,
        metadata={"description": "draft|published|closed|archived"},
    )

    # Operación
    headcount = fields.Int(
        required=False,
        dump_default=1,
        validate=validate.Range(min=1),
    )

    # Auditoría
    created_by = fields.Int(dump_only=True)
    updated_by = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    role_objective = fields.Str(
        required=False, allow_none=True,
        metadata={"description": "Párrafo de objetivo del rol"},
    )

    # Listas de bullets tolerantes (devuelven siempre list[str])
    responsibilities = BulletsField(
        allow_none=True,
        load_default=list,
        dump_default=list,
        metadata={"description": "Viñetas: responsabilidades"},
    )
    req_education = BulletsField(
        allow_none=True,
        load_default=list,
        dump_default=list,
        metadata={"description": "Viñetas: formación académica"},
    )
    req_experience = BulletsField(
        allow_none=True,
        load_default=list,
        dump_default=list,
        metadata={"description": "Viñetas: experiencia requerida"},
    )
    req_knowledge = BulletsField(
        allow_none=True,
        load_default=list,
        dump_default=list,
        metadata={"description": "Viñetas: conocimientos clave"},
    )
    benefits = BulletsField(
        allow_none=True,
        load_default=list,
        dump_default=list,
        metadata={"description": "Viñetas: beneficios"},
    )

    company_about = fields.Str(
        required=False, allow_none=True,
        metadata={"description": "Párrafo sobre la empresa (Nosotros)"},
    )

    # Etiquetas/chips: acepta CSV o lista; SIEMPRE devuelve list[str]
    tags = TagsListField(
        allow_none=True,
        load_default=list,
        dump_default=list,
        metadata={"description": "Etiquetas libres (chips)"},
    )

    hero_image_url = fields.Str(
        required=False, allow_none=True,
        validate=validate.Length(max=2000),
        metadata={"description": "URL opcional de imagen/cover"},
    )

    # Requisitos (skills asociadas) – solo lectura aquí
    requirements = fields.List(
        fields.Nested(VacancySkillSchema),
        dump_only=True,
        metadata={"description": "Skills asociadas a la vacante (N:N)"},
    )
