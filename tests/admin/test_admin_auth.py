# tests/admin/test_admin_auth.py
from datetime import timedelta
from flask_jwt_extended import create_access_token
from tests.factories import make_admin

def _admin_headers(app, admin_id: int):
    with app.app_context():
        token = create_access_token(identity=f"admin:{admin_id}", expires_delta=timedelta(hours=1))
    return {"Authorization": f"Bearer {token}"}

# ---------- /api/admin/auth/login ----------
def test_admin_login_ok(client):
    make_admin(email="a1@mail.com", password="Clave#123")
    r = client.post("/api/admin/auth/login", json={"email": "a1@mail.com", "password": "Clave#123"})
    assert r.status_code == 200
    data = r.get_json()
    assert "access_token" in data and "user" in data
    assert data["user"]["email"] == "a1@mail.com"

def test_admin_login_wrong_password(client):
    make_admin(email="a2@mail.com", password="Good#123")
    assert client.post("/api/admin/auth/login", json={"email": "a2@mail.com", "password": "bad"}).status_code == 401

def test_admin_login_inactive_user(client):
    make_admin(email="a3@mail.com", password="Clave#123", is_active=False)
    assert client.post("/api/admin/auth/login", json={"email": "a3@mail.com", "password": "Clave#123"}).status_code == 401

# ---------- /api/admin/auth/profile ----------
def test_admin_profile_ok(client, test_app):
    admin = make_admin(email="p@mail.com", password="Clave#123")
    headers = _admin_headers(test_app, admin.id)
    r = client.get("/api/admin/auth/profile", headers=headers)
    assert r.status_code == 200
    assert r.get_json()["email"] == "p@mail.com"

def test_admin_profile_requires_admin_prefix(client, test_app):
    admin = make_admin(email="p2@mail.com", password="Clave#123")
    with test_app.app_context():
        bad_token = create_access_token(identity=str(admin.id), expires_delta=timedelta(hours=1))
    r = client.get("/api/admin/auth/profile", headers={"Authorization": f"Bearer {bad_token}"})
    assert r.status_code == 403

def test_admin_profile_without_token(client):
    assert client.get("/api/admin/auth/profile").status_code in (401, 422, 403)
