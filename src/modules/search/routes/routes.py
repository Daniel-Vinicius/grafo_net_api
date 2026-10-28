from flask import Blueprint, jsonify

from infra.http.authentication import authenticated, identity
from infra.http.boundary import json_body
from infra.http.contract import Actions
from infra.http.documentation import documented


def create_routes(actions: Actions):
    blueprint = Blueprint("search", __name__)

    @blueprint.post("/search")
    @documented(
        "Busca",
        "Buscar pessoas por afinidade e caminho",
        response="SearchResult",
        body="SearchInput",
        status=200,
        public=False,
        multipart=False,
    )
    @authenticated
    def search():
        return jsonify(actions.searchProfiles.execute(identity(), json_body()))

    return blueprint
