# tests/admin/test_admin_steps.py
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone, date
import random
import string

import pytest
from flask_jwt_extended import create_access_token

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import create_app
from app.ext.db import db

from app.models.admin.vacancy import Vacancy
from app.models.admin.skill import Skill
from app.models.admin.vacancy_skills import VacancySkill
from app.models.admin.interview import Interview
from app.models.admin.skill_grade import SkillGrade
from app.models.admin.course import Course
from app.models.admin.skills_courses import skills_courses 
from app.models.admin.charges import Charges
from app.models.personality.attempt import PersonalityAttempt
from app.models.web_portal.applicant import Applicant
from app.models.web_portal.postulation import Postulation


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _only_model_columns(model_cls, data: dict) -> dict:
    cols = {c.key for c in model_cls.__table__.columns}
    return {k: v for k, v in data.items() if k in cols}


def _rand_email(prefix="user") -> str:
    suf = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{prefix}.{suf}@example.com"


def make_applicant(
    first_name: str = "Postulante",
    last_name: str = "Prueba",
    phone: str = "0999999999",
) -> Applicant:
    email = _rand_email("applicant")
    username = email.split("@")[0]
    payload = {
        "username": username,
        "email": email,
        "nombre": first_name,
        "apellido": last_name,
        "numero": phone,
        "password_hash": None,
        "is_google": False,
    }
    obj = Applicant(**_only_model_columns(Applicant, payload))
    db.session.add(obj)
    db.session.commit()
    return obj


def make_charge(title: str = "Backend Developer") -> Charges:
    payload = {
        "title": title,
        "area": "Engineering",
        "description": "Cargo de prueba",
    }
    obj = Charges(**_only_model_columns(Charges, payload))
    db.session.add(obj)
    db.session.commit()
    return obj


def make_vacancy(
    title: str = "Vacante Backend",
    description: str = "Descripción de prueba",
    is_active: bool = True,
    status: str = "published",
) -> Vacancy:
    ch = make_charge("Backend Developer")
    now = datetime.now(timezone.utc)
    payload = {
        "charge_id": ch.id,
        "title": title,
        "description": description,
        "location": "Remote",
        "modality": "remote",
        "apply_until": date.today() + timedelta(days=30),
        "publish_at": now,
        "is_active": is_active,
        "status": status,
        "headcount": 1,
        "responsibilities": [],
        "req_education": [],
        "req_experience": [],
        "req_knowledge": [],
        "benefits": [],
        "tags": [],
        "company_about": None,
        "hero_image_url": None,
    }
    obj = Vacancy(**_only_model_columns(Vacancy, payload))
    db.session.add(obj)
    db.session.commit()
    return obj


def make_skill(nombre: str) -> Skill:
    payload = {
        "nombre": nombre,       
        "descripcion": f"Habilidad {nombre}",
        "nivel_minimo": 1,
        "is_active": True,
    }
    obj = Skill(**_only_model_columns(Skill, payload))
    db.session.add(obj)
    db.session.commit()
    return obj


def link_vacancy_skill(vacancy_id: int, skill_id: int) -> VacancySkill:
    payload = {
        "vacancy_id": vacancy_id,
        "skill_id": skill_id,
        "required_score": 0,
        "weight": 1.0,
    }
    obj = VacancySkill(**_only_model_columns(VacancySkill, payload))
    db.session.add(obj)
    db.session.commit()
    return obj


def make_postulation(applicant: Applicant, vacancy: Vacancy, status: str = "submitted") -> Postulation:
    payload = {
        "vacancy_id": vacancy.id,
        "applicant_id": applicant.id,
        "cv_path": "/tmp/cv_dummy.pdf",
        "status": status,
        "residence_addr": None,
        "age": None,
        "role_exp_years": None,
        "expected_salary": None,
        "credential": None,
        "number": None,
    }
    obj = Postulation(**_only_model_columns(Postulation, payload))
    db.session.add(obj)
    db.session.commit()
    return obj


def _iso_in(minutes: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()



@pytest.fixture(scope="session")
def app():
    os.environ.setdefault("FLASK_ENV", "testing")
    os.environ.setdefault("APP_CONFIG", "testing")

    app = create_app("testing")
    app.config.update(
        TESTING=True,
        PROPAGATE_EXCEPTIONS=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JWT_TOKEN_LOCATION=["headers"],
        JWT_SECRET_KEY="test-secret-key",
        ENABLE_ADMIN_SIMULATION=True,
    )

    with app.app_context():
        db.create_all()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_headers(app, app_ctx):
    token = create_access_token(
        identity="test-admin-id",
        additional_claims={"roles": ["admin"], "is_admin": True},
    )
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------
def test_full_admin_flow_steps_1_to_5_and_cancel(client, app_ctx, auth_headers):
    """
    Flujo:
      1) Step1: accepted
      2) Step2: complete -> personality_test_ready
      3) Step3: GET pending, personality exam -> interview_scheduled, GET completed
      4) Step4: schedule, grade (1), bulk, notes, complete -> selection_pending
      5) Step5: hire -> hired
      6) Cancel desde 'hired' => 400/409 (no permitido)
      7) Cancel en otra postulación en 'accepted' => 200 (rejected/cancelled)
    """
    # --- Datos base ---
    applicant = make_applicant()
    vacancy = make_vacancy()
    skill1 = make_skill("Python")
    skill2 = make_skill("SQL")
    link_vacancy_skill(vacancy.id, skill1.id)
    link_vacancy_skill(vacancy.id, skill2.id)
    post = make_postulation(applicant=applicant, vacancy=vacancy, status="submitted")

    # -------- Step 1: aceptar --------
    r = client.post(
        f"/api/admin/postulations/{post.id}/steps/1/start",
        headers=auth_headers,
    )
    assert r.status_code == 200, r.get_json()
    body = r.get_json()
    assert (body.get("status") or "").lower() == "accepted"

    # -------- Step 2: completar prescreen --------
    r = client.post(
        f"/api/admin/postulations/{post.id}/complete",
        headers=auth_headers,
    )
    assert r.status_code == 200, r.get_json()
    body = r.get_json()
    assert (body.get("status") or "").lower() == "personality_test_ready"

    # -------- Step 3: GET debe ser pending --------
    r = client.get(
        f"/api/admin/postulations/personality/{post.id}",
        headers=auth_headers,
    )
    assert r.status_code == 200, r.get_json()
    data = r.get_json()
    assert (data.get("status") or "").lower() == "personality_test_ready"
    assert data.get("view_state") == "pending"
    assert data.get("results") is None

    # -------- Step 3: simular que el postulante terminó su examen --------
    att = PersonalityAttempt(
        postulation_id=post.id,
        applicant_id=post.applicant_id,
        vacancy_id=post.vacancy_id,
        status="finished",
        started_at=datetime.now(timezone.utc) - timedelta(minutes=12),
        finished_at=datetime.now(timezone.utc),
        duration_sec=12 * 60,
        overall_score=76,
        traits_json={"percents": {"Responsabilidad": 0.8, "Trabajo en equipo": 0.7}},
        recommendation="CONTINUE",
    )
    db.session.add(att)
    db.session.commit()

    # <- NUEVO: avanzar el estado como hacía el mock-finish
    post.status = "interview_scheduled"
    db.session.add(post)
    db.session.commit()

    # -------- Step 3: GET ahora debe mostrar completed --------
    r = client.get(
        f"/api/admin/postulations/personality/{post.id}",
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("view_state") == "completed"
    assert data.get("results") is not None
    assert data["results"]["overall_score"] >= 0
    assert (data.get("status") or "").lower() in (
        "interview_scheduled", "selection_pending", "hired"
    )


    # -------- Step 4: schedule entrevista --------
    payload_schedule = {
        "starts_at": _iso_in(90),
        "modality": "online",
        "location": None,
        "meet_url": "https://meet.example.com/abc",
        "postulation_id": post.id,
    }
    r = client.post(
        f"/api/admin/postulations/interview/{post.id}/schedule",
        json=payload_schedule,
        headers=auth_headers,
    )
    assert r.status_code == 200, r.get_json()
    itv = r.get_json()
    assert itv["postulation_id"] == post.id
    assert itv["starts_at"]

    # -------- Step 4: agregar 1 grade --------
    r = client.post(
        f"/api/admin/postulations/interview/{post.id}/grades",
        json={"skill_id": skill1.id, "score": 88},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.get_json()
    g1 = r.get_json()
    assert g1["skill_id"] == skill1.id
    assert g1["score"] == 88

    # -------- Step 4: bulk grades (incluye la segunda skill) --------
    r = client.post(
        f"/api/admin/postulations/interview/{post.id}/grades/bulk",
        json={"grades": [{"skill_id": skill2.id, "score": 91}]},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.get_json()
    bulk = r.get_json()
    assert bulk.get("updated", 0) >= 1
    assert len(bulk.get("items") or []) >= 1
    assert bulk["items"][0]["skill_id"] == skill2.id

    # -------- Step 4: notas --------
    r = client.patch(
        f"/api/admin/postulations/interview/{post.id}/notes",
        json={"notes": "Buen desempeño técnico."},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.get_json()
    itv_after_notes = r.get_json()
    assert itv_after_notes.get("notes") == "Buen desempeño técnico."

    # -------- Step 4: completar (pasa a selection_pending) --------
    r = client.post(
        f"/api/admin/postulations/interview/{post.id}/complete",
        headers=auth_headers,
    )
    assert r.status_code == 200, r.get_json()
    st = r.get_json()
    assert (st.get("status") or "").lower() == "selection_pending"

    # -------- Step 5: hire --------
    r = client.post(
        f"/api/admin/postulations/{post.id}/hire",
        headers=auth_headers,
    )
    assert r.status_code == 200, r.get_json()
    st = r.get_json()
    assert (st.get("status") or "").lower() == "hired"

    # -------- Cancel desde 'hired' no permitido --------
    r = client.post(
        f"/api/admin/postulations/{post.id}/cancel",
        json={"reason": "Prueba no válida"},
        headers=auth_headers,
    )
    assert r.status_code in (400, 409)

    # -------- Caso alterno: cancelar otra postulación en 'accepted' --------
    applicant2 = make_applicant()
    post2 = make_postulation(applicant=applicant2, vacancy=vacancy, status="submitted")

    # Step 1 -> accepted
    r = client.post(
        f"/api/admin/postulations/{post2.id}/steps/1/start",
        headers=auth_headers,
    )
    assert r.status_code == 200, r.get_json()

    # Cancelar aceptada
    r = client.post(
        f"/api/admin/postulations/{post2.id}/cancel",
        json={"reason": "No cumple requisitos"},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.get_json()
    body = r.get_json()
    assert (body.get("status") or "").lower() in ("rejected", "cancelled", "canceled")


def test_step2_rejects_from_wrong_state(client, app_ctx, auth_headers):
    """Step 2 debe rechazar transición si el estado no es accepted/prescreen_call."""
    applicant = make_applicant()
    vacancy = make_vacancy()
    post = make_postulation(applicant=applicant, vacancy=vacancy, status="submitted")

    # Intentar completar Step2 directamente desde 'submitted'
    r = client.post(
        f"/api/admin/postulations/{post.id}/complete",
        headers=auth_headers,
    )
    assert r.status_code == 400, r.get_json()
    body = r.get_json()
    assert "no permitida" in (body.get("message", "").lower())
