from flask import Blueprint, jsonify

from infra.http.authentication import authenticated, identity
from infra.http.contract import Actions
from infra.http.documentation import documented


def create_routes(actions: Actions):
    blueprint = Blueprint("graph", __name__)

    @blueprint.get("/graph")
    @documented(
        "Grafo",
        "Consultar amizades diretas",
        response="Graph",
        body=None,
        status=200,
        public=False,
        multipart=False,
    )
    @authenticated
    def graph():
        return jsonify(actions.getCloseNetwork.execute(identity()))

    @blueprint.get("/graph/paths/<identifier>")
    @documented(
        "Grafo",
        "Consultar caminho até uma pessoa",
        response="PathResult",
        body=None,
        status=200,
        public=False,
        multipart=False,
    )
    @authenticated
    def path(identifier):
        return jsonify(actions.getPath.execute(identity(), identifier))

    return blueprint
