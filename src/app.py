from collections.abc import Mapping
from flask import Flask
from modules.health.routes.routes import create_health_routes

def create_app(config: Mapping[str, object] | None = None) -> Flask:
    app = Flask(__name__)
    if config is not None:
        app.config.from_mapping(config)
    app.register_blueprint(create_health_routes())
    return app
