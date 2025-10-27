# tests/admin/test_step3_personality.py
import pytest
from datetime import datetime, timedelta
from flask_jwt_extended import create_access_token

from app.models.web_portal.postulation import Postulation
from app.models.personality.attempt import PersonalityAttempt

# Fallback por si no está montado el guard/constante en este entorno
try:
    from app.resources.guards import DOC_PATH_REQUIRED
except Exception:  # pragma: no cover
    DOC_PATH_REQUIRED = "/terms/latest"

BASE = "/api/admin/steps/personality"


# -----------------------
# Auth headers (IDENTITY como STRING)
# -----------------------
@pytest.fixture()
def auth_headers(test_app):
    with test_app.app_context():
        token = create_access_token(
            identity="1",  # <- string, no dict
            additional_claims={"role": "admin", "uid": 1},
        )
    return {"Authorization": f"Bearer {token}"}


# -----------------------
# Aceptar términos AUTOUSE (si existe la ruta)
# -----------------------
@pytest.fixture(autouse=True)
def _accept_terms_autouse(client, auth_headers):
    try:
        r = client.post(
            "/api/terms/acceptances",
            json={"doc_path": DOC_PATH_REQUIRED},
            headers=auth_headers,
        )
        # 200 si ya existía, 201 si se creó, 404 si no montaste el blueprint de términos
        assert r.status_code in (200, 201, 404)
    except Exception:
        # Si no existe/está deshabilitado, ignorar
        pass
    yield


# -----------------------
# Parchear VALID_STATES AUTOUSE (añadir "personality_exam")
# -----------------------
@pytest.fixture(autouse=True)
def _patch_valid_states(monkeypatch):
    import app.resources.admin.steps.step3_personality as mod
    states = set(getattr(mod, "VALID_STATES", []))
    states.update({"personality_exam"})
    monkeypatch.setattr(mod, "VALID_STATES", states, raising=False)
    yield


# -----------------------
# Helpers / Dummies
# -----------------------
class DummyPostulation:
    def __init__(self, status: str):
        self.status = status


class DummyAttempt:
    def __init__(
        self,
        *,
        id=1,
        status="finished",
        duration_sec=None,
        started_at=None,
        finished_at=None,
        traits_json=None,
        overall_score=0.0,
        recommendation=None,
    ):
        self.id = id
        self.status = status
        self.duration_sec = duration_sec
        self.started_at = started_at
        self.finished_at = finished_at
        self.traits_json = traits_json
        self.overall_score = overall_score
        self.recommendation = recommendation


def stub_sa_queries(monkeypatch, postulations_by_id: dict[int, DummyPostulation], attempts_by_pid: dict[int, DummyAttempt]):
    """
    Monkeypatch de:
      - Postulation.query.get(pid) -> postulations_by_id.get(pid)
      - PersonalityAttempt.query.filter_by(postulation_id=pid).one_or_none() -> attempts_by_pid.get(pid)
    """

    class _PostulationQueryStub:
        @staticmethod
        def get(pid: int):
            return postulations_by_id.get(pid)

    class _AttemptQueryStub:
        def __init__(self, pid: int):
            self._pid = pid

        def one_or_none(self):
            return attempts_by_pid.get(self._pid)

    class _AttemptQueryProxy:
        @staticmethod
        def filter_by(**kwargs):
            pid = kwargs.get("postulation_id")
            return _AttemptQueryStub(pid)

    monkeypatch.setattr(Postulation, "query", _PostulationQueryStub)
    monkeypatch.setattr(PersonalityAttempt, "query", _AttemptQueryProxy)


# -----------------------
# Tests
# -----------------------

def test_404_not_found(client, auth_headers, monkeypatch):
    stub_sa_queries(monkeypatch, postulations_by_id={}, attempts_by_pid={})
    r = client.get(f"{BASE}/999", headers=auth_headers)
    assert r.status_code == 404
    assert r.json["message"] == "Postulación no encontrada"


def test_400_invalid_state(client, auth_headers, monkeypatch):
    pid = 1
    postulations = {pid: DummyPostulation(status="estado_raro")}
    stub_sa_queries(monkeypatch, postulations_by_id=postulations, attempts_by_pid={})
    r = client.get(f"{BASE}/{pid}", headers=auth_headers)
    assert r.status_code == 400
    assert "Estado inválido" in r.json["message"]


@pytest.mark.parametrize("status", ["submitted", "accepted", "prescreen_call"])
def test_locked_before_step(client, auth_headers, monkeypatch, status):
    pid = 2
    postulations = {pid: DummyPostulation(status=status)}
    stub_sa_queries(monkeypatch, postulations_by_id=postulations, attempts_by_pid={})
    r = client.get(f"{BASE}/{pid}", headers=auth_headers)
    assert r.status_code == 200
    body = r.json
    assert body["status"] == status
    assert body["view_state"] == "locked"
    assert body["results"] is None
    assert "Aún no corresponde revisar el examen" in body["message"]


def test_locked_terminal_rejected(client, auth_headers, monkeypatch):
    pid = 3
    postulations = {pid: DummyPostulation(status="rejected")}
    stub_sa_queries(monkeypatch, postulations_by_id=postulations, attempts_by_pid={})
    r = client.get(f"{BASE}/{pid}", headers=auth_headers)
    assert r.status_code == 200
    body = r.json
    assert body["status"] == "rejected"
    assert body["view_state"] == "locked"
    assert body["results"] is None
    assert "finalizado (rechazado)" in body["message"]


@pytest.mark.parametrize("att_status", [None, "created", "started"])
def test_pending_when_no_attempt_or_in_progress(client, auth_headers, monkeypatch, att_status):
    pid = 4
    postulations = {pid: DummyPostulation(status="personality_exam")}
    attempts = {}
    if att_status is not None:
        attempts[pid] = DummyAttempt(status=att_status)

    stub_sa_queries(monkeypatch, postulations_by_id=postulations, attempts_by_pid=attempts)
    r = client.get(f"{BASE}/{pid}", headers=auth_headers)
    assert r.status_code == 200
    body = r.json
    assert body["status"] == "personality_exam"
    assert body["view_state"] == "pending"
    assert body["results"] is None
    assert "aún no finaliza" in body["message"]


def test_locked_expired_with_results(client, auth_headers, monkeypatch):
    pid = 5
    postulations = {pid: DummyPostulation(status="personality_exam")}
    started = datetime(2025, 10, 1, 10, 0, 0)
    finished = started + timedelta(minutes=37)
    traits_payload = {"percents": {"A": 0.8, "B": 0.1, "C": 0.1}}
    attempts = {
        pid: DummyAttempt(
            id=77,
            status="expired",
            started_at=started,
            finished_at=finished,
            traits_json=traits_payload,
            overall_score=73.5,
            recommendation="Perfil compatible, pero expiró.",
        )
    }

    stub_sa_queries(monkeypatch, postulations_by_id=postulations, attempts_by_pid=attempts)
    r = client.get(f"{BASE}/{pid}", headers=auth_headers)
    assert r.status_code == 200
    body = r.json
    assert body["status"] == "personality_exam"
    assert body["view_state"] == "locked"
    assert "expiró por tiempo límite" in body["message"]

    res = body["results"]
    assert res["provider"] == "InHouse v1 (Excel fijo)"
    assert res["attempt_id"] == 77
    assert res["duration_minutes"] == 37
    # overall_score se serializa como entero
    assert res["overall_score"] == int(73.5)
    assert res["recommendation"] == "Perfil compatible, pero expiró."
    assert res["traits"] == {"A": 0.8, "B": 0.1, "C": 0.1}
    assert res["status"] == "expired"


def test_completed_with_results(client, auth_headers, monkeypatch):
    pid = 6
    postulations = {pid: DummyPostulation(status="personality_exam")}
    attempts = {
        pid: DummyAttempt(
            id=88,
            status="finished",
            duration_sec=125,  # → 2 minutos
            started_at=datetime(2025, 10, 2, 9, 0, 0),
            finished_at=datetime(2025, 10, 2, 9, 3, 0),
            traits_json={"X": 0.3, "Y": 0.7},
            overall_score=91.2,
            recommendation="Altamente recomendado",
        )
    }
    stub_sa_queries(monkeypatch, postulations_by_id=postulations, attempts_by_pid=attempts)

    r = client.get(f"{BASE}/{pid}", headers=auth_headers)
    assert r.status_code == 200
    body = r.json
    assert body["status"] == "personality_exam"
    assert body["view_state"] == "completed"
    assert "finalizó su examen" in body["message"]

    res = body["results"]
    assert res["attempt_id"] == 88
    assert res["duration_minutes"] == 2  # 125 // 60
    assert res["traits"] == {"X": 0.3, "Y": 0.7}
    # overall_score se serializa como entero
    assert res["overall_score"] == int(91.2)
    assert res["recommendation"] == "Altamente recomendado"
    assert res["status"] == "finished"
