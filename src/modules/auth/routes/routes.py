from flask import Blueprint, jsonify, make_response, request
from flask_jwt_extended import (
    create_access_token,
    current_user,
    jwt_required,
    set_access_cookies,
    unset_jwt_cookies,
)

from modules.auth.repositories.contract import UserRepository
from modules.auth.useCases.login.login import AuthService


def create_auth_routes(users: UserRepository) -> Blueprint:
    blueprint = Blueprint("auth", __name__, url_prefix="/api/auth")
    service = AuthService(users)

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
            identity = service.authenticate(email, password)
        except ValueError:
            return jsonify({"message": "Usuario ou Senha inválidas"}), 401

        token = create_access_token(identity=identity["id"])
        response = jsonify(identity)
        set_access_cookies(response, token)
        return response

    @blueprint.get("/me")
    @jwt_required()
    def me():
        return jsonify(current_user.to_public())

    @blueprint.post("/logout")
    @jwt_required()
    def logout():
        # A resposta 204 não tem corpo; os headers expiram os cookies no navegador.
        response = make_response("", 204)
        unset_jwt_cookies(response)
        return response

    return blueprint
