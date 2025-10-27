# tests/web_portal/test_vacancies_public_api.py
import os
import uuid
from datetime import date, timedelta

from app import create_app

API_LOGIN = "/api/admin/auth/login"
API_CHARGES = "/api/admin/charges"
API_VACANCIES_ADMIN = "/api/admin/vacancies"
API_VACANCIES_PUBLIC = "/api/vacancies"

ADMIN_EMAIL = os.getenv("TEST_ADMIN_EMAIL", "admin@multiapoyo.com.ec")
ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "adminmulti007")


# ===== Helpers =====
def _make_client():
    app = create_app("dev")
    return app.test_client()


def _get_admin_token(client):
    resp = client.post(API_LOGIN, json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert resp.status_code == 200, f"Login admin falló: {resp.status_code} {resp.get_json()}"
    return resp.get_json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_charge(client, token, title=None, area="Comercial", description="desc"):
    if title is None:
        title = f"Charge-{uuid.uuid4().hex[:8]}"
    payload = {"title": title, "area": area, "description": description}
    r = client.post(f"{API_CHARGES}/", json=payload, headers=_auth(token))
    assert r.status_code == 201, f"Crear charge falló: {r.status_code} {r.get_json()}"
    return r.get_json()


def _create_vacancy(client, token, charge_id, days_from_today=10, location="Quito", modality="onsite"):
    payload = {
        "charge_id": charge_id,
        "title": f"Vac-{uuid.uuid4().hex[:6]}",
        "description": "desc",
        "location": location,
        "modality": modality,
        "apply_until": (date.today() + timedelta(days=days_from_today)).isoformat(),
        "headcount": 1,
    }
    r = client.post(f"{API_VACANCIES_ADMIN}/", json=payload, headers=_auth(token))
    assert r.status_code == 201, r.get_json()
    return r.get_json()


# ===== Tests =====
def test_public_listing_shows_only_published_active_and_not_expired():
    client = _make_client()
    token = _get_admin_token(client)
    ch = _create_charge(client, token, area="IT")

    # Crear dos vacantes: una será publicada (vigente), otra quedará draft
    v_pub = _create_vacancy(client, token, ch["id"], days_from_today=7, location="Quito", modality="onsite")
    v_draft = _create_vacancy(client, token, ch["id"], days_from_today=7, location="Guayaquil", modality="remote")

    # Publicar la primera
    r = client.post(f"{API_VACANCIES_ADMIN}/{v_pub['id']}/publish", headers=_auth(token))
    assert r.status_code == 200

    # Listado público: solo debe aparecer la publicada
    r = client.get(f"{API_VACANCIES_PUBLIC}/")
    assert r.status_code == 200
    data = r.get_json()
    ids = [it["id"] for it in data["items"]]
    assert v_pub["id"] in ids
    assert v_draft["id"] not in ids

    # Detalle público: la publicada responde 200
    r = client.get(f"{API_VACANCIES_PUBLIC}/{v_pub['id']}")
    assert r.status_code == 200

    # Detalle público: la draft responde 404
    r = client.get(f"{API_VACANCIES_PUBLIC}/{v_draft['id']}")
    assert r.status_code == 404

    # Cerrar la publicada → debe dejar de salir en público
    r = client.post(f"{API_VACANCIES_ADMIN}/{v_pub['id']}/close", headers=_auth(token))
    assert r.status_code == 200

    r = client.get(f"{API_VACANCIES_PUBLIC}/")
    assert r.status_code == 200
    ids = [it["id"] for it in r.get_json()["items"]]
    assert v_pub["id"] not in ids

    # Limpieza
    client.delete(f"{API_VACANCIES_ADMIN}/{v_pub['id']}", headers=_auth(token))
    client.delete(f"{API_VACANCIES_ADMIN}/{v_draft['id']}", headers=_auth(token))


def test_public_filters_area_modality_location_and_pagination():
    client = _make_client()
    token = _get_admin_token(client)

    ch_ops = _create_charge(client, token, area="Operaciones")
    ch_hr = _create_charge(client, token, area="RRHH")

    # Crear 3 vacantes y publicar 2
    v1 = _create_vacancy(client, token, ch_ops["id"], days_from_today=10, location="Quito", modality="onsite")
    v2 = _create_vacancy(client, token, ch_ops["id"], days_from_today=10, location="Remoto", modality="remote")
    v3 = _create_vacancy(client, token, ch_hr["id"], days_from_today=10, location="Quito", modality="hybrid")

    for v in (v1, v2, v3):
        client.post(f"{API_VACANCIES_ADMIN}/{v['id']}/publish", headers=_auth(token))

    try:
        # Filtro area=Operaciones
        r = client.get(f"{API_VACANCIES_PUBLIC}/?area=Operaciones")
        assert r.status_code == 200
        items = r.get_json()["items"]
        assert items and all(it["charge_id"] == ch_ops["id"] for it in items)

        # Filtro modality=remote
        r = client.get(f"{API_VACANCIES_PUBLIC}/?modality=remote")
        assert r.status_code == 200
        items = r.get_json()["items"]
        assert items and all(it["modality"] == "remote" for it in items)

        # Filtro location contains "Quito"
        r = client.get(f"{API_VACANCIES_PUBLIC}/?location=Quit")
        assert r.status_code == 200
        items = r.get_json()["items"]
        assert items and all("Quito" in (it["location"] or "") for it in items)

        # Paginación
        r = client.get(f"{API_VACANCIES_PUBLIC}/?per_page=2&page=1")
        assert r.status_code == 200
        meta = r.get_json()["meta"]
        assert meta["page"] == 1 and meta["per_page"] == 2
        assert len(r.get_json()["items"]) <= 2
    finally:
        # Cleanup
        for v in (v1, v2, v3):
            client.post(f"{API_VACANCIES_ADMIN}/{v['id']}/close", headers=_auth(token))
            client.delete(f"{API_VACANCIES_ADMIN}/{v['id']}", headers=_auth(token))
