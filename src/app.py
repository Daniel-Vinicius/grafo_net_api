from collections.abc import Mapping

from flask import Flask

from config import configure_app
from modules.auth.routes.routes import create_auth_routes
from modules.health.routes.routes import create_health_routes


def create_app(config: Mapping[str, object] | None = None) -> Flask:
    app = Flask(__name__)
    configure_app(app, config)
    app.register_blueprint(create_health_routes())
    app.register_blueprint(create_auth_routes(app))
    return app
