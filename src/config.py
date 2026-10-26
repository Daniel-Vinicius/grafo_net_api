"""Carrega as configurações da aplicação e permite sobrescritas explícitas."""

import os
from collections.abc import Mapping
from datetime import timedelta
from urllib.parse import urlsplit

from dotenv import load_dotenv
from flask import Flask


def configure_app(app: Flask, config: Mapping[str, object] | None = None) -> None:
    load_dotenv()
    app.config.from_mapping(
        JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY"),
        JWT_TOKEN_LOCATION=["headers"],
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=15),
        MONGO_URI=os.getenv("MONGO_URI"),
        MONGO_DB=os.getenv("MONGO_DB"),
        SMTP_HOST=os.getenv("SMTP_HOST", "127.0.0.1"),
        SMTP_PORT=int(os.getenv("SMTP_PORT", "1025")),
        SMTP_FROM=os.getenv("SMTP_FROM", "grafonet@insper.edu.br"),
        SMTP_USERNAME=os.getenv("SMTP_USERNAME"),
        SMTP_PASSWORD=os.getenv("SMTP_PASSWORD"),
        SMTP_USE_TLS=os.getenv("SMTP_USE_TLS", "false").lower() == "true",
        FRONTEND_URL=os.getenv("FRONTEND_URL", "http://localhost:5173"),
        BOOTSTRAP_KEY=os.getenv("BOOTSTRAP_KEY") or None,
    )
    if config is not None:
        app.config.from_mapping(config)
    secret = app.config["JWT_SECRET_KEY"]
    if not isinstance(secret, str) or len(secret.encode("utf-8")) < 32:
        raise ValueError("JWT_SECRET_KEY deve ter pelo menos 32 bytes")
    bootstrap_key = app.config["BOOTSTRAP_KEY"]
    if bootstrap_key is not None and (not isinstance(bootstrap_key, str) or len(bootstrap_key.encode()) < 32):
        raise ValueError("BOOTSTRAP_KEY deve ter pelo menos 32 bytes")
    frontend = urlsplit(app.config["FRONTEND_URL"])
    if frontend.scheme not in ("http", "https") or not frontend.netloc or frontend.query or frontend.fragment:
        raise ValueError("FRONTEND_URL deve ser uma URL HTTP ou HTTPS sem query ou fragmento")
