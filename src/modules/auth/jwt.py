"""Validação JWT e carregamento do usuário para todas as rotas protegidas."""

from typing import Any

from flask import Flask, jsonify
from flask_jwt_extended import JWTManager

from modules.auth.domain.user import User
from modules.auth.repositories.contract import TokenRepository, UserRepository


def configure_jwt(app: Flask, users: UserRepository, tokens: TokenRepository) -> JWTManager:
    jwt = JWTManager(app)

    def unauthorized(*_args: Any):
        return jsonify({"message": "Autenticação inválida"}), 401

    jwt.unauthorized_loader(unauthorized)
    jwt.invalid_token_loader(unauthorized)
    jwt.expired_token_loader(unauthorized)
    jwt.user_lookup_error_loader(unauthorized)
    jwt.revoked_token_loader(unauthorized)

    @jwt.token_in_blocklist_loader
    def is_revoked(_header: dict[str, Any], payload: dict[str, Any]) -> bool:
        return tokens.is_revoked(payload["jti"])

    @jwt.user_lookup_loader
    def load_user(_header: dict[str, Any], payload: dict[str, Any]) -> User | None:
        user_id = payload.get("sub")
        if not isinstance(user_id, str):
            return None
        user = users.find_by_id(user_id)
        return user if user is not None and user.is_active else None

    return jwt
