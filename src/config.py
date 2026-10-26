"""Carrega as configurações da aplicação e permite sobrescritas explícitas."""

import os
from collections.abc import Mapping
from datetime import timedelta

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
    )
    if config is not None:
        app.config.from_mapping(config)
    secret = app.config["JWT_SECRET_KEY"]
    if not isinstance(secret, str) or len(secret.encode("utf-8")) < 32:
        raise ValueError("JWT_SECRET_KEY deve ter pelo menos 32 bytes")
