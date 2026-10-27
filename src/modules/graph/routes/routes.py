from flask import Blueprint, Flask, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from pymongo.errors import PyMongoError

from modules.connections.domain.errors import NetworkError
from modules.connections.repositories.contract import ConnectionRepository
from modules.graph.repositories.contract import ProfileRepository
from modules.graph.repositories.mongo.repository import MongoProfileRepository
from modules.graph.useCases.buildGraph.buildGraph import GraphUseCase


def create_graph_routes(
    app: Flask,
    profiles_repository: ProfileRepository | None = None,
    connections_repository: ConnectionRepository | None = None,
) -> Blueprint:
    if profiles_repository is None:
        profiles_repository = MongoProfileRepository(app.extensions["mongo_database"])
    connections: ConnectionRepository = (connections_repository if connections_repository is not None
                                         else app.extensions["connection_repository"])
    app.extensions["profile_repository"] = profiles_repository
    graph = GraphUseCase(profiles_repository, connections)
    blueprint = Blueprint("graph", __name__, url_prefix="/graph")

    @blueprint.errorhandler(NetworkError)
    def invalid(error: NetworkError):
        return jsonify({"message": str(error)}), error.status

    @blueprint.errorhandler(PyMongoError)
    def unavailable(_error: PyMongoError):
        return jsonify({"message": "Banco indisponível"}), 503

    @blueprint.get("")
    @jwt_required()
    def close_network():
        return jsonify(graph.snapshot().close_network(get_jwt_identity()))

    @blueprint.get("/paths/<target_id>")
    @jwt_required()
    def path(target_id: str):
        snapshot = graph.snapshot()
        snapshot.require(target_id)
        origin = get_jwt_identity()
        result = snapshot.paths_from(origin).path_to(target_id)
        return jsonify({"path": result.public() if result else None,
                        "graph": snapshot.visualization(origin, [result], [target_id])})

    return blueprint
