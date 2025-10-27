# app/config.py
import os

class BaseConfig:
    # --- General / API ---
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
    RESET_TOKEN_HOURS = int(os.getenv("RESET_TOKEN_HOURS", "2"))
    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_SENDER = os.getenv("MAIL_SENDER", "Multitalent <haylandsebastian5@gmail.com>")

    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    CORS_HEADERS = "Content-Type,Authorization"
    API_TITLE = "Multitalent API"
    API_VERSION = "v1"
    OPENAPI_VERSION = "3.0.3"
    OPENAPI_URL_PREFIX = "/docs"
    OPENAPI_SWAGGER_UI_PATH = "/"
    OPENAPI_SWAGGER_UI_URL = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
    DEBUG = False
    PROPAGATE_EXCEPTIONS = True

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///dev.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-in-prod")

    OPENAPI_COMPONENTS = {
        "securitySchemes": {
            "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
        }
    }

    # ===================== Personality Test=====================
    PERSONALITY_TIME_LIMIT_SEC = 1800  # 30 min

    AUTO_TRANSITION_ON_FINISH = True

    ENABLE_ADMIN_SIMULATION = False
    # =======================================================================


class DevConfig(BaseConfig):
    DEBUG = True
    ENABLE_ADMIN_SIMULATION = True


class ProdConfig(BaseConfig):
    DEBUG = False
    ENABLE_ADMIN_SIMULATION = False


def get_config(name=None):
    if (name or os.getenv("FLASK_ENV", "dev")).lower().startswith("prod"):
        return ProdConfig
    return DevConfig
