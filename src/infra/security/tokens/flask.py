from flask import jsonify
from flask_jwt_extended import JWTManager, create_access_token


class FlaskTokenIssuer:
    def issue(self, identifier, version):
        return create_access_token(
            identity=identifier, additional_claims={"auth_version": version}
        )


def configure_tokens(app, repositories):
    jwt = JWTManager(app)

    def unauthorized(*args):
        return jsonify({"message": "Autenticação inválida"}), 401

    for register in (
        jwt.unauthorized_loader,
        jwt.invalid_token_loader,
        jwt.expired_token_loader,
        jwt.user_lookup_error_loader,
        jwt.revoked_token_loader,
    ):
        register(unauthorized)

    @jwt.token_in_blocklist_loader
    def revoked(header, payload):
        return repositories.tokens.is_revoked(payload["jti"])

    @jwt.user_lookup_loader
    def account(header, payload):
        identifier = payload.get("sub")
        if not isinstance(identifier, str):
            return None
        user = repositories.users.get(identifier)
        return (
            user
            if user
            and user.is_active
            and type(payload.get("auth_version")) is int
            and payload["auth_version"] == user.auth_version
            else None
        )
