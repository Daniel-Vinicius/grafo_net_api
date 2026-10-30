from unittest.mock import patch

from flask import Flask

from config import configure_app


def test_sendgrid_is_the_default_mail_configuration(monkeypatch):
    for name in (
        "SMTP_HOST", "SMTP_PORT", "SMTP_FROM", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_USE_TLS",
    ):
        monkeypatch.delenv(name, raising=False)

    with patch("config.load_dotenv"):
        app = Flask(__name__)
        configure_app(app, {"JWT_SECRET_KEY": "config-test-secret-at-least-32-bytes"})

    assert app.config["SMTP_HOST"] == "smtp.sendgrid.net"
    assert app.config["SMTP_PORT"] == 587
    assert app.config["SMTP_FROM"] == ""
    assert app.config["SMTP_USERNAME"] is None
    assert app.config["SMTP_PASSWORD"] is None
    assert app.config["SMTP_USE_TLS"] is True


def test_smtp_configuration_can_be_overridden_by_environment(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "mailpit")
    monkeypatch.setenv("SMTP_PORT", "1025")
    monkeypatch.setenv("SMTP_FROM", "grafonet@localhost")
    monkeypatch.setenv("SMTP_USE_TLS", "false")

    with patch("config.load_dotenv"):
        app = Flask(__name__)
        configure_app(app, {"JWT_SECRET_KEY": "config-test-secret-at-least-32-bytes"})

    assert app.config["SMTP_HOST"] == "mailpit"
    assert app.config["SMTP_PORT"] == 1025
    assert app.config["SMTP_FROM"] == "grafonet@localhost"
    assert app.config["SMTP_USE_TLS"] is False
