from flask import Blueprint, jsonify

from infra.http.contract import Actions
from infra.http.documentation import documented


def create_routes(actions: Actions):
    blueprint = Blueprint("health", __name__)

    @blueprint.get("/health")
    @documented(
        "Saúde",
        "Consultar disponibilidade",
        response="Health",
        body=None,
        status=200,
        public=True,
        multipart=False,
    )
    def health():
        return jsonify({"status": "ok"})

    return blueprint
