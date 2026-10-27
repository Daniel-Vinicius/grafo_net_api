from datetime import datetime, timezone

from flask import Blueprint, Flask, jsonify, request
from flask_jwt_extended import create_access_token, current_user, get_jwt, get_jwt_identity, jwt_required
from pymongo.errors import PyMongoError

from database.connection import create_database
from modules.auth.domain.errors import (
    AuthenticationRequiredError, BootstrapForbiddenError, DuplicateEmailError,
    EmailDeliveryError, ValidationError,
)
from modules.auth.email import EmailSender, SMTPEmailSender
from modules.auth.jwt import configure_jwt
from modules.auth.repositories.contract import InviteRepository, TokenRepository, UserRepository
from modules.auth.repositories.mongo.repository import MongoInviteRepository, MongoTokenRepository, MongoUserRepository
from modules.auth.useCases.invite.invite import InviteUseCase
from modules.auth.useCases.login.login import AuthUseCase
from modules.auth.useCases.register.register import RegisterUseCase
from modules.connections.domain.errors import NetworkError
from modules.connections.repositories.contract import ConnectionRepository
from modules.connections.repositories.mongo.repository import MongoConnectionRepository
from modules.search.hooks import profile_saved


def create_auth_routes(
    app: Flask,
    users_repository: UserRepository | None = None,
    tokens_repository: TokenRepository | None = None,
    invites_repository: InviteRepository | None = None,
    mailer: EmailSender | None = None,
    connections_repository: ConnectionRepository | None = None,
) -> Blueprint:
    if users_repository is None or tokens_repository is None or invites_repository is None:
        database = create_database(app.config["MONGO_URI"], app.config["MONGO_DB"])
        app.extensions["mongo_client"] = database.client
        app.extensions["mongo_database"] = database
        if users_repository is None:
            users_repository = MongoUserRepository(database)
        if tokens_repository is None:
            tokens_repository = MongoTokenRepository(database)
        if invites_repository is None:
            invites_repository = MongoInviteRepository(database)
        if connections_repository is None:
            connections_repository = MongoConnectionRepository(database)
    if mailer is None:
        mailer = SMTPEmailSender(
            app.config["SMTP_HOST"], app.config["SMTP_PORT"], app.config["SMTP_FROM"],
            app.config["SMTP_USERNAME"], app.config["SMTP_PASSWORD"], app.config["SMTP_USE_TLS"],
        )
    app.extensions["user_repository"] = users_repository
    app.extensions["connection_repository"] = connections_repository or getattr(invites_repository, "connections", None)
    configure_jwt(app, users_repository, tokens_repository)
    auth = AuthUseCase(users_repository, tokens_repository)
    registration = RegisterUseCase(users_repository, invites_repository)
    invitations = InviteUseCase(
        users_repository, invites_repository, mailer, app.config["FRONTEND_URL"], app.config["BOOTSTRAP_KEY"],
    )
    blueprint = Blueprint("auth", __name__)

    def json_body() -> dict:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise ValidationError("Envie um objeto JSON válido")
        return data

    @blueprint.errorhandler(ValidationError)
    def invalid_input(error):
        return jsonify({"message": str(error)}), 400

    @blueprint.errorhandler(DuplicateEmailError)
    def duplicate_email(error):
        return jsonify({"message": str(error)}), 409

    @blueprint.errorhandler(NetworkError)
    def network_error(error: NetworkError):
        return jsonify({"message": str(error)}), error.status

    @blueprint.errorhandler(AuthenticationRequiredError)
    def authentication_required(error):
        return jsonify({"message": str(error)}), 401

    @blueprint.errorhandler(BootstrapForbiddenError)
    def bootstrap_forbidden(error):
        return jsonify({"message": str(error)}), 403

    @blueprint.errorhandler(EmailDeliveryError)
    @blueprint.errorhandler(PyMongoError)
    def unavailable(error):
        message = "Não foi possível enviar o convite" if isinstance(error, EmailDeliveryError) else "Banco indisponível"
        return jsonify({"message": message}), 503

    @blueprint.post("/invitations")
    @jwt_required(optional=True)
    def issue_invite():
        data = json_body()
        invite = invitations.issue(data.get("email"), get_jwt_identity(), request.headers.get("X-Bootstrap-Key"))
        return jsonify(invite), 201

    @blueprint.post("/auth/register")
    def register():
        data = json_body()
        identity = registration.register(
            data.get("name"), data.get("email"), data.get("password"), data.get("invite_token"),
        )
        profile_saved(app, identity["id"])
        return jsonify(identity), 201

    @blueprint.post("/auth/login")
    def login():
        data = json_body()
        email = data.get("email")
        password = data.get("password")
        if not isinstance(email, str) or not isinstance(password, str):
            raise ValidationError("E-mail e senha devem ser textos")
        if not email.strip() or not password:
            raise ValidationError("E-mail e senha são obrigatórios")
        try:
            identity = auth.authenticate(email, password)
        except ValueError:
            return jsonify({"message": "Usuario ou Senha inválidas"}), 401
        token = create_access_token(identity=identity["id"])
        return jsonify({"access_token": token, "user": identity})

    @blueprint.get("/auth/me")
    @jwt_required()
    def me():
        return jsonify(current_user.to_public())

    @blueprint.post("/auth/logout")
    @jwt_required()
    def logout():
        token = get_jwt()
        auth.logout(token["jti"], datetime.fromtimestamp(token["exp"], timezone.utc))
        return "", 204

    return blueprint
