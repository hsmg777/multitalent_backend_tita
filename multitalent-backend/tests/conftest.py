import pytest
from flask import Flask
from flask_smorest import Api
from flask_jwt_extended import JWTManager
from sqlalchemy.pool import StaticPool

from app.ext.db import db
from app.resources.web_portal.applicant import blp as applicants_blp
from app.resources.admin.auth import blp as admin_auth_blp
from app.resources.admin.users import blp as admin_users_blp
from app.resources.admin.charges import blp as admin_charges_blp 
from app.resources.web_portal.postulation import blp as postulations_blp
from app.resources.admin.steps.step3_personality import blp as admin_step3_blp


@pytest.fixture(scope="session")
def test_app():
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        PROPAGATE_EXCEPTIONS=True,
        API_TITLE="API Test",
        API_VERSION="v1",
        OPENAPI_VERSION="3.0.3",
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={
            "poolclass": StaticPool,
            "connect_args": {"check_same_thread": False},
        },
        JWT_SECRET_KEY="test-secret",
        RESET_TOKEN_HOURS=2,
        FRONTEND_URL="http://frontend.test",
    )

    db.init_app(app)
    JWTManager(app)

    api = Api(app)
    api.register_blueprint(applicants_blp, url_prefix="/api/applicants")
    api.register_blueprint(admin_auth_blp,   url_prefix="/api/admin/auth")
    api.register_blueprint(admin_users_blp,  url_prefix="/api/admin/users")
    api.register_blueprint(admin_charges_blp, url_prefix="/api/admin/charges")
    api.register_blueprint(admin_step3_blp, url_prefix="/api/admin/steps")
    api.register_blueprint(postulations_blp, url_prefix="/api")

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(test_app):
    return test_app.test_client()


@pytest.fixture()
def app_ctx(test_app):
    with test_app.app_context():
        yield