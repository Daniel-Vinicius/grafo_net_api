from flask import Blueprint, Flask, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from pymongo.errors import PyMongoError

from modules.auth.repositories.contract import UserRepository
from modules.connections.domain.errors import NetworkError
from modules.connections.repositories.contract import ConnectionRepository
from modules.connections.useCases.manage.manage import ConnectionUseCase


def create_connections_routes(
    app: Flask,
    connections_repository: ConnectionRepository | None = None,
    users_repository: UserRepository | None = None,
) -> Blueprint:
    repository: ConnectionRepository = (connections_repository if connections_repository is not None
                                        else app.extensions["connection_repository"])
    users: UserRepository = (users_repository if users_repository is not None
                             else app.extensions["user_repository"])
    connections = ConnectionUseCase(repository, users)
    blueprint = Blueprint("connections", __name__, url_prefix="/connections")

    @blueprint.errorhandler(NetworkError)
    def invalid(error: NetworkError):
        return jsonify({"message": str(error)}), error.status

    @blueprint.errorhandler(PyMongoError)
    def unavailable(_error: PyMongoError):
        return jsonify({"message": "Banco indisponível"}), 503

    @blueprint.get("")
    @jwt_required()
    def list_connections():
        records = connections.repository.list_for(get_jwt_identity())
        return jsonify({"connections": [item.public() for item in sorted(records, key=lambda c: c.id)]})

    @blueprint.post("")
    @jwt_required()
    def request_connection():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise NetworkError("Envie um objeto JSON válido")
        connection = connections.request(get_jwt_identity(), data.get("target_user_id"))
        return jsonify(connection.public()), 201

    @blueprint.post("/<connection_id>/accept")
    @jwt_required()
    def accept(connection_id: str):
        return jsonify(connections.accept(get_jwt_identity(), connection_id).public())

    @blueprint.delete("/<connection_id>")
    @jwt_required()
    def remove(connection_id: str):
        connections.remove(get_jwt_identity(), connection_id)
        return "", 204

    return blueprint
