# tests/admin/test_vacancies_api.py
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


def _make_client():
    app = create_app("dev")
    return app.test_client()


def _get_admin_token(client):
    r = client.post(API_LOGIN, json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"Login admin falló: {r.status_code} {r.get_json()}"
    return r.get_json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_charge(client, token, title=None, area="Operaciones", description="desc"):
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


def test_admin_vacancy_crud_and_publish_close_flow():
    client = _make_client()
    token = _get_admin_token(client)

    ch = _create_charge(client, token, area="IT")

    # CREATE
    v = _create_vacancy(client, token, ch["id"], days_from_today=7, location="Quito", modality="onsite")
    vid = v["id"]

    # GET by ID
    r = client.get(f"{API_VACANCIES_ADMIN}/{vid}", headers=_auth(token))
    assert r.status_code == 200

    # PATCH (update título y headcount)
    new_title = v["title"] + "-upd"
    r = client.patch(
        f"{API_VACANCIES_ADMIN}/{vid}",
        json={"title": new_title, "headcount": 2},
        headers=_auth(token),
    )
    assert r.status_code == 200
    assert r.get_json()["title"] == new_title
    assert r.get_json()["headcount"] == 2

    # PUBLISH
    r = client.post(f"{API_VACANCIES_ADMIN}/{vid}/publish", headers=_auth(token))
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "published"
    assert body["is_active"] is True

    # CLOSE
    r = client.post(f"{API_VACANCIES_ADMIN}/{vid}/close", headers=_auth(token))
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "closed"
    assert body["is_active"] is False

    # DELETE
    r = client.delete(f"{API_VACANCIES_ADMIN}/{vid}", headers=_auth(token))
    assert r.status_code == 204

    # GET after delete → 404
    r = client.get(f"{API_VACANCIES_ADMIN}/{vid}", headers=_auth(token))
    assert r.status_code == 404


def test_admin_vacancy_enriched_fields_roundtrip():
    client = _make_client()
    token = _get_admin_token(client)

    ch = _create_charge(client, token, area="Operaciones")

    v = _create_vacancy(client, token, ch["id"], days_from_today=10, location="Quito", modality="hybrid")
    vid = v["id"]

    # PATCH con contenido enriquecido
    # Nota: 'tags' como STRING (tu endpoint admin hoy lo trata así).
    enriched = {
        "role_objective": "Impulsar el crecimiento con análisis de datos",
        "responsibilities": ["Analizar métricas", "Diseñar experimentos"],
        "req_education": ["Licenciatura en Sistemas"],
        "req_experience": ["3+ años en analítica"],
        "req_knowledge": ["SQL", "Python"],
        "benefits": ["Seguro médico", "Bono anual"],
        "company_about": "Somos una fintech en expansión",
        "hero_image_url": "https://example.com/banner.jpg",
        "tags": "analytics, growth",
    }
    r = client.patch(f"{API_VACANCIES_ADMIN}/{vid}", json=enriched, headers=_auth(token))
    assert r.status_code == 200, r.get_json()

    # GET y verificar roundtrip
    r = client.get(f"{API_VACANCIES_ADMIN}/{vid}", headers=_auth(token))
    assert r.status_code == 200
    got = r.get_json()

    assert got["role_objective"] == enriched["role_objective"]
    for k in ["responsibilities", "req_education", "req_experience", "req_knowledge", "benefits"]:
        assert got[k] == enriched[k]
    assert got["company_about"] == enriched["company_about"]
    assert got["hero_image_url"] == enriched["hero_image_url"]
    assert isinstance(got.get("tags"), list) and set(got["tags"]) >= {"analytics", "growth"}

    # cleanup
    client.delete(f"{API_VACANCIES_ADMIN}/{vid}", headers=_auth(token))


def test_admin_vacancies_listing_filters():
    client = _make_client()
    token = _get_admin_token(client)

    ch_ops = _create_charge(client, token, area="Operaciones")
    ch_hr  = _create_charge(client, token, area="RRHH")

    # Crear 3 y publicarlas
    v1 = _create_vacancy(client, token, ch_ops["id"], days_from_today=10, location="Quito",  modality="onsite")
    v2 = _create_vacancy(client, token, ch_ops["id"], days_from_today=10, location="Remoto", modality="remote")
    v3 = _create_vacancy(client, token, ch_hr["id"],  days_from_today=10, location="Quito",  modality="hybrid")

    for v in (v1, v2, v3):
        client.post(f"{API_VACANCIES_ADMIN}/{v['id']}/publish", headers=_auth(token))

    try:
        # === Estos filtros existen en el ENDPOINT PÚBLICO ===
        # area=Operaciones
        r = client.get(f"{API_VACANCIES_PUBLIC}/?area=Operaciones")
        assert r.status_code == 200
        items = r.get_json()["items"]
        assert items and all(it["charge_id"] == ch_ops["id"] for it in items)

        # modality=remote
        r = client.get(f"{API_VACANCIES_PUBLIC}/?modality=remote")
        assert r.status_code == 200
        items = r.get_json()["items"]
        assert items and all(it["modality"] == "remote" for it in items)

        # location contains "Quito"
        r = client.get(f"{API_VACANCIES_PUBLIC}/?location=Quit")
        assert r.status_code == 200
        items = r.get_json()["items"]
        assert items and all("Quito" in (it["location"] or "") for it in items)

        # paginación
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
