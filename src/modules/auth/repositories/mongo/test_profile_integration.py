"""Integração real, somente em banco temporário criado por este teste."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from io import BytesIO
import os
import secrets
from unittest.mock import Mock
from uuid import uuid4

from flask import Flask
from PIL import Image
from pymongo import MongoClient
from pymongo.errors import OperationFailure
import pytest

from config import configure_app
from database.setup import preparar_banco
from modules.auth.domain.invite import Invite, token_hash
from modules.auth.domain.profile import Profile, ResearchProject
from modules.auth.domain.user import User
from modules.auth.email import EmailSender
from modules.auth.passwords import hash_password
from modules.auth.repositories.mongo.repository import MongoInviteRepository, MongoUserRepository, MongoTokenRepository
from modules.auth.repositories.mongo.profiles import MongoProfileRepository, MongoPhotoStore
from modules.auth.routes.routes import create_auth_routes
from modules.auth.useCases.profile.profile import ProfileUseCase, clean_photos

PROFILE = {"name": "Pessoa", "course_id": "law", "semester": 1, "field_id": "technology", "bio": "Minha bio"}
PROJECT = {"title": "Pesquisa", "description": "Descrição", "advisor": "Professor", "field_id": "technology", "start_date": "2026-01-01", "end_date": None, "status": "planned"}


@pytest.fixture(scope="module")
def database():
    uri = os.getenv("MONGO_TEST_URI")
    if not uri:
        pytest.skip("Defina MONGO_TEST_URI para os testes de integração")
    client = MongoClient(uri, tz_aware=True, serverSelectionTimeoutMS=5000)
    name = "grafonet_profile_test_" + uuid4().hex
    db = client[name]
    try:
        preparar_banco(db)
        yield db
    finally:
        client.drop_database(name)
        client.close()


def create_user(db):
    users, invites = MongoUserRepository(db), MongoInviteRepository(db)
    user = User(str(uuid4()), uuid4().hex + "@insper.edu.br", hash_password("senha1234"), True)
    now = datetime.now(timezone.utc)
    invite = Invite(str(uuid4()), user.email, token_hash(secrets.token_urlsafe(32)), None, now, now + timedelta(days=1))
    invites.save(invite)
    profile = Profile.create(user.id, PROFILE)
    invites.register_with_invite(user, profile, invite.token_hash)
    return user, profile, invites


def test_profile_insert_failure_rolls_back_user_and_invite(database, monkeypatch):
    user, _profile, invites = create_user(database)
    duplicate = replace(user, id=str(uuid4()), email=uuid4().hex + "@insper.edu.br")
    now = datetime.now(timezone.utc)
    invite = Invite(str(uuid4()), duplicate.email, secrets.token_hex(32), None, now, now + timedelta(days=1))
    invites.save(invite)
    with monkeypatch.context() as patch:
        patch.setattr(invites._profiles, "insert_one", Mock(side_effect=OperationFailure("forced profile failure")))
        with pytest.raises(OperationFailure):
            invites.register_with_invite(duplicate, Profile.create(duplicate.id, PROFILE), invite.token_hash)
    assert database.users.find_one({"_id": duplicate.id}) is None
    assert database.profiles.find_one({"_id": duplicate.id}) is None
    saved_invite = invites.find_by_hash(invite.token_hash)
    assert saved_invite is not None and saved_invite.used_at is None


def test_project_profile_transaction_rollback(database, monkeypatch):
    user, profile, _ = create_user(database)
    repository = MongoProfileRepository(database)
    project = ResearchProject.create(user.id, PROJECT)
    # Fazer falhar o insert após o update do perfil precisa desfazer ambos.
    from pymongo.synchronous.collection import Collection
    original = Collection.insert_one
    def fail_project(self, *args, **kwargs):
        if self.name == "research_projects":
            raise OperationFailure("forced project failure")
        return original(self, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(Collection, "insert_one", fail_project)
        with pytest.raises(OperationFailure):
            repository.create_project(user.id, project)
    assert repository.get_profile(user.id) == profile
    assert repository.get_project(project.id) is None


def test_delete_transaction_failure_preserves_account(database, monkeypatch):
    user, profile, _ = create_user(database)
    repository = MongoProfileRepository(database)
    from pymongo.synchronous.collection import Collection
    original = Collection.update_many
    def fail_project(self, *args, **kwargs):
        if self.name == "research_projects":
            raise OperationFailure("forced deletion failure")
        return original(self, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(Collection, "update_many", fail_project)
        with pytest.raises(OperationFailure):
            repository.delete_account(user)
    assert MongoUserRepository(database).find_by_id(user.id) == user
    assert repository.get_profile(user.id) == profile


def test_mongo_full_http_flow_with_photo_credentials_and_delete(database):
    user, _profile, invites = create_user(database)
    app = Flask(__name__)
    configure_app(app, {"TESTING": True, "JWT_SECRET_KEY": "integration-test-secret-at-least-32-bytes"})
    repository, photos = MongoProfileRepository(database), MongoPhotoStore(database)
    app.register_blueprint(create_auth_routes(app, MongoUserRepository(database), MongoTokenRepository(database), invites, Mock(spec=EmailSender), repository, photos))
    client = app.test_client()
    def login(password="senha1234"):
        result = client.post("/api/auth/login", json={"email": user.email, "password": password})
        assert result.status_code == 200
        return {"Authorization": "Bearer " + result.get_json()["access_token"]}
    headers = login()
    assert client.patch("/api/auth/profile", headers=headers, json={"bio": "Bio atualizada", "entity_ids": ["insper-code"], "experiences_completed": True}).status_code == 200
    created = client.post("/api/auth/research-projects", headers=headers, json=PROJECT)
    assert created.status_code == 201
    project_id = created.get_json()["id"]
    assert project_id in client.get("/api/auth/profile", headers=headers).get_json()["research_project_ids"]
    image = BytesIO()
    Image.new("RGB", (600, 600), "blue").save(image, format="PNG")
    image.seek(0)
    assert client.put("/api/auth/profile/photo", headers=headers, data={"photo": (image, "photo.png")}).status_code == 204
    saved_profile = repository.get_profile(user.id)
    assert saved_profile is not None and saved_profile.photo_id is not None
    old_photo_id = saved_profile.photo_id
    assert client.get("/api/auth/profile/photo", headers=headers).status_code == 200
    assert client.patch("/api/auth/account/password", headers=headers, json={"current_password": "senha1234", "new_password": "nova-senha"}).status_code == 204
    assert client.get("/api/auth/profile", headers=headers).status_code == 401
    headers = login("nova-senha")
    assert client.delete("/api/auth/account", headers=headers, json={"current_password": "nova-senha"}).status_code == 204
    assert MongoUserRepository(database).find_by_id(user.id) is None
    assert repository.get_profile(user.id) is None
    saved_project = repository.get_project(project_id)
    assert saved_project is not None and saved_project.creator_id is None
    assert photos.get(old_photo_id) is None
    assert clean_photos(repository, photos) == 0
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_profile_schema_and_unique_id(database):
    user, profile, _ = create_user(database)
    with pytest.raises(OperationFailure):
        database.profiles.update_one({"_id": user.id}, {"$set": {"semester": 9}})
    assert MongoProfileRepository(database).get_profile(user.id) == profile


def test_explicit_reset_preserves_unrelated_collections_and_reseeds(database):
    from database.setup import reset_test_data
    database.connections.insert_one({"_id": "must-remain"})
    database.entities.insert_one({"_id": "test-entity", "name": "Test Entity"})
    reset_test_data(database)
    assert database.connections.find_one({"_id": "must-remain"}) is not None
    for name in ("users", "profiles", "invites", "revoked_tokens", "entities", "research_projects", "photo_cleanup", "profile_photos.files", "profile_photos.chunks"):
        assert database[name].count_documents({}) == 0
    preparar_banco(database)
    preparar_banco(database)
    assert database.entities.count_documents({}) == 11
