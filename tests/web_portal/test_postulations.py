# tests/web_portal/test_postulations.py
from datetime import datetime, timedelta, date
from uuid import uuid4
import pytest
from flask_jwt_extended import create_access_token

from app.ext.db import db
from app.models.web_portal.postulation import Postulation
from app.models.admin.vacancy import Vacancy
from app.models.admin.charges import Charges  # ✅ import verificado
from app.models.web_portal.applicant import Applicant
from tests.factories import make_applicant

API_BASE = "/api"  # si registraste con "/api/web", cambia a "/api/web"

# --------- helpers ---------
@pytest.fixture()
def applicant(app_ctx):
    # generamos email/username únicos para evitar UNIQUE(email)
    return make_applicant(
        email=f"aspirante+{uuid4().hex[:8]}@test.com",
        username=f"asp_{uuid4().hex[:6]}",
    )

@pytest.fixture()
def auth_headers(test_app, applicant):
    # identity es string; en el recurso lo casteas a int
    token = create_access_token(identity=str(applicant.id))
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture()
def charge(app_ctx):
    """
    Crea un registro Charges compatible con distintos esquemas:
      - Usa el campo de nombre que exista: name / nombre / title
      - Rellena campos NOT NULL comunes como description (y area si existe)
      - Setea is_active=True si el modelo lo tiene
    """
    kwargs = {}

    # nombre/título
    if hasattr(Charges, "name"):
        kwargs["name"] = f"Dev JR {uuid4().hex[:6]}"
    elif hasattr(Charges, "nombre"):
        kwargs["nombre"] = f"Dev JR {uuid4().hex[:6]}"
    elif hasattr(Charges, "title"):
        kwargs["title"] = f"Dev JR {uuid4().hex[:6]}"

    # posibles columnas adicionales
    if hasattr(Charges, "area"):
        kwargs["area"] = "General"
    if hasattr(Charges, "description"):
        kwargs["description"] = "Cargo de prueba para tests"

    c = Charges(**kwargs)

    if hasattr(Charges, "is_active"):
        setattr(c, "is_active", True)

    db.session.add(c)
    db.session.commit()
    return c

@pytest.fixture()
def published_vacancy(app_ctx, charge):
    v = Vacancy(
        title="Dev JR",
        description="Vacante publicada de prueba",  # ✅ NOT NULL
        status="published",        # requerido por el recurso
        is_active=True,            # requerido por el recurso
        charge_id=charge.id,       # 👈 requerido
        publish_at=None,           # ya publicada
        apply_until=date.today() + timedelta(days=7),
    )
    db.session.add(v)
    db.session.commit()
    return v

@pytest.fixture()
def draft_vacancy(app_ctx, charge):
    v = Vacancy(
        title="Draft role",
        description="Vacante en borrador para pruebas",  # ✅ NOT NULL
        status="draft",
        is_active=True,
        charge_id=charge.id,       # 👈
        publish_at=None,
        apply_until=date.today() + timedelta(days=7),
    )
    db.session.add(v)
    db.session.commit()
    return v

@pytest.fixture()
def future_vacancy(app_ctx, charge):
    v = Vacancy(
        title="Future role",
        description="Vacante futura aún no habilitada",  # ✅ NOT NULL
        status="published",
        is_active=True,
        charge_id=charge.id,       # 👈
        publish_at=datetime.utcnow() + timedelta(days=2),   # aún no abre
        apply_until=date.today() + timedelta(days=10),
    )
    db.session.add(v)
    db.session.commit()
    return v

@pytest.fixture()
def expired_vacancy(app_ctx, charge):
    v = Vacancy(
        title="Expired role",
        description="Vacante expirada de prueba",  # ✅ NOT NULL
        status="published",
        is_active=True,
        charge_id=charge.id,       # 👈
        publish_at=None,
        apply_until=date.today() - timedelta(days=1),       # vencida
    )
    db.session.add(v)
    db.session.commit()
    return v

@pytest.fixture()
def cv_payload(published_vacancy):
    # payload mínimo válido
    return {
        "vacancy_id": published_vacancy.id,
        "residence_addr": "Quito",
        "credential": "CI",
        "number": "1717171717",
        "age": 24,
        "role_exp_years": 1,
        "expected_salary": 800,
        "cv_path": "https://s3.aws/mybucket/curriculums/abc.pdf",
    }

# --------- POST /postulations ----------
def test_postulation_create_ok(client, auth_headers, cv_payload):
    r = client.post(f"{API_BASE}/postulations", json=cv_payload, headers=auth_headers)
    assert r.status_code == 201
    body = r.get_json()
    assert body["vacancy_id"] == cv_payload["vacancy_id"]
    assert body["status"] == "submitted"

def test_postulation_duplicate_409(client, auth_headers, cv_payload, app_ctx):
    r1 = client.post(f"{API_BASE}/postulations", json=cv_payload, headers=auth_headers)
    assert r1.status_code == 201
    r2 = client.post(f"{API_BASE}/postulations", json=cv_payload, headers=auth_headers)
    assert r2.status_code == 409
    assert "ya has postulado" in r2.get_json()["message"].lower()

def test_postulation_rejected_draft_400(client, auth_headers, draft_vacancy, cv_payload):
    bad = dict(cv_payload, vacancy_id=draft_vacancy.id)
    r = client.post(f"{API_BASE}/postulations", json=bad, headers=auth_headers)
    assert r.status_code == 400

def test_postulation_rejected_future_400(client, auth_headers, future_vacancy, cv_payload):
    bad = dict(cv_payload, vacancy_id=future_vacancy.id)
    r = client.post(f"{API_BASE}/postulations", json=bad, headers=auth_headers)
    assert r.status_code == 400
    assert "aún no" in r.get_json()["message"].lower()

def test_postulation_rejected_expired_400(client, auth_headers, expired_vacancy, cv_payload):
    bad = dict(cv_payload, vacancy_id=expired_vacancy.id)
    r = client.post(f"{API_BASE}/postulations", json=bad, headers=auth_headers)
    assert r.status_code == 400
    assert "no acepta postulaciones" in r.get_json()["message"].lower()

# --------- GET /postulations (list mine) ----------
def test_list_my_postulations(client, auth_headers, cv_payload):
    r1 = client.post(f"{API_BASE}/postulations", json=cv_payload, headers=auth_headers)
    assert r1.status_code == 201

    r = client.get(f"{API_BASE}/postulations", headers=auth_headers)
    assert r.status_code == 200
    items = r.get_json()
    assert isinstance(items, list)
    assert len(items) == 1
    assert items[0]["vacancy_id"] == cv_payload["vacancy_id"]

# --------- GET /postulations/<id> ----------
def test_get_my_postulation_by_id_ok(client, auth_headers, cv_payload):
    created = client.post(f"{API_BASE}/postulations", json=cv_payload, headers=auth_headers).get_json()
    pid = created["id"]
    r = client.get(f"{API_BASE}/postulations/{pid}", headers=auth_headers)
    assert r.status_code == 200
    assert r.get_json()["id"] == pid

def test_get_postulation_403_other_user(client, test_app, auth_headers, cv_payload, app_ctx):
    other = Applicant(
        username=f"otro_{uuid4().hex[:6]}",
        email=f"otro+{uuid4().hex[:8]}@test.com",
        nombre="O", apellido="U", numero="099"
    )
    other.set_password("Clave#123")
    other.normalize()
    db.session.add(other); db.session.commit()

    other_headers = {"Authorization": f"Bearer {create_access_token(identity=str(other.id))}"}

    created = client.post(f"{API_BASE}/postulations", json=cv_payload, headers=other_headers).get_json()
    pid = created["id"]

    r = client.get(f"{API_BASE}/postulations/{pid}", headers=auth_headers)
    assert r.status_code == 403

# --------- PATCH /postulations/<id> ----------
def test_patch_postulation_updates_fields(client, auth_headers, cv_payload):
    created = client.post(f"{API_BASE}/postulations", json=cv_payload, headers=auth_headers).get_json()
    pid = created["id"]

    patch_data = {"expected_salary": 900, "status": "reviewing"}
    r = client.patch(f"{API_BASE}/postulations/{pid}", json=patch_data, headers=auth_headers)
    assert r.status_code == 200
    body = r.get_json()
    assert body["expected_salary"] == 900
    assert body["status"] == "reviewing"

# --------- DELETE /postulations/<id> ----------
def test_delete_postulation_removes_and_deletes_cv(client, auth_headers, cv_payload, monkeypatch):
    # mock de funciones S3
    calls = {"deleted": False, "extracted": None}

    def fake_extract(path):
        calls["extracted"] = "curriculums/abc.pdf"
        return calls["extracted"]

    def fake_delete(key):
        calls["deleted"] = (key == "curriculums/abc.pdf")

    import app.resources.web_portal.postulation as post_mod
    monkeypatch.setattr(post_mod, "extract_key_from_cv_path", fake_extract)
    monkeypatch.setattr(post_mod, "delete_cv_key", fake_delete)

    created = client.post(f"{API_BASE}/postulations", json=cv_payload, headers=auth_headers).get_json()
    pid = created["id"]

    r = client.delete(f"{API_BASE}/postulations/{pid}", headers=auth_headers)
    assert r.status_code == 204
    # validamos que se intentó borrar el CV en S3
    assert calls["extracted"] == "curriculums/abc.pdf"
    assert calls["deleted"] is True

    # ya no debe existir en BD
    with client.application.app_context():
        assert db.session.get(Postulation, pid) is None

# --------- Helper: GET /postulations/by-vacancy/<id>/me ----------
def test_get_by_vacancy_me_ok(client, auth_headers, cv_payload):
    created = client.post(f"{API_BASE}/postulations", json=cv_payload, headers=auth_headers).get_json()
    vac_id = created["vacancy_id"]

    r = client.get(f"{API_BASE}/postulations/by-vacancy/{vac_id}/me", headers=auth_headers)
    assert r.status_code == 200
    assert r.get_json()["id"] == created["id"]

def test_get_by_vacancy_me_404(client, auth_headers, published_vacancy):
    r = client.get(f"{API_BASE}/postulations/by-vacancy/{published_vacancy.id}/me", headers=auth_headers)
    assert r.status_code == 404
