from dataclasses import replace
from datetime import datetime, timedelta, timezone
from io import BytesIO
from unittest.mock import Mock
import secrets

from flask import Flask
from PIL import Image
import pytest
from pymongo.errors import AutoReconnect

from config import configure_app
from modules.auth.domain.invite import Invite, token_hash
from modules.auth.domain.profile import Profile
from modules.auth.domain.user import User
from modules.auth.email import EmailSender
from modules.auth.passwords import hash_password
from modules.auth.repositories.in_memory.repository import InMemoryUserRepository, InMemoryInviteRepository, InMemoryTokenRepository
from modules.auth.routes.routes import create_auth_routes
from modules.auth.useCases.profile.profile import clean_photos

DATA = {"name": "Pessoa", "course_id": "computer-science", "semester": 2, "field_id": "technology", "bio": "Estudo computação."}
PROJECT = {"title": "Pesquisa", "description": "Uma pesquisa acadêmica", "advisor": "Professora",
           "field_id": "technology", "start_date": "2026-01-01", "end_date": None, "status": "in_progress"}


@pytest.fixture
def environment():
    users = InMemoryUserRepository([])
    invites = InMemoryInviteRepository(users)
    app = Flask(__name__)
    configure_app(app, {"TESTING": True, "JWT_SECRET_KEY": "profile-tests-secret-at-least-32-bytes"})
    app.register_blueprint(create_auth_routes(app, users, InMemoryTokenRepository(), invites, Mock(spec=EmailSender)))
    return app, app.test_client(), users, invites


def signup(environment, email="pessoa@insper.edu.br"):
    app, client, users, invites = environment
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    invite = Invite(secrets.token_hex(8), email, token_hash(token), None, now, now + timedelta(days=1))
    invites.save(invite)
    response = client.post("/api/auth/register", json={"profile": DATA, "email": email,
                                                    "password": "senha1234", "invite_token": token})
    assert response.status_code == 201, response.json
    login = client.post("/api/auth/login", json={"email": email, "password": "senha1234"})
    assert login.status_code == 200
    headers = {"Authorization": "Bearer " + login.json["access_token"]}
    return headers, response.json["id"]


def test_signup_separates_profile_and_user(environment):
    app, client, users, _ = environment
    headers, user_id = signup(environment)
    assert users.find_by_id(user_id).auth_version == 0
    assert not hasattr(users.find_by_id(user_id), "name")
    assert not hasattr(users.find_by_id(user_id), "profile")
    profile = client.get("/api/auth/profile", headers=headers)
    assert profile.status_code == 200
    assert profile.json == {"id": user_id, **DATA, "photo_id": None, "entity_ids": [],
                            "research_project_ids": [], "experiences_completed": False}
    assert "interests" not in profile.json
    assert client.get("/api/auth/profile").status_code == 401
    assert client.get("/api/auth/profiles/" + user_id, headers=headers).status_code == 404
    assert client.get("/api/auth/profile-options").status_code == 200
    assert len(client.get("/api/auth/entities", headers=headers).json) == 11


@pytest.mark.parametrize("data", [{"semester": True}, {"semester": 0}, {"semester": 9},
    {"bio": " "}, {"bio": "a" * 501}, {"course_id": "invalid"}, {"field_id": "invalid"},
    {"id": "another"}, {"email": "x@insper.edu.br"}, {"interests": "x"},
    {"entity_ids": ["missing"]}, {"entity_ids": ["insper-code", "insper-code"]},
    {"research_project_ids": ["missing"]}, {"experiences_completed": 1}])
def test_invalid_profile_changes_preserve_profile(environment, data):
    _, client, _, _ = environment
    headers, _ = signup(environment)
    before = client.get("/api/auth/profile", headers=headers).json
    assert client.patch("/api/auth/profile", headers=headers, json=data).status_code == 400
    assert client.get("/api/auth/profile", headers=headers).json == before


def test_patch_preserves_omitted_fields_and_checks_ownership(environment):
    _, client, _, _ = environment
    first, first_id = signup(environment)
    second, second_id = signup(environment, "outra@insper.edu.br")
    result = client.patch("/api/auth/profile", headers=first, json={"bio": "Nova bio", "entity_ids": ["insper-code"], "experiences_completed": True})
    assert result.status_code == 200
    assert result.json["name"] == DATA["name"]
    assert result.json["id"] == first_id
    assert client.patch("/api/auth/profile", headers=first, json={"id": second_id}).status_code == 400
    assert client.get("/api/auth/profile", headers=second).json["bio"] == DATA["bio"]


def test_research_creation_selection_and_edit_permissions(environment):
    _, client, _, _ = environment
    first, first_id = signup(environment)
    second, _ = signup(environment, "outra@insper.edu.br")
    created = client.post("/api/auth/research-projects", headers=first, json=PROJECT)
    assert created.status_code == 201
    project_id = created.json["id"]
    assert created.json["creator_id"] == first_id
    assert client.get("/api/auth/profile", headers=first).json["research_project_ids"] == [project_id]
    assert client.patch("/api/auth/profile", headers=second, json={"research_project_ids": [project_id]}).status_code == 200
    assert client.patch("/api/auth/research-projects/" + project_id, headers=second, json={"title": "No"}).status_code == 403
    assert client.patch("/api/auth/research-projects/" + project_id, headers=first, json={"title": "Novo"}).json["title"] == "Novo"
    client.patch("/api/auth/profile", headers=first, json={"research_project_ids": []})
    assert client.get("/api/auth/research-projects/" + project_id, headers=second).status_code == 200


@pytest.mark.parametrize("changes", [{"start_date": "x"}, {"end_date": "2025-01-01"},
    {"status": []}, {"title": " "}, {"creator_id": "another"}, {"start_date": "20260101"}])
def test_research_validation_leaves_no_orphans(environment, changes):
    _, client, _, _ = environment
    headers, _ = signup(environment)
    assert client.post("/api/auth/research-projects", headers=headers, json={**PROJECT, **changes}).status_code == 400
    assert client.get("/api/auth/research-projects", headers=headers).json == []
    assert client.get("/api/auth/profile", headers=headers).json["research_project_ids"] == []


@pytest.mark.parametrize("path,payload", [
    ("email", {"new_email": "novo@insper.edu.br"}),
    ("password", {"new_password": "outra-senha"}),
])
def test_credential_changes_invalidate_every_session(environment, path, payload):
    _, client, _, _ = environment
    first, _ = signup(environment)
    second_login = client.post("/api/auth/login", json={"email": "pessoa@insper.edu.br", "password": "senha1234"})
    second = {"Authorization": "Bearer " + second_login.json["access_token"]}
    assert client.patch("/api/auth/account/" + path, headers=first, json={**payload, "current_password": "wrong"}).status_code == 401
    assert client.get("/api/auth/me", headers=first).status_code == 200
    assert client.patch("/api/auth/account/" + path, headers=first, json={**payload, "current_password": "senha1234"}).status_code == 204
    for headers in (first, second):
        assert client.get("/api/auth/me", headers=headers).status_code == 401
    credentials = {"email": payload.get("new_email", "pessoa@insper.edu.br"), "password": payload.get("new_password", "senha1234")}
    assert client.post("/api/auth/login", json=credentials).status_code == 200


def test_email_duplicate_and_validation(environment):
    _, client, _, _ = environment
    first, _ = signup(environment)
    signup(environment, "outra@insper.edu.br")
    for email, status in [("outra@insper.edu.br", 409), ("x@gmail.com", 400), ("pessoa@insper.edu.br", 400)]:
        assert client.patch("/api/auth/account/email", headers=first, json={"current_password": "senha1234", "new_email": email}).status_code == status
    assert client.get("/api/auth/me", headers=first).status_code == 200


def image_bytes(size=(1000, 700), fmt="PNG"):
    output = BytesIO()
    Image.new("RGB", size, "red").save(output, format=fmt)
    return output.getvalue()


def upload(client, headers, content):
    return client.put("/api/auth/profile/photo", headers=headers, data={"photo": (BytesIO(content), "picture.png")})


def test_photo_upload_resize_is_private_replace_remove(environment):
    app, client, _, _ = environment
    first, _ = signup(environment)
    second, _ = signup(environment, "outra@insper.edu.br")
    assert upload(client, first, image_bytes(fmt="JPEG")).status_code == 204
    photo = client.get("/api/auth/profile/photo", headers=first)
    assert photo.status_code == 200 and photo.mimetype == "image/png"
    with Image.open(BytesIO(photo.data)) as image:
        assert image.size == (512, 358)
        assert not image.getexif()
    assert photo.headers["Cache-Control"] == "no-store"
    assert client.get("/api/auth/profile/photo").status_code == 401
    assert client.get("/api/auth/profile/photo", headers=second).status_code == 404
    assert upload(client, first, image_bytes((20, 20))).status_code == 204
    assert len(app.extensions["photo_store"].files) == 1
    assert client.delete("/api/auth/profile/photo", headers=first).status_code == 204
    assert app.extensions["photo_store"].files == {}


@pytest.mark.parametrize("content,status", [(b"not an image", 400), (b"x" * (2 * 1024 * 1024 + 1), 413)])
def test_invalid_photo(environment, content, status):
    _, client, _, _ = environment
    headers, _ = signup(environment)
    response = upload(client, headers, content)
    assert response.status_code == status and response.is_json
    assert client.get("/api/auth/profile", headers=headers).json["photo_id"] is None


def test_photo_rejects_too_many_pixels_and_wrong_format(environment):
    _, client, _, _ = environment
    headers, _ = signup(environment)
    assert upload(client, headers, image_bytes((4001, 4000))).status_code == 400
    assert upload(client, headers, image_bytes(fmt="GIF")).status_code == 400


def test_photo_failed_attachment_cleans_new_file(environment, monkeypatch):
    app, client, _, _ = environment
    headers, _ = signup(environment)
    repository = app.extensions["profile_repository"]
    monkeypatch.setattr(repository, "set_photo", Mock(side_effect=AutoReconnect("fail")))
    assert upload(client, headers, image_bytes()).status_code == 503
    assert app.extensions["photo_store"].files == {}


def test_photo_cleanup_retries_after_storage_failure(environment, monkeypatch):
    app, client, _, _ = environment
    headers, _ = signup(environment)
    upload(client, headers, image_bytes())
    photos = app.extensions["photo_store"]
    repository = app.extensions["profile_repository"]
    with monkeypatch.context() as patch:
        patch.setattr(photos, "delete", Mock(side_effect=OSError("offline")))
        assert client.delete("/api/auth/profile/photo", headers=headers).status_code == 204
    assert repository.pending_photos()
    assert clean_photos(repository, photos) == 1
    assert clean_photos(repository, photos) == 0


def test_delete_preserves_shared_projects_and_invalidates_access(environment):
    app, client, users, invites = environment
    first, first_id = signup(environment)
    second, _ = signup(environment, "outra@insper.edu.br")
    project_id = client.post("/api/auth/research-projects", headers=first, json=PROJECT).json["id"]
    client.patch("/api/auth/profile", headers=second, json={"research_project_ids": [project_id]})
    upload(client, first, image_bytes())
    now = datetime.now(timezone.utc)
    for used in (None, now):
        invite = Invite(secrets.token_hex(8), "convite@insper.edu.br", secrets.token_hex(32), first_id, now, now + timedelta(days=1), used)
        invites.save(invite)
    assert client.delete("/api/auth/account", headers=first, json={"current_password": "wrong"}).status_code == 401
    assert client.delete("/api/auth/account", headers=first, json={"current_password": "senha1234"}).status_code == 204
    assert users.find_by_id(first_id) is None
    assert first_id not in users._profiles
    assert app.extensions["photo_store"].files == {}
    assert client.get("/api/auth/me", headers=first).status_code == 401
    assert client.get("/api/auth/profile", headers=second).json["research_project_ids"] == [project_id]
    assert client.get("/api/auth/research-projects/" + project_id, headers=second).json["creator_id"] is None
    assert client.patch("/api/auth/research-projects/" + project_id, headers=second, json={"title": "x"}).status_code == 403
    assert all(invite.used_at is not None and invite.created_by is None for invite in invites._invites.values() if invite.email == "convite@insper.edu.br")


@pytest.mark.parametrize("changes", [{"bio": ""}, {"semester": 9}, {"semester": True},
    {"course_id": "other"}, {"field_id": "other"}, {"interests": "no"}, {"name": " "}])
def test_registration_invalid_profile_keeps_invite_usable(environment, changes):
    _, client, users, invites = environment
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    invite = Invite("invite", "novo@insper.edu.br", token_hash(token), None, now, now + timedelta(days=1))
    invites.save(invite)
    payload = {"profile": {**DATA, **changes}, "email": invite.email, "password": "senha1234", "invite_token": token}
    assert client.post("/api/auth/register", json=payload).status_code == 400
    assert not users.has_any() and not users._profiles
    assert invites.find_by_hash(invite.token_hash).used_at is None


@pytest.mark.parametrize("method,path", [
    ("get", "/api/auth/profile"), ("patch", "/api/auth/profile"),
    ("get", "/api/auth/entities"), ("get", "/api/auth/research-projects"),
    ("post", "/api/auth/research-projects"), ("patch", "/api/auth/research-projects/other"),
    ("patch", "/api/auth/account/email"), ("patch", "/api/auth/account/password"),
    ("delete", "/api/auth/account"), ("put", "/api/auth/profile/photo"),
    ("get", "/api/auth/profile/photo"), ("delete", "/api/auth/profile/photo"),
])
def test_new_private_endpoints_require_jwt(environment, method, path):
    _, client, _, _ = environment
    response = getattr(client, method)(path)
    assert response.status_code == 401 and response.is_json


def test_login_does_not_upgrade_a_stale_password_check_to_a_new_session_version(environment, monkeypatch):
    app, client, users, _ = environment
    _headers, user_id = signup(environment)
    from flask_jwt_extended import create_access_token
    def change_credentials_before_issuing(*args, **kwargs):
        user = users.find_by_id(user_id)
        app.extensions["profile_repository"].change_credentials(user, {"password_hash": hash_password("changed-password")})
        return create_access_token(*args, **kwargs)
    monkeypatch.setattr("modules.auth.routes.routes.create_access_token", change_credentials_before_issuing)
    login = client.post("/api/auth/login", json={"email": "pessoa@insper.edu.br", "password": "senha1234"})
    assert login.status_code == 200
    token = login.get_json()["access_token"]
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer " + token}).status_code == 401
