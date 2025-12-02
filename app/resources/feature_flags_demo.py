# app/resources/feature_flags_demo.py
from flask_smorest import Blueprint
from flask.views import MethodView
from flask import request
from ..feature_flags import is_feature_enabled

blp = Blueprint(
    "FeatureFlagsDemo",
    "feature_flags_demo",
    description="Endpoints de demo para LaunchDarkly",
)

@blp.route("/feature-flags/demo")
class FeatureFlagsDemoResource(MethodView):
    @blp.response(200)
    def get(self):
        """
        Demo simple:
        - Si el flag 'mi-feature-nueva' está activo -> mensaje nuevo
        - Si está apagado -> mensaje clásico
        """
        user_id = request.headers.get("X-User-Id", "anonymous")
        enabled = is_feature_enabled("mi-feature-nueva", user_id)

        if enabled:
            return {"message": "Nueva funcionalidad ACTIVADA 🚀"}
        else:
            return {"message": "Funcionalidad clásica (flag apagado)"}
