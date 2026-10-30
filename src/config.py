"""Carrega as configurações da aplicação e permite sobrescritas explícitas."""

import os
import math
from collections.abc import Mapping
from datetime import timedelta
from urllib.parse import urlsplit

from dotenv import load_dotenv
from flask import Flask, request


def configure_app(app: Flask, config: Mapping[str, object] | None = None) -> None:
    load_dotenv()
    app.config.from_mapping(
        JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY"),
        JWT_TOKEN_LOCATION=["headers"],
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=15),
        MONGO_URI=os.getenv("MONGO_URI"),
        MONGO_DB=os.getenv("MONGO_DB"),
        SMTP_HOST=os.getenv("SMTP_HOST", "smtp.sendgrid.net"),
        SMTP_PORT=int(os.getenv("SMTP_PORT", "587")),
        SMTP_FROM=os.getenv("SMTP_FROM"),
        SMTP_USERNAME=os.getenv("SMTP_USERNAME"),
        SMTP_PASSWORD=os.getenv("SMTP_PASSWORD"),
        SMTP_USE_TLS=os.getenv("SMTP_USE_TLS", "true").lower() == "true",
        FRONTEND_URL=os.getenv("FRONTEND_URL", "http://localhost:5173"),
        BOOTSTRAP_KEY=os.getenv("BOOTSTRAP_KEY") or None,
        GEMINI_API_KEY=os.getenv("GEMINI_API_KEY") or None,
        GEMINI_TIMEOUT=float(os.getenv("GEMINI_TIMEOUT", "15")),
        SEARCH_MIN_SCORE=float(os.getenv("SEARCH_MIN_SCORE", "0.50")),
    )
    if config is not None:
        app.config.from_mapping(config)
    minimum = app.config["SEARCH_MIN_SCORE"]
    timeout = app.config["GEMINI_TIMEOUT"]
    if not isinstance(minimum, (float, int)) or not math.isfinite(minimum) or not -1 <= minimum <= 1:
        raise ValueError("SEARCH_MIN_SCORE deve estar entre -1 e 1")
    if not isinstance(timeout, (float, int)) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("GEMINI_TIMEOUT deve ser positivo")
    secret = app.config["JWT_SECRET_KEY"]
    if not isinstance(secret, str) or len(secret.encode("utf-8")) < 32:
        raise ValueError("JWT_SECRET_KEY deve ter pelo menos 32 bytes")
    bootstrap_key = app.config["BOOTSTRAP_KEY"]
    if bootstrap_key is not None and (not isinstance(bootstrap_key, str) or len(bootstrap_key.encode()) < 32):
        raise ValueError("BOOTSTRAP_KEY deve ter pelo menos 32 bytes")
    frontend = urlsplit(app.config["FRONTEND_URL"])
    if frontend.scheme not in ("http", "https") or not frontend.netloc or frontend.query or frontend.fragment:
        raise ValueError("FRONTEND_URL deve ser uma URL HTTP ou HTTPS sem query ou fragmento")


def configure_cors(app: Flask) -> None:
    parsed = urlsplit(app.config["FRONTEND_URL"])
    allowed = f"{parsed.scheme}://{parsed.netloc}"

    @app.after_request
    def cors(response):
        response.vary.add("Origin")
        if request.headers.get("Origin") == allowed:
            response.headers["Access-Control-Allow-Origin"] = allowed
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Bootstrap-Key"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            response.headers["Access-Control-Max-Age"] = "600"
        return response
