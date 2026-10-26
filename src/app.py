import os
from collections.abc import Mapping
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask

from database.connection import create_database
from modules.auth.jwt import configure_jwt
from modules.auth.repositories.contract import UserRepository
from modules.auth.repositories.in_memory.repository import InMemoryUserRepository
from modules.auth.repositories.mongo.repository import MongoUserRepository
from modules.auth.routes.routes import create_auth_routes
from modules.health.routes.routes import create_health_routes


def create_app(
    config: Mapping[str, object] | None = None,
    users: UserRepository | None = None,
) -> Flask:
    load_dotenv()
    app = Flask(__name__)
    app.config.from_mapping(
        JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY"),
        JWT_TOKEN_LOCATION=["cookies"],
        JWT_COOKIE_CSRF_PROTECT=True,
        JWT_COOKIE_SECURE=os.getenv("JWT_COOKIE_SECURE", "true").lower() == "true",
        JWT_COOKIE_SAMESITE="Lax",
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=15),
        MONGO_URI=os.getenv("MONGO_URI"),
        MONGO_DB=os.getenv("MONGO_DB"),
    )
    if config is not None:
        app.config.from_mapping(config)
    secret = app.config["JWT_SECRET_KEY"]
    if not isinstance(secret, str) or len(secret.encode("utf-8")) < 32:
        raise ValueError("JWT_SECRET_KEY deve ter pelo menos 32 bytes")

    if users is None:
        if app.testing:
            users = InMemoryUserRepository([])
        else:
            database = create_database(app.config["MONGO_URI"], app.config["MONGO_DB"])
            app.extensions["mongo_client"] = database.client
            users = MongoUserRepository(database)
    app.extensions["user_repository"] = users
    configure_jwt(app, users)
    app.register_blueprint(create_health_routes())
    app.register_blueprint(create_auth_routes(users))
    return app
