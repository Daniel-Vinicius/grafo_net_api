from dataclasses import replace
from datetime import timedelta

import bcrypt
from flask import Flask
from flask_jwt_extended import create_access_token, decode_token
import jwt
import pytest

from app import create_app
from config import configure_app
from modules.auth.domain.user import User
from modules.auth.repositories.in_memory.repository import InMemoryTokenRepository, InMemoryUserRepository
from modules.auth.routes.routes import create_auth_routes


@pytest.fixture
def auth():
    password = "senha-de-teste"
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode()
    records = [User("1", "joao@example.com", password_hash, True)]
    app = Flask(__name__)
    configure_app(app, {
        "TESTING": True,
        "JWT_SECRET_KEY": "auth-test-only-secret-at-least-32-bytes",
    })
    app.register_blueprint(create_auth_routes(
        app, InMemoryUserRepository(records), InMemoryTokenRepository(),
    ))
    return app, app.test_client(), records, password


def test_login_returns_bearer_token_and_allows_me(auth):
    app, client, records, password = auth
    response = client.post("/api/auth/login", json={
        "email": " Joao@EXAMPLE.com ", "password": password,
    })
    assert response.status_code == 200
    assert response.json["user"] == records[0].to_public()
    assert "Set-Cookie" not in response.headers
    token = response.json["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json == records[0].to_public()
    with app.app_context():
        claims = decode_token(token)
    assert claims["sub"] == records[0].id
    assert claims["exp"] - claims["iat"] == 900
    assert not {"email", "password", "password_hash", "is_active"} & claims.keys()
    client.set_cookie("access_token_cookie", token)
    assert client.get("/api/auth/me").status_code == 401


@pytest.mark.parametrize("case", ["inactive", "unknown", "wrong", "long_password"])
def test_login_rejects_invalid_credentials(auth, case):
    _app, client, records, password = auth
    email = records[0].email
    if case == "inactive":
        records[0] = replace(records[0], is_active=False)
    elif case == "unknown":
        email = "unknown@example.com"
    else:
        password = "a" * 73 if case == "long_password" else "wrong"
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 401
    assert response.json == {"message": "Usuario ou Senha inválidas"}


@pytest.mark.parametrize("data", [None, [], "text", {}, {"email": 1, "password": "x"},
    {"email": "a@b.com", "password": []}, {"email": " ", "password": "x"},
    {"email": "a@b.com", "password": ""}])
def test_login_rejects_invalid_json(auth, data):
    _app, client, _records, _password = auth
    assert client.post("/api/auth/login", json=data).status_code == 400


@pytest.mark.parametrize("case", ["missing", "expired", "tampered", "malformed", "wrong_key"])
def test_me_rejects_invalid_jwt(auth, case):
    app, client, _records, _password = auth
    headers = {}
    if case != "missing":
        with app.app_context():
            token = create_access_token(identity="1", expires_delta=timedelta(seconds=-1)
                if case == "expired" else timedelta(minutes=15))
        if case == "malformed":
            token = "not-a-jwt"
        elif case == "tampered":
            header, payload, signature = token.split(".")
            signature = ("A" if signature[0] != "A" else "B") + signature[1:]
            token = ".".join([header, payload, signature])
        elif case == "wrong_key":
            token = jwt.encode({"sub": "1"}, "other-secret-with-at-least-32-bytes", algorithm="HS256")
        headers["Authorization"] = f"Bearer {token}"
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 401 and response.is_json


@pytest.mark.parametrize("change", ["deleted", "inactive"])
def test_me_reloads_user(auth, change):
    _app, client, records, password = auth
    response = client.post("/api/auth/login", json={
        "email": records[0].email, "password": password,
    })
    token = response.json["access_token"]
    if change == "deleted":
        records.clear()
    else:
        records[0] = replace(records[0], is_active=False)
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401 and response.is_json


@pytest.mark.parametrize("secret", [None, "", "short"])
def test_rejects_invalid_jwt_secret(secret):
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        create_app({"TESTING": True, "JWT_SECRET_KEY": secret})


def test_logout_revokes_only_the_presented_token(auth):
    _app, client, records, password = auth
    payload = {"email": records[0].email, "password": password}
    first = client.post("/api/auth/login", json=payload).json["access_token"]
    second = client.post("/api/auth/login", json=payload).json["access_token"]
    first_headers = {"Authorization": f"Bearer {first}"}
    second_headers = {"Authorization": f"Bearer {second}"}
    assert client.post("/api/auth/logout").status_code == 401
    assert client.post("/api/auth/logout", headers=first_headers).status_code == 204
    assert client.get("/api/auth/me", headers=first_headers).status_code == 401
    assert client.post("/api/auth/logout", headers=first_headers).status_code == 401
    assert client.get("/api/auth/me", headers=second_headers).status_code == 200
