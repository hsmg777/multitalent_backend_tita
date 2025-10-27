# tests/test_ai_logic_minimal.py
# -----------------------------------------------------------------------------
# Pruebas unitarias minimalistas del flujo de "scoring IA" sin dependencias
# externas (sin Flask, sin DB, sin S3). Simulan la orquestación y verifican:
#   - Selección de ruta (v3 / v2 / legacy / v2 default)
#   - Que se llama a "save_result" con los campos esperados
#   - Orden básico del pipeline: fetch_text -> summarize -> score -> save
# -----------------------------------------------------------------------------

from dataclasses import dataclass
from typing import Callable, Dict, Any, List


@dataclass
class AIScoringService:
    """Servicio minimal para testear la lógica de orquestación del scoring."""
    fetch_text: Callable[[dict], str]
    summarize_cv_to_json: Callable[[str], dict]
    score_v3: Callable[[dict, dict, dict], dict]
    score_v2: Callable[[dict, dict, str], dict]
    score_legacy: Callable[[str, list, list, int, dict, str], dict]
    save_result: Callable[[Dict[str, Any]], None]

    def run(self, data: dict) -> dict:
        # 1) Extraer texto de CV
        text = self.fetch_text(data.get("cv") or {})

        # 2) Resumir a JSON estructurado
        cv_json = self.summarize_cv_to_json(text)

        # 3) Elegir ruta de scoring
        ap = data.get("applicant_profile")
        vp = data.get("vacancy_profile")

        if isinstance(ap, dict) and isinstance(vp, dict):
            result = self.score_v3(ap, vp, cv_json)
        elif isinstance(ap, dict) or isinstance(vp, dict):
            result = self.score_v2(ap or {}, vp or {}, text)
        elif data.get("position"):
            result = self.score_legacy(
                data["position"],
                data.get("required_skills", []),
                data.get("nice_to_haves", []),
                data.get("min_years_experience", 0),
                data.get("applicant", {}),
                text,
            )
        else:
            result = self.score_v2({}, {}, text)

        # 4) Guardar resultado (simulado)
        payload_to_save = {
            "postulation_id": data.get("postulation_id"),
            "vacancy_id": data.get("vacancy_id"),
            "score": result.get("score"),
            "feedback": result.get("feedback"),
        }
        self.save_result(payload_to_save)
        return payload_to_save


# ----------------------------------------------------------------------------- #
#                                TESTS                                           #
# ----------------------------------------------------------------------------- #

def _make_service(
    *,
    fetch_text=lambda cv: "TEXT",
    summarize=lambda t: {"skills": ["python"]},
    score_v3=lambda ap, vp, cvj: {"score": 95, "feedback": "ok v3"},
    score_v2=lambda ap, vp, t: {"score": 70, "feedback": "ok v2"},
    score_legacy=lambda p, r, n, m, a, t: {"score": 55, "feedback": "legacy"},
    sink_dict=None,
):
    sink = sink_dict if sink_dict is not None else {}
    return AIScoringService(
        fetch_text=fetch_text,
        summarize_cv_to_json=summarize,
        score_v3=score_v3,
        score_v2=score_v2,
        score_legacy=score_legacy,
        save_result=lambda r: sink.update(r),
    ), sink


def test_v3_happy():
    svc, saved = _make_service()
    out = svc.run({
        "postulation_id": 1,
        "vacancy_id": 10,
        "applicant_profile": {"age": 22},
        "vacancy_profile": {"location": "Quito"},
    })
    assert out["score"] == 95
    assert out["feedback"] == "ok v3"
    assert saved == out  # se guardó lo mismo que retorna


def test_v2_incomplete_profile():
    # Solo applicant_profile presente -> v2
    svc, saved = _make_service(
        score_v3=lambda *a, **k: {"score": -1, "feedback": "NO"},
        score_v2=lambda ap, vp, t: {"score": 72, "feedback": "ok v2 (incompleto)"},
    )
    out = svc.run({
        "postulation_id": 2,
        "vacancy_id": 10,
        "applicant_profile": {"age": 22},
        "vacancy_profile": None,
    })
    assert out["score"] == 72
    assert "incompleto" in out["feedback"]
    assert saved["postulation_id"] == 2 and saved["vacancy_id"] == 10


def test_legacy_when_position():
    # Sin perfiles pero con position -> legacy
    svc, saved = _make_service(
        score_v3=lambda *a, **k: {"score": -1},
        score_v2=lambda *a, **k: {"score": -1},
        score_legacy=lambda p, r, n, m, a, t: {"score": 60, "feedback": "legacy ok"},
    )
    out = svc.run({
        "postulation_id": 3,
        "vacancy_id": 10,
        "position": "Python Intern",
        "required_skills": ["python"],
    })
    assert out["score"] == 60
    assert out["feedback"] == "legacy ok"
    assert saved["score"] == 60


def test_v2_default_when_nothing():
    # Sin perfiles y sin position -> v2 por defecto
    svc, saved = _make_service(
        score_v3=lambda *a, **k: {"score": -1},
        score_v2=lambda ap, vp, t: {"score": 40, "feedback": "v2-default"},
        score_legacy=lambda *a, **k: {"score": -1},
    )
    out = svc.run({
        "postulation_id": 4,
        "vacancy_id": 10,
    })
    assert out["score"] == 40
    assert out["feedback"] == "v2-default"
    assert saved["postulation_id"] == 4


def test_pipeline_order_is_fetch_then_summarize_then_score_then_save():
    calls: List[str] = []

    def _fetch(cv):
        calls.append("fetch")
        return "TEXT"

    def _summarize(t):
        calls.append("summarize")
        return {"k": 1}

    def _score_v3(ap, vp, cvj):
        calls.append("score_v3")
        return {"score": 90, "feedback": "ok"}

    saved = {}
    svc = AIScoringService(
        fetch_text=_fetch,
        summarize_cv_to_json=_summarize,
        score_v3=_score_v3,
        score_v2=lambda *a, **k: {"score": -1},
        score_legacy=lambda *a, **k: {"score": -1},
        save_result=lambda r: (calls.append("save"), saved.update(r)),
    )

    svc.run({"postulation_id": 5, "vacancy_id": 10, "applicant_profile": {}, "vacancy_profile": {}})

    assert calls == ["fetch", "summarize", "score_v3", "save"]


def test_save_result_called_once_with_expected_fields():
    save_calls: List[Dict[str, Any]] = []

    svc, _ = _make_service(
        score_v3=lambda ap, vp, cvj: {"score": 88, "feedback": "v3-done"},
        sink_dict=None,
    )
    # Reemplazamos save_result para contar llamadas
    svc.save_result = lambda r: save_calls.append(r)

    payload = {"postulation_id": 9, "vacancy_id": 99, "applicant_profile": {}, "vacancy_profile": {}}
    out = svc.run(payload)

    assert len(save_calls) == 1
    saved = save_calls[0]
    assert set(saved.keys()) == {"postulation_id", "vacancy_id", "score", "feedback"}
    assert saved["postulation_id"] == 9 and saved["vacancy_id"] == 99
    assert out == saved


def test_errors_in_scorers_do_not_crash_when_handled_externally():
    # Si quieres demostrar manejo simple, puedes decidir capturar excepción aquí,
    # o dejar que explote. En este minimal test verificamos que si el scorer
    # lanza, la excepción burbujea (comportamiento explícito).
    svc, _ = _make_service(
        score_v3=lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    try:
        svc.run({"applicant_profile": {}, "vacancy_profile": {}})
        assert False, "Se esperaba RuntimeError"
    except RuntimeError as e:
        assert "boom" in str(e)
