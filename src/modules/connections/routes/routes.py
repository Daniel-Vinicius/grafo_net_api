from flask import Blueprint, jsonify

from infra.http.authentication import authenticated, identity
from infra.http.boundary import json_body
from infra.http.contract import Actions
from infra.http.documentation import documented


def create_routes(actions: Actions):
    blueprint = Blueprint("connections", __name__)

    @blueprint.get("/connections")
    @documented(
        "Conexões",
        "Listar conexões",
        response="Connections",
        body=None,
        status=200,
        public=False,
        multipart=False,
    )
    @authenticated
    def connections():
        return jsonify(actions.listConnections.execute(identity()))

    @blueprint.post("/connections")
    @documented(
        "Conexões",
        "Solicitar conexão",
        response="Connection",
        body="ConnectionInput",
        status=201,
        public=False,
        multipart=False,
    )
    @authenticated
    def request_connection():
        return jsonify(
            actions.requestConnection.execute(
                identity(), json_body({"target_user_id"}).get("target_user_id")
            )
        ), 201

    @blueprint.post("/connections/<identifier>/accept")
    @documented(
        "Conexões",
        "Aceitar conexão",
        response="Connection",
        body=None,
        status=200,
        public=False,
        multipart=False,
    )
    @authenticated
    def accept_connection(identifier):
        return jsonify(actions.acceptConnection.execute(identity(), identifier))

    @blueprint.delete("/connections/<identifier>")
    @documented(
        "Conexões",
        "Cancelar, recusar ou remover conexão",
        response=None,
        body=None,
        status=204,
        public=False,
        multipart=False,
    )
    @authenticated
    def remove_connection(identifier):
        actions.removeConnection.execute(identity(), identifier)
        return "", 204

    return blueprint
