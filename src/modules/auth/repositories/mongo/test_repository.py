from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import os
import secrets
from threading import Barrier
from unittest.mock import MagicMock
from uuid import uuid4

import bcrypt
from bson import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import OperationFailure
import pytest

from database.setup import preparar_banco
from modules.auth.domain.errors import DuplicateEmailError, InvalidInviteError
from modules.auth.domain.invite import Invite, token_hash
from modules.auth.domain.user import User
from modules.auth.domain.profile import Profile
from modules.auth.repositories.mongo.repository import MongoInviteRepository, MongoUserRepository


def test_mongo_user_mapping_and_normalized_email():
    database = MagicMock()
    identifier = ObjectId()
    database.__getitem__.return_value.find_one.return_value = {
        "_id": identifier, "email": "joao@example.com",
        "password_hash": "bcrypt-hash", "is_active": True,
    }
    repository = MongoUserRepository(database)
    user = repository.find_by_email(" Joao@EXAMPLE.com ")
    database.__getitem__.return_value.find_one.assert_called_once_with({
        "email": "joao@example.com",
    })
    assert user is not None
    assert user.id == str(identifier)
    assert user.password_hash == "bcrypt-hash"
    assert user.is_active
    assert user.to_public() == {"id": str(identifier), "email": "joao@example.com"}


def test_mongo_id_supports_objectid_and_string():
    database = MagicMock()
    database.__getitem__.return_value.find_one.return_value = None
    repository = MongoUserRepository(database)
    identifier = ObjectId()
    assert repository.find_by_id(str(identifier)) is None
    database.__getitem__.return_value.find_one.assert_called_with({
        "_id": {"$in": [str(identifier), identifier]},
    })
    assert repository.find_by_id("custom-id") is None
    database.__getitem__.return_value.find_one.assert_called_with({
        "_id": {"$in": ["custom-id"]},
    })


@pytest.fixture(scope="module")
def mongo_registration():
    load_dotenv()
    uri = os.getenv("MONGO_TEST_URI")
    if not uri:
        pytest.skip("Defina MONGO_TEST_URI para executar os testes de transação")
    client = MongoClient(uri, tz_aware=True, serverSelectionTimeoutMS=5000)
    name = "grafonet_gn06_test_" + uuid4().hex[:16]
    database = client[name]
    try:
        preparar_banco(database)
        yield database, MongoInviteRepository(database)
    finally:
        if database.name == name and name.startswith("grafonet_gn06_test_"):
            client.drop_database(name)
        client.close()


def pending_registration(repository, email=None):
    now = datetime.now(timezone.utc)
    email = email or uuid4().hex + "@insper.edu.br"
    invite = Invite(str(uuid4()), email, token_hash(secrets.token_urlsafe(32)), None, now, now + timedelta(days=7))
    repository.save(invite)
    password_hash = bcrypt.hashpw(b"senha1234", bcrypt.gensalt(rounds=4)).decode()
    user = User(str(uuid4()), email, password_hash, True)
    return invite, user


def test_mongo_register_consumes_once_and_rolls_back_duplicate_email(mongo_registration):
    database, repository = mongo_registration
    invite, user = pending_registration(repository)
    repository.register_with_invite(user, Profile.create(user.id, {"name": "Pessoa", "course_id": "computer-science", "semester": 1, "field_id": "technology", "bio": "Bio de teste"}), invite.token_hash)
    assert repository.find_by_hash(invite.token_hash).used_at is not None
    assert database["profiles"].find_one({"_id": user.id})["name"] == "Pessoa"
    assert "profile" not in database["users"].find_one({"_id": user.id})
    with pytest.raises(InvalidInviteError):
        repository.register_with_invite(user, Profile.create(user.id, {"name": "Pessoa", "course_id": "computer-science", "semester": 1, "field_id": "technology", "bio": "Bio de teste"}), invite.token_hash)
    second, duplicate = pending_registration(repository, user.email)
    with pytest.raises(DuplicateEmailError):
        repository.register_with_invite(duplicate, Profile.create(duplicate.id, {"name": "Pessoa", "course_id": "computer-science", "semester": 1, "field_id": "technology", "bio": "Bio de teste"}), second.token_hash)
    assert repository.find_by_hash(second.token_hash).used_at is None
    assert database["users"].count_documents({"email": user.email}) == 1


def test_mongo_failure_after_claim_keeps_invite_usable(mongo_registration, monkeypatch):
    database, repository = mongo_registration
    invite, user = pending_registration(repository)

    def fail(*args, **kwargs):
        raise OperationFailure("Falha forçada durante a criação")

    with monkeypatch.context() as patch:
        patch.setattr(repository._users, "insert_one", fail)
        with pytest.raises(OperationFailure):
            repository.register_with_invite(user, Profile.create(user.id, {"name": "Pessoa", "course_id": "computer-science", "semester": 1, "field_id": "technology", "bio": "Bio de teste"}), invite.token_hash)
    assert repository.find_by_hash(invite.token_hash).used_at is None
    assert database["users"].find_one({"_id": user.id}) is None
    repository.register_with_invite(user, Profile.create(user.id, {"name": "Pessoa", "course_id": "computer-science", "semester": 1, "field_id": "technology", "bio": "Bio de teste"}), invite.token_hash)
    assert database["users"].find_one({"_id": user.id}) is not None


def test_mongo_concurrent_registration_has_one_winner(mongo_registration):
    database, repository = mongo_registration
    invite, user = pending_registration(repository)
    barrier = Barrier(2)

    def register():
        barrier.wait(timeout=10)
        try:
            repository.register_with_invite(user, Profile.create(user.id, {"name": "Pessoa", "course_id": "computer-science", "semester": 1, "field_id": "technology", "bio": "Bio de teste"}), invite.token_hash)
            return "created"
        except InvalidInviteError:
            return "invalid"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: register(), range(2)))
    assert sorted(results) == ["created", "invalid"]
    assert database["users"].count_documents({"email": user.email}) == 1


@pytest.mark.parametrize("case", ["expired", "used", "different_email"])
def test_mongo_rechecks_invite_conditions(mongo_registration, case):
    database, repository = mongo_registration
    invite, user = pending_registration(repository)
    if case == "expired":
        database["invites"].update_one({"_id": invite.id}, {"$set": {"expires_at": datetime.now(timezone.utc)}})
    elif case == "used":
        database["invites"].update_one({"_id": invite.id}, {"$set": {"used_at": datetime.now(timezone.utc)}})
    else:
        user = replace(user, email="outra-" + user.email)
    before = database["invites"].find_one({"_id": invite.id})
    with pytest.raises(InvalidInviteError):
        repository.register_with_invite(user, Profile.create(user.id, {"name": "Pessoa", "course_id": "computer-science", "semester": 1, "field_id": "technology", "bio": "Bio de teste"}), invite.token_hash)
    assert database["users"].find_one({"_id": user.id}) is None
    assert database["invites"].find_one({"_id": invite.id}) == before


@pytest.mark.parametrize("full", [False, True])
def test_mongo_invitation_friendship_and_full_inviter_rollback(mongo_registration, full):
    from modules.connections.domain.connection import Connection
    from modules.connections.domain.errors import NetworkError
    from modules.connections.repositories.mongo.repository import MongoConnectionRepository

    database, repository = mongo_registration
    sender_invite, sender = pending_registration(repository)
    repository.register_with_invite(sender, Profile.create(sender.id, {"name": "Pessoa", "course_id": "computer-science", "semester": 1, "field_id": "technology", "bio": "Bio de teste"}), sender_invite.token_hash)
    connections = MongoConnectionRepository(database)
    if full:
        for _ in range(10):
            connections.save(Connection.create(sender.id, str(uuid4()), True))
    invite, user = pending_registration(repository)
    invite = replace(invite, created_by=sender.id)
    database["invites"].update_one({"_id": invite.id}, {"$set": {"created_by": sender.id}})
    if full:
        with pytest.raises(NetworkError):
            repository.register_with_invite(user, Profile.create(user.id, {"name": "Pessoa", "course_id": "computer-science", "semester": 1, "field_id": "technology", "bio": "Bio de teste"}), invite.token_hash)
        assert database["users"].find_one({"_id": user.id}) is None
        pending = repository.find_by_hash(invite.token_hash)
        assert pending is not None and pending.used_at is None
    else:
        repository.register_with_invite(user, Profile.create(user.id, {"name": "Pessoa", "course_id": "computer-science", "semester": 1, "field_id": "technology", "bio": "Bio de teste"}), invite.token_hash)
        friendship = connections.find_pair(user.id, sender.id)
        assert friendship is not None and friendship.status == "accepted"


def test_mongo_connection_unique_pair_and_embedding_roundtrip(mongo_registration):
    from modules.connections.domain.connection import Connection
    from modules.connections.domain.errors import NetworkError
    from modules.connections.repositories.mongo.repository import MongoConnectionRepository
    from modules.search.repositories.mongo.repository import MongoEmbeddingRepository

    database, _ = mongo_registration
    connections = MongoConnectionRepository(database)
    first, second = str(uuid4()), str(uuid4())
    connection = Connection.create(first, second)
    connections.save(connection)
    with pytest.raises(NetworkError):
        connections.save(Connection.create(second, first))
    assert len(connections.list_for(first)) == 1
    connections.save(replace(connection, status="accepted", accepted_at=datetime.now(timezone.utc)))
    assert connections.count_accepted(second) == 1
    assert any(item.id == connection.id for item in connections.accepted())
    connections.delete(connection.id)
    assert connections.find(connection.id) is None
    embeddings = MongoEmbeddingRepository(database)
    record = {"_id": first, "vector": [1.0, 0.0], "model": "test", "dimensions": 2,
              "text_version": 1, "source_hash": "hash", "status": "ready"}
    embeddings.save(record)
    assert embeddings.all()[first] == record


def test_real_app_registration_indexing_graph_and_search(mongo_registration):
    from app import create_app
    from modules.search.hooks import profile_saved

    class FakeProvider:
        model = "integration-test"
        dimensions = 2
        queries = 0

        def document(self, text: str, title: str) -> list[float]:
            return [1, 0]

        def query(self, text: str) -> list[float]:
            self.queries += 1
            return [1, 0]

    database, repository = mongo_registration
    sender_invite, sender = pending_registration(repository)
    repository.register_with_invite(sender, Profile.create(sender.id, {"name": "Pessoa", "course_id": "computer-science", "semester": 1, "field_id": "technology", "bio": "Bio de teste"}), sender_invite.token_hash)
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    recipient = uuid4().hex + "@insper.edu.br"
    invite = Invite(str(uuid4()), recipient, token_hash(token), sender.id, now, now + timedelta(days=1))
    repository.save(invite)
    app = create_app({
        "TESTING": True, "MONGO_URI": os.environ["MONGO_TEST_URI"], "MONGO_DB": database.name,
        "JWT_SECRET_KEY": "real-app-test-secret-at-least-32-bytes", "GEMINI_API_KEY": None,
    })
    provider = FakeProvider()
    app.extensions["index_profiles_use_case"].provider = provider
    try:
        client = app.test_client()
        created = client.post("/auth/register", json={
            "profile": {"name": "Pessoa", "course_id": "computer-science", "semester": 1, "field_id": "technology", "bio": "Bio de teste"}, "email": recipient, "password": "senha1234", "invite_token": token,
        })
        assert created.status_code == 201
        assert created.json is not None
        user_id = created.json["id"]
        embedding = database["profile_embeddings"].find_one({"_id": user_id})
        assert embedding is not None and embedding["status"] == "ready"
        login = client.post("/auth/login", json={"email": recipient, "password": "senha1234"})
        assert login.json is not None
        headers = {"Authorization": "Bearer " + login.json["access_token"]}
        graph = client.get("/graph", headers=headers)
        assert graph.json is not None
        assert {node["id"] for node in graph.json["nodes"]} == {sender.id, user_id}
        assert len(graph.json["edges"]) == 1
        sender_login = client.post("/auth/login", json={"email": sender.email, "password": "senha1234"})
        sender_headers = {"Authorization": "Bearer " + sender_login.get_json()["access_token"]}
        edited = client.patch("/auth/profile", headers=sender_headers, json={"bio": "Trabalho com fintechs"})
        assert edited.status_code == 200
        assert database["profiles"].find_one({"_id": sender.id})["bio"] == "Trabalho com fintechs"
        assert database["profile_embeddings"].find_one({"_id": sender.id})["status"] == "ready"
        result = client.post("/search", json={"query": "fintechs"}, headers=headers)
        assert result.json is not None
        assert result.status_code == 200 and result.json["total"] == 1
        assert result.json["results"][0]["profile"]["id"] == sender.id
        assert result.json["results"][0]["cost"] == {"contextual_edges": 0, "hops": 1}
        assert provider.queries == 1
        assert "password_hash" not in result.get_data(as_text=True)
        assert sender.email not in result.get_data(as_text=True)
        research = client.post("/auth/research-projects", headers=sender_headers, json={
            "title": "Pesquisa de dados", "description": "Projeto inicial", "advisor": "Professora",
            "field_id": "technology", "start_date": "2026-01-01", "end_date": None, "status": "planned",
        })
        assert research.status_code == 201
        project_id = research.get_json()["id"]
        assert client.patch("/auth/profile", headers=headers, json={"research_project_ids": [project_id]}).status_code == 200
        before = database["profile_embeddings"].find_one({"_id": user_id})["source_hash"]
        assert client.patch("/auth/research-projects/" + project_id, headers=sender_headers,
                            json={"description": "Nova descrição pesquisável"}).status_code == 200
        assert database["profile_embeddings"].find_one({"_id": user_id})["source_hash"] != before
        assert client.delete("/auth/account", headers=sender_headers, json={"current_password": "senha1234"}).status_code == 204
        assert database["profile_embeddings"].find_one({"_id": sender.id}) is None
        assert database["connections"].count_documents({"$or": [{"user_a_id": sender.id}, {"user_b_id": sender.id}]}) == 0
        assert database["research_projects"].find_one({"_id": project_id})["creator_id"] is None
        assert client.get("/graph", headers=headers).get_json()["edges"] == []
    finally:
        app.extensions["mongo_client"].close()
