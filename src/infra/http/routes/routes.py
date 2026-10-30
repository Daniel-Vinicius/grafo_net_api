from copy import deepcopy

from apispec import APISpec
from apispec_webframeworks.flask import FlaskPlugin
from flask import Blueprint, jsonify
from flask_swagger_ui import get_swaggerui_blueprint

from infra.http.schemas import schemas


def register_documentation(app):
    spec = APISpec(
        title="GrafoNet API",
        version="1.0.0",
        openapi_version="3.0.3",
        plugins=[FlaskPlugin()],
        servers=[{"url": "/"}],
    )
    spec.components.security_scheme(
        "bearerAuth", {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    )
    spec.components.security_scheme(
        "bootstrapKey", {"type": "apiKey", "in": "header", "name": "X-Bootstrap-Key"}
    )
    for name, schema in schemas().items():
        spec.components.schema(name, schema)
    with app.test_request_context():
        for rule in app.url_map.iter_rules():
            view = app.view_functions[rule.endpoint]
            metadata = getattr(view, "openapi", None)
            if metadata is None:
                continue
            for method in sorted(rule.methods - {"HEAD", "OPTIONS"}):
                operation = deepcopy(metadata)
                for parameter in sorted(rule.arguments):
                    operation.setdefault("parameters", []).append(
                        {
                            "name": parameter,
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    )
                if rule.rule == "/invitations":
                    operation["security"] = [{"bearerAuth": []}, {"bootstrapKey": []}]
                    operation["description"] = (
                        "Com Bearer: convite normal. Sem JWT: X-Bootstrap-Key somente enquanto não existir conta. JWT inválido nunca usa bootstrap."
                    )
                if rule.rule == "/research-participations":
                    operation.setdefault("parameters", []).append(
                        {
                            "name": "status",
                            "in": "query",
                            "schema": {
                                "type": "string",
                                "enum": ["pending", "confirmed", "rejected"],
                                "default": "pending",
                            },
                        }
                    )
                if rule.rule.endswith("/photo") and method == "GET":
                    operation["responses"]["200"]["content"] = {
                        "image/png": {"schema": {"type": "string", "format": "binary"}}
                    }
                    operation["responses"]["200"]["headers"] = {
                        "ETag": {
                            "schema": {"type": "string"},
                            "description": "Versão da foto",
                        }
                    }
                    operation["responses"]["304"] = {
                        "description": "Foto não modificada"
                    }
                spec.path(view=view, operations={method.lower(): operation})
    blueprint = Blueprint("documentation", __name__)

    @blueprint.get("/openapi.json")
    def openapi():
        return jsonify(spec.to_dict())

    app.register_blueprint(blueprint)
    app.register_blueprint(
        get_swaggerui_blueprint(
            "/docs",
            "/openapi.json",
            config={
                "app_name": "GrafoNet API",
                "validatorUrl": None,
                "persistAuthorization": False,
            },
        )
    )
