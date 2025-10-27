from datetime import timedelta
import pytest
from flask_jwt_extended import create_access_token

from tests.factories import make_admin
from app.ext.db import db
from app.models.admin.charges import Charges

# ----------------- helpers -----------------
def _admin_headers(app, admin_id: int):
    """Header Authorization con identidad 'admin:{id}' para pasar _require_admin()."""
    with app.app_context():
        token = create_access_token(identity=f"admin:{admin_id}", expires_delta=timedelta(hours=2))
    return {"Authorization": f"Bearer {token}"}

def _make_charge(title="Developer", description="Builds stuff", area="IT"):
    c = Charges(title=title, description=description, area=area)
    db.session.add(c)
    db.session.commit()
    return c

# ----------------- tests -----------------

def test_charges_crud_happy_path(client, test_app):
    admin = make_admin()
    headers = _admin_headers(test_app, admin.id)

    # Create
    payload = {"title": "Backend Dev", "description": "APIs y más", "area": "IT"}
    r = client.post("/api/admin/charges/", json=payload, headers=headers)
    assert r.status_code == 201
    created = r.get_json()
    charge_id = created["id"]

    # Read
    r = client.get(f"/api/admin/charges/{charge_id}", headers=headers)
    assert r.status_code == 200
    assert r.get_json()["title"] == "Backend Dev"

    # Put (total)
    r = client.put(
        f"/api/admin/charges/{charge_id}",
        json={"title": "Backend Sr", "description": "Microservicios", "area": "Tech"},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.get_json()["title"] == "Backend Sr"

    # Patch (parcial)
    r = client.patch(
        f"/api/admin/charges/{charge_id}",
        json={"description": "Microservicios - actualización"},
        headers=headers,
    )
    assert r.status_code == 200
    assert "actualización" in r.get_json()["description"]

    # Delete
    r = client.delete(f"/api/admin/charges/{charge_id}", headers=headers)
    assert r.status_code == 204

    # Ya no existe
    r = client.get(f"/api/admin/charges/{charge_id}", headers=headers)
    assert r.status_code == 404


def test_charges_duplicate_title_current_behavior(client, test_app):
    """
    Con el modelo actual NO hay restricción de unicidad en title.
    Debe permitir crear duplicados (201) y quedar 2 filas con el mismo título.
    """
    admin = make_admin()
    headers = _admin_headers(test_app, admin.id)

    _make_charge(title="QA", description="Calidad", area="OPS")
    r = client.post(
        "/api/admin/charges/",
        json={"title": "QA", "description": "Otra", "area": "OPS"},
        headers=headers,
    )
    assert r.status_code == 201

    # Verificamos que existan 2 charges con el mismo título
    with test_app.app_context():
        count = Charges.query.filter_by(title="QA").count()
        assert count == 2


def test_charges_list_filters_and_pagination(client, test_app):
    admin = make_admin()
    headers = _admin_headers(test_app, admin.id)

    # Semilla
    data = [
        ("DevOps", "Pipelines", "OPS"),
        ("Backend", "APIs en Python", "IT"),
        ("Frontend", "React y UI", "IT"),
        ("QA Analyst", "Pruebas", "OPS"),
        ("Data Engineer", "ETL", "DATA"),
    ]
    for t, d, a in data:
        _make_charge(title=t, description=d, area=a)

    # List base
    r = client.get("/api/admin/charges/", headers=headers)
    assert r.status_code == 200
    body = r.get_json()
    assert "items" in body and "meta" in body
    assert body["meta"]["total"] >= 5

    # Filtro q
    r = client.get("/api/admin/charges/?q=dev", headers=headers)
    assert r.status_code == 200
    items = r.get_json()["items"]
    assert any("dev" in i["title"].lower() or "dev" in (i.get("description") or "").lower() for i in items)

    # Filtro area
    r = client.get("/api/admin/charges/?area=IT", headers=headers)
    assert r.status_code == 200
    assert all(i.get("area") == "IT" for i in r.get_json()["items"])

    # Paginación válida
    r = client.get("/api/admin/charges/?per_page=2&page=2", headers=headers)
    assert r.status_code == 200
    meta = r.get_json()["meta"]
    assert meta["per_page"] == 2 and meta["page"] == 2

    # Paginación inválida -> 400
    r = client.get("/api/admin/charges/?page=foo", headers=headers)
    assert r.status_code == 400


def test_charges_requires_admin_token(client, test_app):
    # Sin token -> 401/422 (jwt_required)
    assert client.get("/api/admin/charges/").status_code in (401, 422)

    # Token de identidad NO admin -> 403 (_require_admin)
    with test_app.app_context():
        bad_token = create_access_token(identity="123")
    r = client.get("/api/admin/charges/", headers={"Authorization": f"Bearer {bad_token}"})
    assert r.status_code == 403
