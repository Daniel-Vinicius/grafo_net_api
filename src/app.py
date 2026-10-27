from collections.abc import Mapping

from flask import Flask

from config import configure_app, configure_cors
from modules.auth.routes.routes import create_auth_routes
from modules.connections.routes.routes import create_connections_routes
from modules.graph.routes.routes import create_graph_routes
from modules.health.routes.routes import create_health_routes
from modules.search.routes.routes import create_search_routes


def create_app(config: Mapping[str, object] | None = None) -> Flask:
    app = Flask(__name__)
    configure_app(app, config)
    configure_cors(app)
    app.register_blueprint(create_health_routes())
    app.register_blueprint(create_auth_routes(app))
    app.register_blueprint(create_connections_routes(app))
    app.register_blueprint(create_graph_routes(app))
    app.register_blueprint(create_search_routes(app))
    return app
