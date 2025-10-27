# app/schemas/web_portal/vacancy.py
from marshmallow import Schema, fields, EXCLUDE


class ChargeCompactSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int()
    title = fields.Str()
    area = fields.Str(allow_none=True)  # útil en detalle


class VacancySkillPublicSchema(Schema):
    """Fila pública de la relación VacancySkill."""
    class Meta:
        unknown = EXCLUDE

    skill_id = fields.Int()
    # El nombre de la skill viene en obj.skill.nombre
    nombre = fields.Method("get_skill_name", dump_only=True)
    required_score = fields.Int(allow_none=True, dump_default=None)
    weight = fields.Float(allow_none=True, dump_default=None)

    def get_skill_name(self, obj):
        s = getattr(obj, "skill", None)
        return getattr(s, "nombre", None) if s is not None else None


class PublicVacancySchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int(dump_only=True)

    # Relación con cargo
    charge_id = fields.Int(dump_only=True)
    charge = fields.Nested(ChargeCompactSchema, attribute="charge", dump_only=True)

    # ---- Claves en INGLÉS (tests/FE) ----
    title = fields.Str(dump_only=True)
    description = fields.Str(dump_only=True)
    location = fields.Str(dump_only=True, allow_none=True, dump_default=None)
    modality = fields.Str(dump_only=True, allow_none=True, dump_default=None)

    # area tomada del cargo
    area = fields.Method("get_area", dump_only=True)

    # Fechas clave
    apply_until = fields.Date(dump_only=True, allow_none=True, dump_default=None)
    publish_at = fields.DateTime(dump_only=True, allow_none=True, dump_default=None)

    # Cupos / estado / auditoría
    headcount = fields.Int(dump_only=True, allow_none=True, dump_default=None)
    status = fields.Str(dump_only=True)
    created_at = fields.DateTime(dump_only=True)

    # Requisitos/skills asociados (serializa objetos VacancySkill)
    # "requirements" queda por compatibilidad; también exponemos "skills".
    requirements = fields.List(
        fields.Nested(VacancySkillPublicSchema),
        attribute="skills",
        dump_only=True,
        metadata={"description": "Resumen de skills requeridas"},
    )
    skills = fields.List(fields.Nested(VacancySkillPublicSchema), dump_only=True)

    # ---- Contenido “rico” opcional (si existe en el modelo) ----
    role_objective   = fields.Str(dump_only=True, allow_none=True, dump_default=None)
    responsibilities = fields.List(fields.Str(), dump_only=True, dump_default=list)
    req_education    = fields.List(fields.Str(), dump_only=True, dump_default=list)
    req_experience   = fields.List(fields.Str(), dump_only=True, dump_default=list)
    req_knowledge    = fields.List(fields.Str(), dump_only=True, dump_default=list)
    benefits         = fields.List(fields.Str(), dump_only=True, dump_default=list)
    company_about    = fields.Str(dump_only=True, allow_none=True, dump_default=None)
    hero_image_url   = fields.Str(dump_only=True, allow_none=True, dump_default=None)

    # tags: si no hay columna, se infiere de los nombres de skills
    # Devolvemos SIEMPRE list[str] al frontend.
    tags = fields.Method("get_tags", dump_only=True)

    # ---- Alias en ESPAÑOL para el frontend ----
    titulo      = fields.Str(attribute="title", dump_only=True)
    descripcion = fields.Str(attribute="description", dump_only=True)
    ciudad      = fields.Str(attribute="location", dump_only=True, allow_none=True, dump_default=None)
    modalidad   = fields.Str(attribute="modality", dump_only=True, allow_none=True, dump_default=None)

    # ==== helpers ====
    def get_area(self, obj):
        ch = getattr(obj, "charge", None)
        return getattr(ch, "area", None) if ch is not None else None

    def get_tags(self, obj):
        """
        Normaliza tags a list[str]:
          - Si viene como lista/tupla: dedup y trim.
          - Si viene como string CSV: separa por coma/; y trim.
          - Si no hay, deriva de nombres de skills.
        """
        val = getattr(obj, "tags", None)

        # Caso string CSV ("growth, analytics; fintech")
        if isinstance(val, str):
            raw = val.replace(";", ",").split(",")
            out, seen = [], set()
            for t in (p.strip() for p in raw):
                if not t:
                    continue
                k = t.lower()
                if k not in seen:
                    seen.add(k)
                    out.append(t)
            return out

        # Caso lista/tupla
        if isinstance(val, (list, tuple)):
            out, seen = [], set()
            for x in val:
                s = str(x).strip()
                if not s:
                    continue
                k = s.lower()
                if k not in seen:
                    seen.add(k)
                    out.append(s)
            return out

        # Fallback: nombres de skills
        skills = getattr(obj, "skills", None) or []
        names = []
        for vs in skills:
            s = getattr(vs, "skill", None)
            name = getattr(s, "nombre", None) if s is not None else None
            if name:
                names.append(name)

        # Únicos preservando orden
        seen, out = set(), []
        for n in names:
            if n not in seen:
                seen.add(n)
                out.append(n)
        return out


class PublicVacancyListSchema(PublicVacancySchema):
    """Schema para listados públicos (hereda todos los campos)."""
    pass
