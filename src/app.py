from flask import Flask

from infra.config.application import compose
from infra.config.settings import settings
from infra.database.commands import register_commands
from infra.http.boundary import configure_http
from infra.http.routes.routes import register_documentation
from infra.security.tokens.flask import FlaskTokenIssuer, configure_tokens
from modules.auth.routes.routes import create_routes as auth_routes
from modules.connections.routes.routes import create_routes as connection_routes
from modules.graph.routes.routes import create_routes as graph_routes
from modules.health.routes.routes import create_routes as health_routes
from modules.search.routes.routes import create_routes as search_routes


def create_app(config=None, application=None):
    app = Flask(__name__)
    app.config.update(settings(config))
    application = application or compose(app.config)
    app.extensions["application"] = application
    configure_http(app)
    configure_tokens(app, application.repositories)
    app.register_blueprint(auth_routes(application.actions, FlaskTokenIssuer()))
    for factory in (connection_routes, graph_routes, search_routes, health_routes):
        app.register_blueprint(factory(application.actions))
    register_documentation(app)
    register_commands(app, application)
    return app
