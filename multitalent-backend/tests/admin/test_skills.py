# tests/admin/test_skills.py
import os
import uuid
from app import create_app

API_LOGIN = "/api/admin/auth/login"
API_SKILLS = "/api/admin/skills"

# Si tu admin no es el default, sobreescribe por variables de entorno
ADMIN_EMAIL = os.getenv("TEST_ADMIN_EMAIL", "admin@multiapoyo.com.ec")
ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "adminmulti007")


def _make_client():
    app = create_app("dev")  # ajusta config si usas otro nombre
    return app.test_client()


def _get_admin_token(client):
    resp = client.post(API_LOGIN, json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert resp.status_code == 200, f"Login admin falló: {resp.status_code} {resp.get_json()}"
    return resp.get_json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_skills_crud_happy_path():
    client = _make_client()
    token = _get_admin_token(client)

    # CREATE
    unique_name = f"Skill-{uuid.uuid4().hex[:8]}"
    payload = {"nombre": unique_name, "descripcion": "Desc", "nivel_minimo": 5, "is_active": True}
    r = client.post(f"{API_SKILLS}/", json=payload, headers=_auth(token))
    assert r.status_code == 201, r.get_json()
    created = r.get_json()
    skill_id = created["id"]
    assert created["nombre"] == unique_name
    assert created["nivel_minimo"] == 5

    # GET by ID
    r = client.get(f"{API_SKILLS}/{skill_id}", headers=_auth(token))
    assert r.status_code == 200
    got = r.get_json()
    assert got["id"] == skill_id

    # LIST (q filter)
    r = client.get(f"{API_SKILLS}/?q=skill", headers=_auth(token))
    assert r.status_code == 200
    data = r.get_json()
    assert any(item["id"] == skill_id for item in data["items"])

    # PATCH
    r = client.patch(
        f"{API_SKILLS}/{skill_id}",
        json={"nombre": f"{unique_name}-updated", "descripcion": "Nueva", "nivel_minimo": 10, "is_active": False},
        headers=_auth(token),
    )
    assert r.status_code == 200
    updated = r.get_json()
    assert updated["nombre"].endswith("-updated")
    assert updated["nivel_minimo"] == 10
    assert updated["is_active"] is False

    # DELETE
    r = client.delete(f"{API_SKILLS}/{skill_id}", headers=_auth(token))
    assert r.status_code == 204

    # GET after delete → 404
    r = client.get(f"{API_SKILLS}/{skill_id}", headers=_auth(token))
    assert r.status_code == 404


def test_skills_conflict_duplicate_name():
    client = _make_client()
    token = _get_admin_token(client)

    # Crear A
    name_a = f"SkillA-{uuid.uuid4().hex[:6]}"
    r = client.post(f"{API_SKILLS}/", json={"nombre": name_a, "nivel_minimo": 1}, headers=_auth(token))
    assert r.status_code == 201
    a_id = r.get_json()["id"]

    # Crear B
    name_b = f"SkillB-{uuid.uuid4().hex[:6]}"
    r = client.post(f"{API_SKILLS}/", json={"nombre": name_b, "nivel_minimo": 1}, headers=_auth(token))
    assert r.status_code == 201
    b_id = r.get_json()["id"]

    try:
        # Renombrar B → A (conflicto)
        r = client.patch(f"{API_SKILLS}/{b_id}", json={"nombre": name_a}, headers=_auth(token))
        assert r.status_code == 409, f"Esperado 409, fue {r.status_code}: {r.get_json()}"
    finally:
        client.delete(f"{API_SKILLS}/{a_id}", headers=_auth(token))
        client.delete(f"{API_SKILLS}/{b_id}", headers=_auth(token))


def test_skills_validation_nivel_minimo_range_and_pagination():
    client = _make_client()
    token = _get_admin_token(client)

    # Nivel fuera de rango → 400 (schemas validan 1..100)
    r = client.post(f"{API_SKILLS}/", json={"nombre": f"Bad-{uuid.uuid4().hex[:4]}", "nivel_minimo": 0}, headers=_auth(token))
    assert r.status_code == 422

    # Crear algunos para paginación
    ids = []
    try:
        for _ in range(3):
            name = f"Pag-{uuid.uuid4().hex[:6]}"
            r = client.post(f"{API_SKILLS}/", json={"nombre": name, "nivel_minimo": 1, "is_active": True}, headers=_auth(token))
            assert r.status_code == 201
            ids.append(r.get_json()["id"])

        r = client.get(f"{API_SKILLS}/?is_active=true&per_page=2&page=1", headers=_auth(token))
        assert r.status_code == 200
        data = r.get_json()
        assert data["page"] == 1
        assert data["per_page"] == 2
        assert len(data["items"]) <= 2
    finally:
        for sid in ids:
            client.delete(f"{API_SKILLS}/{sid}", headers=_auth(token))
