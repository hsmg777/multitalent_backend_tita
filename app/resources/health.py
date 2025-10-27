from flask.views import MethodView
from flask_smorest import Blueprint
from ..schemas.health import HealthOut  

blp = Blueprint("health", "health", url_prefix="/api/v1/health", description="Health check")

@blp.route("/")
class Health(MethodView):
    @blp.response(200, HealthOut)
    def get(self):
        return {"status": "ok"}
