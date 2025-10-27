# tests/admin/test_courses.py
import os
import uuid
from app import create_app

API_LOGIN = "/api/admin/auth/login"
API_COURSES = "/api/admin/courses"

# Puedes sobreescribir estas credenciales con variables de entorno si tu admin no es el default
ADMIN_EMAIL = os.getenv("TEST_ADMIN_EMAIL", "admin@multiapoyo.com.ec")
ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "adminmulti007")


def _make_client():
    app = create_app("dev")  # ajusta si usas otro config_name
    return app.test_client()


def _get_admin_token(client):
    """Hace login con el admin existente y retorna el JWT (no crea admin)."""
    resp = client.post(API_LOGIN, json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert resp.status_code == 200, f"Login admin falló: {resp.status_code} {resp.get_json()}"
    return resp.get_json()["access_token"]


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_courses_crud_happy_path():
    client = _make_client()
    token = _get_admin_token(client)

    # --- CREATE ---
    unique_name = f"Curso-{uuid.uuid4().hex[:8]}"
    create_payload = {
        "nombre": unique_name,
        "descripcion": "Curso de prueba de CRUD",
        "url": "https://example.com/curso",
        "is_active": True,
    }
    r = client.post(f"{API_COURSES}/", json=create_payload, headers=_auth_header(token))
    assert r.status_code == 201, r.get_json()
    created = r.get_json()
    course_id = created["id"]
    assert created["nombre"] == unique_name
    assert created["url"] == "https://example.com/curso"
    assert created["is_active"] is True

    # --- GET BY ID ---
    r = client.get(f"{API_COURSES}/{course_id}", headers=_auth_header(token))
    assert r.status_code == 200
    got = r.get_json()
    assert got["id"] == course_id
    assert got["nombre"] == unique_name

    # --- LIST (q filter) ---
    q = unique_name.split("-")[0].lower()  # "curso"
    r = client.get(f"{API_COURSES}/?q={q}", headers=_auth_header(token))
    assert r.status_code == 200
    data = r.get_json()
    assert "items" in data and "total" in data
    assert any(item["id"] == course_id for item in data["items"])

    # --- PATCH (update nombre/descripcion/is_active/url) ---
    new_name = f"{unique_name}-updated"
    patch_payload = {
        "nombre": new_name,
        "descripcion": "Descripción actualizada",
        "url": "https://example.com/curso-actualizado",
        "is_active": False,
    }
    r = client.patch(f"{API_COURSES}/{course_id}", json=patch_payload, headers=_auth_header(token))
    assert r.status_code == 200
    updated = r.get_json()
    assert updated["nombre"] == new_name
    assert updated["url"] == "https://example.com/curso-actualizado"
    assert updated["is_active"] is False

    # --- DELETE ---
    r = client.delete(f"{API_COURSES}/{course_id}", headers=_auth_header(token))
    assert r.status_code == 204

    # --- GET 404 luego de eliminar ---
    r = client.get(f"{API_COURSES}/{course_id}", headers=_auth_header(token))
    assert r.status_code == 404


def test_courses_conflict_duplicate_name():
    client = _make_client()
    token = _get_admin_token(client)

    # Creamos curso A
    name_a = f"CursoA-{uuid.uuid4().hex[:6]}"
    r = client.post(
        f"{API_COURSES}/",
        json={"nombre": name_a, "descripcion": "A", "url": "https://a.com", "is_active": True},
        headers=_auth_header(token),
    )
    assert r.status_code == 201, r.get_json()
    course_a = r.get_json()
    course_a_id = course_a["id"]

    # Creamos curso B
    name_b = f"CursoB-{uuid.uuid4().hex[:6]}"
    r = client.post(
        f"{API_COURSES}/",
        json={"nombre": name_b, "descripcion": "B", "url": "https://b.com", "is_active": True},
        headers=_auth_header(token),
    )
    assert r.status_code == 201, r.get_json()
    course_b = r.get_json()
    course_b_id = course_b["id"]

    try:
        # Intentamos renombrar B a A -> debe chocar 409 por unicidad de nombre
        r = client.patch(
            f"{API_COURSES}/{course_b_id}",
            json={"nombre": name_a},
            headers=_auth_header(token),
        )
        assert r.status_code == 409, f"Debería ser 409, fue {r.status_code}: {r.get_json()}"
    finally:
        # Limpieza: borrar ambos cursos creados
        client.delete(f"{API_COURSES}/{course_a_id}", headers=_auth_header(token))
        client.delete(f"{API_COURSES}/{course_b_id}", headers=_auth_header(token))


def test_courses_list_filters_and_pagination():
    client = _make_client()
    token = _get_admin_token(client)

    # Crear algunos cursos para asegurar resultados
    created_ids = []
    try:
        for _ in range(3):
            name = f"Pag-{uuid.uuid4().hex[:6]}"
            r = client.post(
                f"{API_COURSES}/",
                json={"nombre": name, "descripcion": "Paginacion", "url": "https://pag.com", "is_active": True},
                headers=_auth_header(token),
            )
            assert r.status_code == 201
            created_ids.append(r.get_json()["id"])

        # Lista con filtro is_active=true y paginación per_page=2
        r = client.get(f"{API_COURSES}/?is_active=true&per_page=2&page=1", headers=_auth_header(token))
        assert r.status_code == 200
        data = r.get_json()
        assert "items" in data and "total" in data and "page" in data and "per_page" in data
        assert data["page"] == 1
        assert data["per_page"] == 2
        assert len(data["items"]) <= 2

    finally:
        # Limpieza
        for cid in created_ids:
            client.delete(f"{API_COURSES}/{cid}", headers=_auth_header(token))
