# app/ext/db_types.py
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON as SA_JSON

def JSONBCompat_for(db):
    try:
        if db.engine and db.engine.url.get_backend_name() == "postgresql":
            return JSONB
    except Exception:
        pass
    return SA_JSON
