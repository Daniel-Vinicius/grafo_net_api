from dataclasses import replace
from datetime import timedelta
from unittest.mock import Mock
from urllib.parse import parse_qs, urlsplit

import bcrypt
from flask import Flask
from flask_jwt_extended import create_access_token, decode_token
import jwt
import pytest

from pymongo.errors import ServerSelectionTimeoutError

from app import create_app
from modules.auth.domain.errors import EmailDeliveryError
from modules.auth.domain.invite import token_hash
from modules.auth.email import EmailSender
from config import configure_app
from modules.auth.domain.user import User
from modules.auth.repositories.in_memory.repository import InMemoryInviteRepository, InMemoryTokenRepository, InMemoryUserRepository
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
    users = InMemoryUserRepository(records)
    app.register_blueprint(create_auth_routes(
        app, users, InMemoryTokenRepository(), InMemoryInviteRepository(users),
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


@pytest.fixture
def signup():
    app = Flask(__name__)
    configure_app(app, {
        "TESTING": True, "JWT_SECRET_KEY": "route-test-secret-at-least-32-bytes",
        "BOOTSTRAP_KEY": "b" * 32, "FRONTEND_URL": "http://localhost:5173",
    })
    users = InMemoryUserRepository([])
    invites = InMemoryInviteRepository(users)
    mailer = Mock(spec=EmailSender)
    app.register_blueprint(create_auth_routes(app, users, InMemoryTokenRepository(), invites, mailer))
    return app.test_client(), users, invites, mailer


def invitation_token(mailer):
    link = mailer.send_invite.call_args.args[1]
    return parse_qs(urlsplit(link).query)["token"][0]


def test_invite_register_login_and_authenticated_invite(signup):
    client, users, invites, mailer = signup
    email = "Pessoa@AL.INSPER.EDU.BR"
    assert client.post("/api/invitations", json={"email": email}).status_code == 401
    issued = client.post("/api/invitations", json={"email": email}, headers={"X-Bootstrap-Key": "b" * 32})
    assert issued.status_code == 201
    token = invitation_token(mailer)
    assert token not in issued.get_data(as_text=True)
    assert "token_hash" not in issued.json
    assert client.get("/api/auth/register", query_string={"token": token}).status_code == 405
    assert invites.find_by_hash(token_hash(token)).used_at is None
    data = {"profile": {"name": "Pessoa", "course_id": "computer-science", "semester": 1, "field_id": "technology", "bio": "Bio de teste"}, "email": email, "password": " senha1234 ", "invite_token": token}
    created = client.post("/api/auth/register", json=data)
    assert created.status_code == 201
    assert set(created.json) == {"id", "email"}
    assert created.json["email"] == email.lower()
    assert "Set-Cookie" not in created.headers
    user = users.find_by_id(created.json["id"])
    assert users._profiles[user.id].name == "Pessoa" and user.is_active
    login = client.post("/api/auth/login", json={"email": email, "password": data["password"]})
    assert login.status_code == 200
    headers = {"Authorization": "Bearer " + login.json["access_token"]}
    assert client.get("/api/auth/me", headers=headers).status_code == 200
    second = client.post("/api/invitations", json={"email": "outra@insper.edu.br"}, headers=headers)
    assert second.status_code == 201
    assert invites.find_by_hash(token_hash(invitation_token(mailer))).created_by == user.id
    assert client.post("/api/invitations", json={"email": "terceira@insper.edu.br"},
        headers={"X-Bootstrap-Key": "b" * 32}).status_code == 403
    assert client.post("/api/auth/register", json=data).status_code == 400
    assert client.post("/api/auth/logout", headers=headers).status_code == 204
    assert client.post("/api/invitations", json={"email": "terceira@insper.edu.br"}, headers=headers).status_code == 401


def test_invalid_jwt_cannot_fall_back_to_bootstrap(signup):
    client, _users, _invites, mailer = signup
    response = client.post("/api/invitations", json={"email": "a@insper.edu.br"}, headers={
        "Authorization": "Bearer invalid", "X-Bootstrap-Key": "b" * 32,
    })
    assert response.status_code == 401
    mailer.send_invite.assert_not_called()


@pytest.mark.parametrize("path", ["/api/invitations", "/api/auth/register"])
@pytest.mark.parametrize("data", [None, [], "text"])
def test_signup_routes_reject_non_object_json(signup, path, data):
    client, _users, _invites, _mailer = signup
    assert client.post(path, json=data, headers={"X-Bootstrap-Key": "b" * 32}).status_code == 400


def test_failed_smtp_returns_503_without_leaving_an_invite(signup):
    client, users, invites, mailer = signup
    mailer.send_invite.side_effect = EmailDeliveryError("SMTP indisponível")
    response = client.post("/api/invitations", json={"email": "a@insper.edu.br"},
        headers={"X-Bootstrap-Key": "b" * 32})
    assert response.status_code == 503
    assert not users.has_any() and not invites._invites


def test_database_failure_returns_503_without_sending_email(signup, monkeypatch):
    client, _users, invites, mailer = signup

    def unavailable(invite):
        raise ServerSelectionTimeoutError("Detalhe interno que não deve ser exposto")

    monkeypatch.setattr(invites, "save", unavailable)
    response = client.post("/api/invitations", json={"email": "a@insper.edu.br"},
        headers={"X-Bootstrap-Key": "b" * 32})
    assert response.status_code == 503
    assert "Detalhe interno" not in response.get_data(as_text=True)
    mailer.send_invite.assert_not_called()


def test_duplicate_email_returns_409_and_preserves_second_invite(signup):
    client, _users, invites, mailer = signup
    for _ in range(2):
        assert client.post("/api/invitations", json={"email": "a@insper.edu.br"},
            headers={"X-Bootstrap-Key": "b" * 32}).status_code == 201
    first_link = mailer.send_invite.call_args_list[0].args[1]
    first_token = parse_qs(urlsplit(first_link).query)["token"][0]
    second_token = invitation_token(mailer)
    data = {"profile": {"name": "Pessoa", "course_id": "computer-science", "semester": 1, "field_id": "technology", "bio": "Bio de teste"}, "email": "a@insper.edu.br", "password": "senha1234", "invite_token": first_token}
    assert client.post("/api/auth/register", json=data).status_code == 201
    data["invite_token"] = second_token
    assert client.post("/api/auth/register", json=data).status_code == 409
    assert invites.find_by_hash(token_hash(second_token)).used_at is None


@pytest.mark.parametrize("key", ["", "short"])
def test_rejects_short_bootstrap_key(key):
    with pytest.raises(ValueError, match="BOOTSTRAP_KEY"):
        configure_app(Flask(__name__), {"JWT_SECRET_KEY": "s" * 32, "BOOTSTRAP_KEY": key})
