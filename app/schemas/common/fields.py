# app/schemas/common/fields.py
import re
from marshmallow import fields, ValidationError

_BULLET_RE = re.compile(r'^\s*(?:[•\-\*\u2022]+|\d+[\.\)])\s*')

def _strip_bullet(s: str) -> str:
    s = s.strip()
    s = _BULLET_RE.sub('', s)
    return s.strip()

def _coerce_textish(item):
    if item is None:
        return None
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        for key in ("text", "value", "label", "name", "content", "title", "insert"):
            v = item.get(key)
            if isinstance(v, str):
                return v
        return str(item)
    return str(item)


class BulletsField(fields.Field):
    """
    Acepta:
      - string con saltos de línea y viñetas ("•", "-", "*", "1. ")
      - lista de strings
      - lista de objetos {text|value|label|name|content|title|insert}
      - Quill delta { ops: [{insert:"..."}] }
    Devuelve SIEMPRE: list[str] (sin viñetas, sin vacíos)
    """
    def _deserialize(self, value, attr, data, **kwargs):
        out = []

        # Quill delta {ops:[{insert:"texto\n"}]}
        if isinstance(value, dict) and "ops" in value:
            text = "".join(op.get("insert", "") for op in value.get("ops", []) if isinstance(op, dict))
            value = text

        if value is None or value == "":
            return []

        if isinstance(value, str):
            lines = re.split(r"\r?\n", value)
            out = [_strip_bullet(x) for x in lines if _strip_bullet(x)]
            return out

        if isinstance(value, list):
            for it in value:
                s = _coerce_textish(it)
                if not isinstance(s, str):
                    continue
                s = _strip_bullet(s)
                if s:
                    # si viene con comas o saltos, también los separamos
                    parts = re.split(r"[\r\n]+", s)
                    for p in parts:
                        pp = _strip_bullet(p)
                        if pp:
                            out.append(pp)
            return out

        raise ValidationError("Formato inválido para lista de viñetas")

    def _serialize(self, value, attr, obj, **kwargs):
        if not value:
            return []
        if isinstance(value, list):
            return [_strip_bullet(_coerce_textish(x) or "") for x in value if _strip_bullet(_coerce_textish(x) or "")]
        if isinstance(value, str):
            return [_strip_bullet(x) for x in re.split(r"\r?\n", value) if _strip_bullet(x)]
        return []

class TagsListField(fields.Field):
    """Acepta 'a, b, c' o ['a','b','c'] al cargar; siempre serializa como list[str]."""
    default_error_messages = {
        "invalid": "tags debe ser string CSV o lista de strings",
    }

    def _deserialize(self, value, attr, data, **kwargs):
        if value is None:
            return []
        if isinstance(value, str):
            return [t.strip() for t in value.split(",") if t.strip()]
        if isinstance(value, (list, tuple, set)):
            return [str(t).strip() for t in value if str(t).strip()]
        self.fail("invalid")

    def _serialize(self, value, attr, obj, **kwargs):
        if not value:
            return []
        if isinstance(value, str):
            # por si en DB quedó string antiguo:
            return [t.strip() for t in value.split(",") if t.strip()]
        if isinstance(value, (list, tuple, set)):
            return [str(t) for t in value]
        # caso raro: forzamos lista vacía
        return []


class TagsCSVField(fields.Field):
    """
    Acepta:
      - string "tag1, tag2; tag3"
      - lista de strings
      - lista de objetos {text|value|label|name}
    Devuelve: string CSV normalizado "tag1, tag2, tag3"
    """
    def _deserialize(self, value, attr, data, **kwargs):
        def one(x):
            if x is None:
                return None
            if isinstance(x, str):
                return x
            if isinstance(x, dict):
                for k in ("text", "value", "label", "name"):
                    v = x.get(k)
                    if isinstance(v, str):
                        return v
                return str(x)
            return str(x)

        if value is None or value == "":
            return ""

        raw = []
        if isinstance(value, str):
            raw = value.replace(";", ",").split(",")
        elif isinstance(value, list):
            for it in value:
                s = one(it)
                if s:
                    raw += s.replace(";", ",").split(",")
        else:
            s = one(value)
            if s:
                raw = s.replace(";", ",").split(",")

        cleaned = []
        seen = set()
        for t in (p.strip() for p in raw):
            if not t:
                continue
            key = t.lower()
            if key not in seen:
                seen.add(key)
                cleaned.append(t)

        return ", ".join(cleaned)

    def _serialize(self, value, attr, obj, **kwargs):
        if not value:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return ", ".join(str(x).strip() for x in value if str(x).strip())
        return str(value)

    
