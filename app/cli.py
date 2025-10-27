# app/cli.py
import click
from .ext.db import db
from .models.admin.admin_user import AdminUser

def register_cli(app):
    @app.cli.command("seed-admin")
    @click.option("--email", default="admin@multiapoyo.com.ec", show_default=True)
    @click.option("--password", default="adminmulti007", show_default=True)
    @click.option("--nombre", default="Recursos", show_default=True)
    @click.option("--apellido", default="Humanos", show_default=True)
    @click.option("--superuser/--no-superuser", default=True, show_default=True)
    def seed_admin(email, password, nombre, apellido, superuser):
        """Crea o actualiza el usuario admin por defecto."""
        email = email.strip().lower()

        user = AdminUser.query.filter_by(email=email).first()
        if user is None:
            user = AdminUser(
                nombre=nombre,
                apellido=apellido,
                email=email,
                is_active=True,
                is_superuser=superuser,
            )
            user.set_password(password)
            user.normalize()
            db.session.add(user)
            db.session.commit()
            click.echo(f"✔ Usuario admin creado: {email}")
        else:
            # Actualiza datos básicos y contraseña
            user.nombre = nombre
            user.apellido = apellido
            user.is_active = True
            user.is_superuser = superuser
            user.set_password(password)
            user.normalize()
            db.session.commit()
            click.echo(f"✔ Usuario admin actualizado: {email}")
