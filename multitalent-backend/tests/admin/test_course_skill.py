# tests/admin/test_course_skill.py
import os
import uuid
from app import create_app

API_LOGIN = "/api/admin/auth/login"
API_SKILLS = "/api/admin/skills"
API_COURSES = "/api/admin/courses"

# Si tu admin no es el default, puedes sobreescribir por variables de entorno
ADMIN_EMAIL = os.getenv("TEST_ADMIN_EMAIL", "admin@multiapoyo.com.ec")
ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "adminmulti007")


# ===== Helpers (mismo estilo que test_skills.py) =====

def _make_client():
    app = create_app("dev")  # misma config que usas en tus otros tests
    return app.test_client()


def _get_admin_token(client):
    resp = client.post(API_LOGIN, json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert resp.status_code == 200, f"Login admin falló: {resp.status_code} {resp.get_json()}"
    return resp.get_json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _rand_name(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _create_course(client, token, nombre=None, descripcion="desc test", is_active=True):
    if nombre is None:
        nombre = _rand_name("curso")
    payload = {"nombre": nombre, "descripcion": descripcion, "is_active": is_active}
    r = client.post(f"{API_COURSES}/", json=payload, headers=_auth(token))
    assert r.status_code == 201, f"Crear curso falló: {r.status_code} {r.get_json()}"
    return r.get_json()


def _create_skill(client, token, nombre=None, descripcion="desc skill", nivel_minimo=10, is_active=True):
    if nombre is None:
        nombre = _rand_name("skill")
    payload = {
        "nombre": nombre,
        "descripcion": descripcion,
        "nivel_minimo": nivel_minimo,
        "is_active": is_active,
    }
    r = client.post(f"{API_SKILLS}/", json=payload, headers=_auth(token))
    assert r.status_code == 201, f"Crear skill falló: {r.status_code} {r.get_json()}"
    return r.get_json()


# ===== Tests =====

def test_associate_course_to_skill_happy_path():
    client = _make_client()
    token = _get_admin_token(client)

    course = _create_course(client, token)
    skill = _create_skill(client, token)

    # Asociar (POST /api/admin/skills/<skill_id>/courses)
    r = client.post(
        f"{API_SKILLS}/{skill['id']}/courses",
        json={"course_ids": [course["id"]]},
        headers=_auth(token),
    )
    assert r.status_code == 201, r.get_data(as_text=True)
    data = r.get_json()
    assert isinstance(data, list) and data, "Respuesta debe ser lista no vacía"
    assert any(c["id"] == course["id"] for c in data)

    # Listar cursos de la skill (GET /skills/<id>/courses)
    r = client.get(f"{API_SKILLS}/{skill['id']}/courses", headers=_auth(token))
    assert r.status_code == 200
    listed = r.get_json()
    assert any(c["id"] == course["id"] for c in listed)

    # Detalle de skill debe incluir courses (SkillSchema.courses)
    r = client.get(f"{API_SKILLS}/{skill['id']}", headers=_auth(token))
    assert r.status_code == 200
    skill_detail = r.get_json()
    assert "courses" in skill_detail
    assert any(c["id"] == course["id"] for c in skill_detail["courses"])


def test_associate_duplicate_returns_409():
    client = _make_client()
    token = _get_admin_token(client)

    course = _create_course(client, token)
    skill = _create_skill(client, token)

    # Primera asociación OK
    r = client.post(
        f"{API_SKILLS}/{skill['id']}/courses",
        json={"course_ids": [course["id"]]},
        headers=_auth(token),
    )
    assert r.status_code == 201

    # Duplicado → 409
    r = client.post(
        f"{API_SKILLS}/{skill['id']}/courses",
        json={"course_ids": [course["id"]]},
        headers=_auth(token),
    )
    assert r.status_code == 409, f"Esperado 409 por duplicado, fue {r.status_code}: {r.get_json()}"


def test_delete_association_success_and_list_empty():
    client = _make_client()
    token = _get_admin_token(client)

    course = _create_course(client, token)
    skill = _create_skill(client, token)

    # Asociar
    r = client.post(
        f"{API_SKILLS}/{skill['id']}/courses",
        json={"course_ids": [course["id"]]},
        headers=_auth(token),
    )
    assert r.status_code == 201

    # Eliminar vínculo
    r = client.delete(
        f"{API_SKILLS}/{skill['id']}/courses/{course['id']}",
        headers=_auth(token),
    )
    assert r.status_code == 204

    # Listar debe quedar vacío de ese curso
    r = client.get(f"{API_SKILLS}/{skill['id']}/courses", headers=_auth(token))
    assert r.status_code == 200
    listed = r.get_json()
    assert all(c["id"] != course["id"] for c in listed)


def test_delete_non_associated_returns_404():
    client = _make_client()
    token = _get_admin_token(client)

    course = _create_course(client, token)
    skill = _create_skill(client, token)

    # Intentar borrar vínculo inexistente → 404
    r = client.delete(
        f"{API_SKILLS}/{skill['id']}/courses/{course['id']}",
        headers=_auth(token),
    )
    assert r.status_code == 404


def test_associate_nonexistent_course_returns_404():
    client = _make_client()
    token = _get_admin_token(client)
    skill = _create_skill(client, token)

    # ID de curso que no existe
    r = client.post(
        f"{API_SKILLS}/{skill['id']}/courses",
        json={"course_ids": [999_999]},
        headers=_auth(token),
    )
    assert r.status_code == 404


def test_associate_to_nonexistent_skill_returns_404():
    client = _make_client()
    token = _get_admin_token(client)
    course = _create_course(client, token)

    # skill inexistente
    r = client.post(
        f"{API_SKILLS}/999999/courses",
        json={"course_ids": [course["id"]]},
        headers=_auth(token),
    )
    assert r.status_code == 404
