# tests/factories.py
from uuid import uuid4
from app.ext.db import db
from app.models.web_portal.applicant import Applicant
from app.models.admin.admin_user import AdminUser

def make_applicant(
    *,
    email=None,
    username=None,
    password="Clave#123",
    nombre="Nombre",
    apellido="Apellido",
    numero="0999999999",
    is_google=False
):
    # 🔧 genera únicos si no llegan
    if email is None:
        email = f"aspirante+{uuid4().hex[:8]}@test.com"
    if username is None:
        username = f"asp_{uuid4().hex[:6]}"

    a = Applicant(
        username=username,
        email=email,
        nombre=nombre,
        apellido=apellido,
        numero=numero,
        is_google=is_google,
    )
    a.normalize()
    if not is_google:
        a.set_password(password)
    else:
        a.password_hash = None
    db.session.add(a)
    db.session.commit()
    return a

def make_admin(
    *,
    email=None,
    nombre="Admin",
    apellido="User",
    password="Clave#123",
    is_active=True,
    is_superuser=False,
):
    if email is None:
        email = f"admin+{uuid4().hex[:8]}@test.com"
    u = AdminUser(
        nombre=nombre,
        apellido=apellido,
        email=email,
        is_active=is_active,
        is_superuser=is_superuser,
    )
    u.normalize()
    u.set_password(password)
    db.session.add(u)
    db.session.commit()
    return u
