# app/resources/admin/steps/step3_personality.py
from datetime import datetime
from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask_jwt_extended import jwt_required
import json


from app.models.web_portal.postulation import Postulation
from app.models.personality.attempt import PersonalityAttempt
from app.schemas.personality.personality import AttemptResultSchema, AdminStep3ResponseSchema
from app.services.postulation_service import VALID_STATES

blp = Blueprint(
    "AdminStep3Personality",
    __name__,
    description="Admin: Step 3 - Examen de personalidad (solo lectura; real data)",
)

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

TERMINAL_STATES = {"rejected"}  

_results_schema = AttemptResultSchema()
_response_schema = AdminStep3ResponseSchema()

def _is_terminal(status: str) -> bool:
    return status in TERMINAL_STATES

def _attempt_to_results(att: PersonalityAttempt) -> dict | None:
    if not att:
        return None

    dur_min = None
    if att.duration_sec is not None:
        dur_min = max(att.duration_sec // 60, 0)
    elif att.started_at and att.finished_at:
        dur_min = max(int((att.finished_at - att.started_at).total_seconds()) // 60, 0)

    traits_src = att.traits_json or {}
    if isinstance(traits_src, str):
        try:
            traits_src = json.loads(traits_src)
        except Exception:
            traits_src = {}

    if isinstance(traits_src, dict):
        if "percents" in traits_src and isinstance(traits_src["percents"], dict):
            traits_flat = traits_src["percents"]
        else:
            traits_flat = traits_src if all(isinstance(v, (int, float)) for v in traits_src.values()) else {}
    else:
        traits_flat = {}

    data = {
        "provider": "InHouse v1 (Excel fijo)",
        "attempt_id": att.id,
        "started_at": att.started_at.isoformat() + "Z" if att.started_at else None,
        "finished_at": att.finished_at.isoformat() + "Z" if att.finished_at else None,
        "duration_minutes": dur_min,
        "overall_score": att.overall_score,
        "traits": traits_flat,  
        "notes": [],
        "recommendation": att.recommendation,
        "status": att.status,
    }
    return _results_schema.dump(data)

# -------------------------------------------------------------------
# GET: Estado del step y resultados (datos reales)
# -------------------------------------------------------------------

@blp.route("/personality/<int:pid>", methods=["GET"])
class AdminPersonalityView(MethodView):
    @jwt_required()
    def get(self, pid: int):
        p = Postulation.query.get(pid)
        if not p:
            abort(404, message="Postulación no encontrada")

        status = (p.status or "").lower()
        if status not in VALID_STATES:
            abort(400, message=f"Estado inválido: {status}")

        if status in ("submitted", "accepted", "prescreen_call"):
            return _response_schema.dump({
                "postulation_id": pid,
                "status": status,
                "view_state": "locked",
                "message": "Aún no corresponde revisar el examen de personalidad.",
                "results": None,
            }), 200

        if _is_terminal(status):
            return _response_schema.dump({
                "postulation_id": pid,
                "status": status,
                "view_state": "locked",
                "message": "El proceso está finalizado (rechazado).",
                "results": None,
            }), 200

        attempt = PersonalityAttempt.query.filter_by(postulation_id=pid).one_or_none()

        if not attempt or attempt.status in ("created", "started"):
            return _response_schema.dump({
                "postulation_id": pid,
                "status": status,
                "view_state": "pending",
                "message": "El postulante aún no finaliza su examen de personalidad.",
                "results": None,
            }), 200

        
        if attempt.status == "expired":
            return _response_schema.dump({
                "postulation_id": pid,
                "status": status,
                "view_state": "locked",
                "message": "El examen expiró por tiempo límite.",
                "results": _attempt_to_results(attempt),
            }), 200

        return _response_schema.dump({
            "postulation_id": pid,
            "status": status,
            "view_state": "completed",
            "message": "El postulante finalizó su examen de personalidad.",
            "results": _attempt_to_results(attempt),
        }), 200
