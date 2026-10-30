import math
import os
from datetime import timedelta
from urllib.parse import urlsplit

from dotenv import load_dotenv


def settings(overrides=None):
    load_dotenv()
    config = {
        "JWT_SECRET_KEY": os.getenv("JWT_SECRET_KEY"),
        "JWT_TOKEN_LOCATION": ["headers"],
        "JWT_ACCESS_TOKEN_EXPIRES": timedelta(minutes=15),
        "MONGO_URI": os.getenv("MONGO_URI"),
        "MONGO_DB": os.getenv("MONGO_DB"),
        "BOOTSTRAP_KEY": os.getenv("BOOTSTRAP_KEY") or None,
        "SMTP_HOST": os.getenv("SMTP_HOST", "127.0.0.1"),
        "SMTP_PORT": os.getenv("SMTP_PORT", "1025"),
        "SMTP_FROM": os.getenv("SMTP_FROM", "grafonet@insper.edu.br"),
        "SMTP_USERNAME": os.getenv("SMTP_USERNAME"),
        "SMTP_PASSWORD": os.getenv("SMTP_PASSWORD"),
        "SMTP_USE_TLS": os.getenv("SMTP_USE_TLS", "false"),
        "FRONTEND_URL": os.getenv("FRONTEND_URL", "http://localhost:5173"),
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY") or None,
        "GEMINI_TIMEOUT": os.getenv("GEMINI_TIMEOUT", "15"),
        "SEARCH_MIN_SCORE": os.getenv("SEARCH_MIN_SCORE", "0.50"),
    }
    config.update(overrides or {})
    for key in ("JWT_SECRET_KEY", "BOOTSTRAP_KEY"):
        value = config[key]
        if key == "BOOTSTRAP_KEY" and value is None:
            continue
        if not isinstance(value, str) or len(value.encode()) < 32:
            raise ValueError(f"{key} precisa de pelo menos 32 bytes")
    for key in ("SEARCH_MIN_SCORE", "GEMINI_TIMEOUT"):
        if isinstance(config[key], bool):
            raise ValueError(f"{key} deve ser numérico")
        config[key] = float(config[key])
        if not math.isfinite(config[key]):
            raise ValueError(f"{key} deve ser finito")
    if not -1 <= config["SEARCH_MIN_SCORE"] <= 1 or config["GEMINI_TIMEOUT"] <= 0:
        raise ValueError("Configuração de busca inválida")
    config["SMTP_PORT"] = int(config["SMTP_PORT"])
    config["SMTP_USE_TLS"] = str(config["SMTP_USE_TLS"]).lower() == "true"
    url = urlsplit(config["FRONTEND_URL"])
    if (
        url.scheme not in ("http", "https")
        or not url.netloc
        or url.query
        or url.fragment
    ):
        raise ValueError("FRONTEND_URL inválida")
    return config
