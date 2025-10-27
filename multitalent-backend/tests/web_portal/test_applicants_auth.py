from datetime import timedelta
from flask_jwt_extended import create_access_token
from flask_smorest import abort
from tests.factories import make_applicant


def _auth_headers(app, applicant_id):
    # Crear el token dentro del app context y con identidad string
    # para evitar el 422 ("Subject must be a string") al decodificar el JWT.
    with app.app_context():
        token = create_access_token(identity=str(applicant_id), expires_delta=timedelta(hours=1))
    return {"Authorization": f"Bearer {token}"}


# -------- Registro --------
def test_register_ok(client):
    payload = {
        "username": "nuevo",
        "email": "nuevo@mail.com",
        "nombre": "Nuevo",
        "apellido": "User",
        "numero": "0999999999",
        "password": "Clave#123",
    }
    r = client.post("/api/applicants/register", json=payload)
    assert r.status_code == 201
    data = r.get_json()
    assert data["email"] == "nuevo@mail.com"
    assert data["username"] == "nuevo"


def test_register_conflict_email_or_username(client, monkeypatch):
    # Parchar blp.abort -> abort global (sin tocar el endpoint)
    monkeypatch.setattr("app.resources.web_portal.applicant.blp.abort", abort, raising=False)

    ok = {
        "username": "dup",
        "email": "dup@mail.com",
        "nombre": "N",
        "apellido": "A",
        "numero": "0999999999",
        "password": "Clave#123",
    }
    assert client.post("/api/applicants/register", json=ok).status_code == 201
    # Conflicto por email
    assert client.post("/api/applicants/register", json={**ok, "username": "otro"}).status_code == 409
    # Conflicto por username
    assert client.post("/api/applicants/register", json={**ok, "email": "otro@mail.com"}).status_code == 409


# -------- Login --------
def test_login_ok(client):
    # Sembramos usuario directo en BD (más estable para flujo de password)
    make_applicant(email="l1@mail.com", username="l1", password="Clave#123")
    r = client.post("/api/applicants/login", json={"email": "l1@mail.com", "password": "Clave#123"})
    assert r.status_code == 200
    data = r.get_json()
    assert "access_token" in data and "user" in data


def test_login_incorrect_password(client):
    make_applicant(email="l2@mail.com", username="l2", password="Clave#123")
    assert client.post("/api/applicants/login", json={"email": "l2@mail.com", "password": "WRONG"}).status_code == 401


def test_login_user_not_found(client):
    assert client.post("/api/applicants/login", json={"email": "noexiste@mail.com", "password": "x"}).status_code == 401


def test_login_google_account_blocked_in_password_flow(client):
    # Crea vía Google (password_hash=None) mediante el endpoint real
    assert client.post("/api/applicants/google", json={
        "email": "glogin@mail.com", "nombre": "G", "apellido": "U", "username": "glogin"
    }).status_code == 200
    r = client.post("/api/applicants/login", json={"email": "glogin@mail.com", "password": "cualquiera"})
    assert r.status_code == 400
    assert "Google" in r.get_json()["message"]


# -------- Profile --------
def test_profile_ok(client, test_app):
    # sembramos usuario y autenticamos con header usando token válido
    a = make_applicant(email="p@mail.com", username="p", password="Clave#123")
    headers = _auth_headers(test_app, a.id)
    r = client.get("/api/applicants/profile", headers=headers)
    assert r.status_code == 200
    assert r.get_json()["email"] == "p@mail.com"


def test_profile_requires_token(client):
    assert client.get("/api/applicants/profile").status_code in (401, 422, 403)


# -------- Google login --------
def test_google_login_creates_user_if_not_exists(client):
    r = client.post("/api/applicants/google", json={
        "email": "g1@mail.com", "nombre": "G", "apellido": "User", "username": "guser"
    })
    assert r.status_code == 200
    data = r.get_json()
    assert data["user"]["email"] == "g1@mail.com"
    assert data["user"]["is_google"] is True


def test_google_login_reuses_existing_user(client):
    assert client.post("/api/applicants/google", json={
        "email": "g2@mail.com", "nombre": "G", "apellido": "U", "username": "guser2"
    }).status_code == 200
    r = client.post("/api/applicants/google", json={
        "email": "g2@mail.com", "nombre": "GG", "apellido": "UU", "username": "whatever"
    })
    assert r.status_code == 200
    assert r.get_json()["user"]["email"] == "g2@mail.com"


# -------- Forgot / Reset --------
def test_forgot_password_sends_mail_when_password_user(client, monkeypatch):
    sent = {"n": 0}
    def fake_send_mail(*args, **kwargs): sent["n"] += 1
    # Parchear en el módulo del blueprint real
    monkeypatch.setattr("app.resources.web_portal.applicant.send_mail", fake_send_mail)

    make_applicant(email="f1@mail.com", username="f1", password="Clave#123")

    r = client.post("/api/applicants/password/forgot", json={"email": "f1@mail.com"})
    assert r.status_code == 200
    assert sent["n"] == 1


def test_forgot_password_google_account_returns_200_but_no_mail(client, monkeypatch):
    sent = {"n": 0}
    def fake_send_mail(*args, **kwargs): sent["n"] += 1
    monkeypatch.setattr("app.resources.web_portal.applicant.send_mail", fake_send_mail)

    # Crea vía endpoint Google (password_hash=None)
    client.post("/api/applicants/google", json={
        "email": "f2@mail.com", "nombre": "G", "apellido": "U", "username": "f2"
    })
    r = client.post("/api/applicants/password/forgot", json={"email": "f2@mail.com"})
    assert r.status_code == 200
    assert sent["n"] == 0


def test_forgot_password_unknown_email_is_200(client, monkeypatch):
    monkeypatch.setattr("app.resources.web_portal.applicant.send_mail", lambda **k: None)
    assert client.post("/api/applicants/password/forgot", json={"email": "nobody@mail.com"}).status_code == 200


def test_reset_password_ok_flow(client, monkeypatch):
    # Sembrar usuario
    a = make_applicant(email="rok@mail.com", username="rok", password="Old#123")

    # simulamos token válido SIN tocar tu modelo/DB
    class _Token:
        def __init__(self, applicant_id): self.applicant_id = applicant_id

    def fake_consume(raw):  # devuelve token con el id del user creado
        return _Token(a.id)

    monkeypatch.setattr("app.resources.web_portal.applicant.PasswordResetToken.consume", fake_consume)

    token_raw = "A" * 32  # cumplir min_length=16 del schema
    assert client.post("/api/applicants/password/reset", json={"token": token_raw, "password": "New#123"}).status_code == 200
    assert client.post("/api/applicants/login", json={"email": "rok@mail.com", "password": "New#123"}).status_code == 200


def test_reset_password_invalid_token(client, monkeypatch):
    # Parchar blp.abort en esta rama también
    monkeypatch.setattr("app.resources.web_portal.applicant.blp.abort", abort, raising=False)
    monkeypatch.setattr("app.resources.web_portal.applicant.PasswordResetToken.consume", lambda raw: None)
    bad_token = "B" * 32  # cumplir min_length=16
    assert client.post("/api/applicants/password/reset", json={"token": bad_token, "password": "Xxxxxx1"}).status_code == 400
