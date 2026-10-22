from flask import Blueprint, Response, jsonify

def create_health_routes() -> Blueprint:
    routes = Blueprint("health", __name__)

    @routes.get("/health")
    def health() -> Response:
        return jsonify(status="ok")

    return routes
