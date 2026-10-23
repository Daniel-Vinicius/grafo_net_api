"""Aceite HTTP com o repositório em memória; nenhum MongoDB é acessado."""

from dataclasses import replace
from datetime import timedelta

import bcrypt
import pytest
from flask_jwt_extended import create_access_token, decode_token

from app import create_app
from modules.auth.domain.user import User
from modules.auth.repositories.in_memory.repository import InMemoryUserRepository

SECRET = "auth-test-only-secret-with-at-least-32-bytes"
ERROR = {"message": "Usuario ou Senha inválidas"}


@pytest.fixture
def auth():
    password = "senha-de-teste"
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode()
    user = User("1", "joao@example.com", password_hash, True)
    records = [user]
    repository = InMemoryUserRepository(records)
    app = create_app(
        {"TESTING": True, "JWT_SECRET_KEY": SECRET, "JWT_COOKIE_SECURE": False},
        users=repository,
    )
    return app, app.test_client(), records, password


@pytest.mark.parametrize("case", ["inactive", "unknown", "wrong", "long_password"])
def test_login_failures_share_generic_401(auth, case):
    _app, client, records, password = auth
    email = records[0].email
    if case == "inactive":
        records[0] = replace(records[0], is_active=False)
    elif case == "unknown":
        email = "unknown@example.com"
    elif case == "long_password":
        password = "a" * 73
    else:
        password = "wrong"
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 401
    assert response.get_json() == ERROR
    assert client.get_cookie("access_token_cookie") is None
    assert client.get_cookie("csrf_access_token") is None


@pytest.mark.parametrize("data", [None, [], "text", {}, {"email": 1, "password": "x"},
    {"email": "a@b.com", "password": []}, {"email": " ", "password": "x"},
    {"email": "a@b.com", "password": ""}])
def test_invalid_login_input_returns_400(auth, data):
    _app, client, _records, _password = auth
    response = client.post("/api/auth/login", json=data)
    assert response.status_code == 400
    assert response.is_json


@pytest.mark.parametrize("case", ["expired", "tampered", "malformed", "wrong_key"])
def test_invalid_jwt_returns_json_401(auth, case):
    app, client, _records, _password = auth
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
        import jwt
        token = jwt.encode({"sub": "1"}, "other-secret-with-at-least-32-bytes", algorithm="HS256")
    client.set_cookie("access_token_cookie", token)
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.is_json


def test_jwt_contains_only_user_id_and_library_metadata(auth):
    app, client, records, password = auth
    client.post("/api/auth/login", json={"email": records[0].email, "password": password})
    cookie = client.get_cookie("access_token_cookie")
    assert cookie is not None
    with app.app_context():
        claims = decode_token(cookie.value)
    assert claims["sub"] == records[0].id
    assert claims["exp"] - claims["iat"] == 900
    assert "csrf" in claims
    assert not {"email", "password", "password_hash", "is_active"} & claims.keys()


@pytest.mark.parametrize("change", ["deleted", "inactive"])
@pytest.mark.parametrize("endpoint", ["/api/auth/me", "/api/auth/logout"])
def test_protected_routes_reload_user(auth, change, endpoint):
    _app, client, records, password = auth
    client.post("/api/auth/login", json={"email": records[0].email, "password": password})
    csrf = client.get_cookie("csrf_access_token")
    assert csrf is not None
    if change == "deleted":
        records.clear()
    else:
        records[0] = replace(records[0], is_active=False)
    if endpoint.endswith("logout"):
        response = client.post(endpoint, headers={"X-CSRF-TOKEN": csrf.value})
    else:
        response = client.get(endpoint)
    assert response.status_code == 401
    assert response.is_json


def test_logout_only_removes_this_browsers_token(auth):
    _app, first, records, password = auth
    second = _app.test_client()
    for client in (first, second):
        assert client.post("/api/auth/login", json={
            "email": records[0].email, "password": password,
        }).status_code == 200
    csrf = first.get_cookie("csrf_access_token")
    assert csrf is not None
    assert first.post("/api/auth/logout", headers={"X-CSRF-TOKEN": csrf.value}).status_code == 204
    assert first.get("/api/auth/me").status_code == 401
    assert second.get("/api/auth/me").status_code == 200


def test_cookie_security_flags_in_https(auth):
    app, _client, records, password = auth
    app.config["JWT_COOKIE_SECURE"] = True
    response = app.test_client().post("/api/auth/login", base_url="https://localhost", json={
        "email": records[0].email, "password": password,
    })
    cookies = response.headers.getlist("Set-Cookie")
    assert len(cookies) == 2
    assert all("Secure" in cookie and "SameSite=Lax" in cookie for cookie in cookies)
    assert "HttpOnly" in next(c for c in cookies if c.startswith("access_token_cookie="))


@pytest.mark.parametrize("secret", [None, "", "short"])
def test_app_rejects_missing_or_short_secret(secret):
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        create_app({"TESTING": True, "JWT_SECRET_KEY": secret})
