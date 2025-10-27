# app/__init__.py
from flask import Flask
from flask_jwt_extended import JWTManager
from .config import get_config
from .resources import register_resources
from .ext.db import db
from .ext.migrate import migrate
from flask_cors import CORS
from . import cli as app_cli
import logging, sys


jwt = JWTManager()

def create_app(config_name=None):
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    # ==== LOGGING CONFIG ====
    root = logging.getLogger()
    if not root.handlers:  # evita duplicados en hot reload
        handler = logging.StreamHandler(sys.stdout)
        fmt = logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s"
        )
        handler.setFormatter(fmt)
        root.addHandler(handler)

    # Nivel global INFO
    root.setLevel(logging.INFO)

    # Niveles específicos (opcional)
    logging.getLogger("werkzeug").setLevel(logging.INFO)
    logging.getLogger("app.resources.web_portal.postulation").setLevel(logging.INFO)
    logging.getLogger("app.resources.ai_scoring").setLevel(logging.INFO)

    # Extensiones
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    CORS(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=True,
        expose_headers=["Content-Type", "Authorization"],
    )
    app.config["CORS_HEADERS"] = "Content-Type, Authorization"

    # Cargar modelos para migraciones
    from . import models  # noqa

    # Blueprints
    register_resources(app)
    app_cli.register_cli(app)

    return app
