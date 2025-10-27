# tests/admin/test_vacancies_skill.py
import os
import uuid
from datetime import date, timedelta
from app import create_app

API_LOGIN = "/api/admin/auth/login"
API_SKILLS = "/api/admin/skills"
API_CHARGES = "/api/admin/charges"
API_VACANCIES = "/api/admin/vacancies"

# Si tu admin no es el default, sobreescribe por variables de entorno
ADMIN_EMAIL = os.getenv("TEST_ADMIN_EMAIL", "admin@multiapoyo.com.ec")
ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "adminmulti007")


def _make_client():
    app = create_app("dev")  # ajusta config si usas otro nombre de configuración
    return app.test_client()


def _get_admin_token(client):
    resp = client.post(API_LOGIN, json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert resp.status_code == 200, f"Login admin falló: {resp.status_code} {resp.get_json()}"
    return resp.get_json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_charge(client, token):
    """Crea un Charge mínimo para poder crear una Vacancy."""
    payload = {
        "title": f"Charge-{uuid.uuid4().hex[:8]}",
        "area": "Engineering",
        "description": "Charge creado por tests",  # <- requerido por tu schema
        # "is_active": True,  # <- quitar, no lo acepta el CreateSchema
    }
    r = client.post(f"{API_CHARGES}/", json=payload, headers=_auth(token))
    assert r.status_code in (200, 201), f"No se pudo crear Charge: {r.status_code} {r.get_json()}"
    return r.get_json()["id"]



def _create_skill(client, token, name_prefix="Skill"):
    payload = {"nombre": f"{name_prefix}-{uuid.uuid4().hex[:8]}", "nivel_minimo": 1, "is_active": True}
    r = client.post(f"{API_SKILLS}/", json=payload, headers=_auth(token))
    assert r.status_code == 201, f"No se pudo crear Skill: {r.status_code} {r.get_json()}"
    return r.get_json()


def _create_vacancy(client, token, charge_id):
    """Crea una Vacancy en draft con datos mínimos válidos."""
    payload = {
        "charge_id": charge_id,
        "title": f"Vac-{uuid.uuid4().hex[:8]}",
        "description": "Descripción de prueba",
        "apply_until": (date.today() + timedelta(days=30)).isoformat(),
        "location": "Quito",
        "modality": "hybrid",
        "headcount": 1,
        "tags": ["python", "flask"],
        # opcionales que tu schema permite; publish_at e is_active/status los maneja el backend
    }
    r = client.post(f"{API_VACANCIES}/", json=payload, headers=_auth(token))
    assert r.status_code == 201, f"No se pudo crear Vacancy: {r.status_code} {r.get_json()}"
    return r.get_json()


def _delete_vacancy(client, token, vacancy_id):
    client.delete(f"{API_VACANCIES}/{vacancy_id}", headers=_auth(token))


def _delete_skill(client, token, skill_id):
    client.delete(f"{API_SKILLS}/{skill_id}", headers=_auth(token))


def test_vacancy_skills_attach_and_list_enriched():
    """
    Happy path:
    - Crea charge, vacancy y 2 skills.
    - PUT asociaciones con metadatos (required_score, weight).
    - Verifica que GET /vacancies/<id>/skills devuelve objetos con `skill {id, nombre}`.
    - Reemplaza el set completo (PUT) y valida que se refleje el cambio.
    """
    client = _make_client()
    token = _get_admin_token(client)

    # Arrange: charge + vacancy + skills
    charge_id = _create_charge(client, token)
    vac = _create_vacancy(client, token, charge_id)
    vacancy_id = vac["id"]

    skill_a = _create_skill(client, token, "SkillA")
    skill_b = _create_skill(client, token, "SkillB")

    try:
        # Act: asociar ambas skills (PUT reemplaza set completo)
        payload = [
            {"skill_id": skill_a["id"], "required_score": 70, "weight": 0.5},
            {"skill_id": skill_b["id"]},  # sin metadatos opcionales
        ]
        r = client.put(f"{API_VACANCIES}/{vacancy_id}/skills", json=payload, headers=_auth(token))
        assert r.status_code == 200, r.get_json()
        items = r.get_json()["items"]
        assert len(items) == 2

        # Assert: cada item incluye skill_id y objeto `skill` con id y nombre
        ids = sorted([it["skill_id"] for it in items])
        assert ids == sorted([skill_a["id"], skill_b["id"]])
        for it in items:
            assert "skill" in it and it["skill"] is not None, "Debe traer objeto skill embebido"
            assert it["skill"]["id"] == it["skill_id"]
            assert isinstance(it["skill"]["nombre"], str) and len(it["skill"]["nombre"]) > 0

        # GET: comprobar que la lista se devuelve enriquecida (joinedload server-side)
        r = client.get(f"{API_VACANCIES}/{vacancy_id}/skills", headers=_auth(token))
        assert r.status_code == 200
        items = r.get_json()["items"]
        assert len(items) == 2
        for it in items:
            assert "skill" in it and it["skill"], "GET también debe venir enriquecido"

        # Reemplazar el set completo: dejar solo una skill
        payload = [{"skill_id": skill_a["id"], "required_score": 80}]
        r = client.put(f"{API_VACANCIES}/{vacancy_id}/skills", json=payload, headers=_auth(token))
        assert r.status_code == 200
        items = r.get_json()["items"]
        assert len(items) == 1
        only = items[0]
        assert only["skill_id"] == skill_a["id"]
        assert only["required_score"] == 80
        assert only["skill"]["id"] == skill_a["id"]
    finally:
        # Cleanup
        _delete_vacancy(client, token, vacancy_id)
        _delete_skill(client, token, skill_a["id"])
        _delete_skill(client, token, skill_b["id"])


def test_vacancy_skills_validation_and_uniqueness():
    """
    - required_score fuera de rango → 422 (schema valida 0..100).
    - weight negativo → 422.
    - Duplicar la misma skill en el payload → 400 (UniqueConstraint en DB).
    """
    client = _make_client()
    token = _get_admin_token(client)

    # Arrange
    charge_id = _create_charge(client, token)
    vac = _create_vacancy(client, token, charge_id)
    vacancy_id = vac["id"]
    skill = _create_skill(client, token, "SkillX")

    try:
        # required_score > 100 => 422
        bad_payload = [{"skill_id": skill["id"], "required_score": 200}]
        r = client.put(f"{API_VACANCIES}/{vacancy_id}/skills", json=bad_payload, headers=_auth(token))
        assert r.status_code == 422, f"Esperado 422 por required_score>100, fue {r.status_code}: {r.get_json()}"

        # weight < 0 => 422
        bad_payload = [{"skill_id": skill["id"], "weight": -0.1}]
        r = client.put(f"{API_VACANCIES}/{vacancy_id}/skills", json=bad_payload, headers=_auth(token))
        assert r.status_code == 422, f"Esperado 422 por weight<0, fue {r.status_code}: {r.get_json()}"

        # Duplicar la misma skill en el set => IntegrityError -> 400
        dup_payload = [
            {"skill_id": skill["id"], "required_score": 50},
            {"skill_id": skill["id"], "required_score": 60},
        ]
        r = client.put(f"{API_VACANCIES}/{vacancy_id}/skills", json=dup_payload, headers=_auth(token))
        assert r.status_code == 400, f"Esperado 400 por duplicado de skill_id, fue {r.status_code}: {r.get_json()}"

        # Finalmente, una asociación válida
        ok_payload = [{"skill_id": skill["id"], "required_score": 75, "weight": 0.3}]
        r = client.put(f"{API_VACANCIES}/{vacancy_id}/skills", json=ok_payload, headers=_auth(token))
        assert r.status_code == 200, r.get_json()
        items = r.get_json()["items"]
        assert len(items) == 1
        it = items[0]
        assert it["skill_id"] == skill["id"]
        assert it["required_score"] == 75
        assert it["weight"] == 0.3
        assert it["skill"]["id"] == skill["id"]
        assert isinstance(it["skill"]["nombre"], str) and it["skill"]["nombre"]
    finally:
        _delete_vacancy(client, token, vacancy_id)
        _delete_skill(client, token, skill["id"])


def test_vacancy_skills_listing_empty_then_add():
    """
    - Una vacante nueva no tiene asociaciones → GET devuelve lista vacía.
    - Luego se agregan asociaciones y GET refleja las nuevas filas.
    """
    client = _make_client()
    token = _get_admin_token(client)

    charge_id = _create_charge(client, token)
    vac = _create_vacancy(client, token, charge_id)
    vacancy_id = vac["id"]
    skill = _create_skill(client, token, "SkillEmpty")

    try:
        # GET vacío
        r = client.get(f"{API_VACANCIES}/{vacancy_id}/skills", headers=_auth(token))
        assert r.status_code == 200
        assert r.get_json()["items"] == []

        # Agregar 1 asociación
        payload = [{"skill_id": skill["id"]}]
        r = client.put(f"{API_VACANCIES}/{vacancy_id}/skills", json=payload, headers=_auth(token))
        assert r.status_code == 200
        items = r.get_json()["items"]
        assert len(items) == 1
        assert items[0]["skill_id"] == skill["id"]
        assert items[0]["skill"]["id"] == skill["id"]

        # GET refleja 1
        r = client.get(f"{API_VACANCIES}/{vacancy_id}/skills", headers=_auth(token))
        assert r.status_code == 200
        assert len(r.get_json()["items"]) == 1
    finally:
        _delete_vacancy(client, token, vacancy_id)
        _delete_skill(client, token, skill["id"])
