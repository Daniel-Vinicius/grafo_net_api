from datetime import datetime, timezone

from flask import Blueprint, Flask, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    current_user,
    get_jwt,
    jwt_required,
)

from database.connection import create_database
from modules.auth.jwt import configure_jwt
from modules.auth.repositories.contract import TokenRepository, UserRepository
from modules.auth.repositories.mongo.repository import MongoTokenRepository, MongoUserRepository
from modules.auth.useCases.login.login import AuthUseCase


def create_auth_routes(
    app: Flask,
    users_repository: UserRepository | None = None,
    tokens_repository: TokenRepository | None = None,
) -> Blueprint:
    if users_repository is None or tokens_repository is None:
        database = create_database(app.config["MONGO_URI"], app.config["MONGO_DB"])
        app.extensions["mongo_client"] = database.client
        if users_repository is None:
            users_repository = MongoUserRepository(database)
        if tokens_repository is None:
            tokens_repository = MongoTokenRepository(database)
    app.extensions["user_repository"] = users_repository
    configure_jwt(app, users_repository, tokens_repository)
    use_case = AuthUseCase(users_repository, tokens_repository)
    blueprint = Blueprint("auth", __name__, url_prefix="/api/auth")

    @blueprint.post("/login")
    def login():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"message": "Envie um objeto JSON válido"}), 400
        email = data.get("email")
        password = data.get("password")
        if not isinstance(email, str) or not isinstance(password, str):
            return jsonify({"message": "E-mail e senha devem ser textos"}), 400
        if not email.strip() or not password:
            return jsonify({"message": "E-mail e senha são obrigatórios"}), 400

        try:
            identity = use_case.authenticate(email, password)
        except ValueError:
            return jsonify({"message": "Usuario ou Senha inválidas"}), 401

        token = create_access_token(identity=identity["id"])
        return jsonify({"access_token": token, "user": identity})

    @blueprint.get("/me")
    @jwt_required()
    def me():
        return jsonify(current_user.to_public())

    @blueprint.post("/logout")
    @jwt_required()
    def logout():
        token = get_jwt()
        use_case.logout(token["jti"], datetime.fromtimestamp(token["exp"], timezone.utc))
        return "", 204

    return blueprint
