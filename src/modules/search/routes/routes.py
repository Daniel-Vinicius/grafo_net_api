from flask import Blueprint, Flask, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from pymongo.errors import PyMongoError

from modules.connections.domain.errors import NetworkError
from modules.connections.repositories.contract import ConnectionRepository
from modules.graph.useCases.buildGraph.buildGraph import GraphUseCase
from modules.search.commands import register_search_commands
from modules.search.embeddings import EmbeddingUnavailable, GeminiEmbeddings
from modules.search.repositories.mongo.repository import MongoEmbeddingRepository
from modules.search.useCases.index.index import IndexProfilesUseCase
from modules.search.useCases.search.search import SearchUseCase


def create_search_routes(
    app: Flask,
    index: IndexProfilesUseCase | None = None,
    connections_repository: ConnectionRepository | None = None,
) -> Blueprint:
    if index is None:
        index = IndexProfilesUseCase(
            app.extensions["profile_repository"],
            MongoEmbeddingRepository(app.extensions["mongo_database"]),
            GeminiEmbeddings(app.config["GEMINI_API_KEY"], app.config["GEMINI_TIMEOUT"]),
        )
    connections: ConnectionRepository = (connections_repository if connections_repository is not None
                                         else app.extensions["connection_repository"])
    app.extensions["index_profiles_use_case"] = index
    app.extensions["profile_saved"] = index.refresh
    graph = GraphUseCase(index.profiles, connections)
    search = SearchUseCase(index, app.config["SEARCH_MIN_SCORE"])
    register_search_commands(app, index)
    blueprint = Blueprint("search", __name__, url_prefix="/search")

    @blueprint.errorhandler(NetworkError)
    def invalid(error: NetworkError):
        return jsonify({"message": str(error)}), error.status

    @blueprint.errorhandler(EmbeddingUnavailable)
    def provider_unavailable(_error: EmbeddingUnavailable):
        return jsonify({"message": "Busca indisponível; tente novamente mais tarde"}), 503

    @blueprint.errorhandler(PyMongoError)
    def database_unavailable(_error: PyMongoError):
        return jsonify({"message": "Banco indisponível"}), 503

    @blueprint.post("")
    @jwt_required()
    def search_profiles():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise NetworkError("Envie um objeto JSON válido")
        catalogs = graph.profiles.catalogs()
        snapshot = graph.snapshot(catalogs)
        return jsonify(search.search(get_jwt_identity(), snapshot, catalogs, data.get("query"),
                                     data.get("mode", "proximity"), data.get("limit", 10), data.get("offset", 0)))

    return blueprint
