from urllib.parse import urlsplit

from flask import jsonify, request
from werkzeug.exceptions import HTTPException

from infra.errors import ConflictError, UnavailableError
from modules.auth.domain.errors import (
    AuthenticationRequiredError,
    BootstrapForbiddenError,
    DuplicateEmailError,
    ForbiddenError,
    NotFoundError,
    PayloadTooLargeError,
    ValidationError,
)


def json_body(allowed=None):
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or (allowed is not None and set(data) - set(allowed)):
        raise ValidationError("Envie um objeto JSON com os campos permitidos")
    return data


def configure_http(app):
    codes = {
        ValidationError: 400,
        AuthenticationRequiredError: 401,
        BootstrapForbiddenError: 403,
        ForbiddenError: 403,
        NotFoundError: 404,
        DuplicateEmailError: 409,
        ConflictError: 409,
        PayloadTooLargeError: 413,
        UnavailableError: 503,
    }
    for error, status in codes.items():

        def handle(exception, code=status):
            return jsonify({"message": str(exception)}), code

        app.register_error_handler(error, handle)

    @app.errorhandler(HTTPException)
    def http_error(exception):
        return jsonify({"message": exception.description}), exception.code

    @app.errorhandler(Exception)
    def unexpected(exception):
        app.logger.exception("Falha inesperada na API")
        return jsonify({"message": "Erro interno"}), 500

    url = urlsplit(app.config["FRONTEND_URL"])
    origin = f"{url.scheme}://{url.netloc}"

    @app.after_request
    def cors(response):
        response.vary.add("Origin")
        if request.headers.get("Origin") == origin:
            response.headers.update(
                {
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Headers": "Authorization, Content-Type, X-Bootstrap-Key",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
                    "Access-Control-Max-Age": "600",
                    "Access-Control-Expose-Headers": "ETag",
                }
            )
        return response
