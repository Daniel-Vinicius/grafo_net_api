"""Verifica a tradução Mongo/domínio sem exigir servidor externo."""

from typing import Any
from unittest.mock import MagicMock

from bson import ObjectId
from pymongo import MongoClient

from app import create_app
from modules.auth.repositories.mongo.repository import MongoUserRepository


def test_mongo_user_mapping_and_normalized_email():
    database = MagicMock()
    identifier = ObjectId()
    database.__getitem__.return_value.find_one.return_value = {
        "_id": identifier, "email": "Joao@example.com", "email_normalized": "joao@example.com",
        "password_hash": "bcrypt-hash", "is_active": True,
    }
    repository = MongoUserRepository(database)
    user = repository.find_by_email(" Joao@EXAMPLE.com ")
    database.__getitem__.return_value.find_one.assert_called_once_with({
        "email_normalized": "joao@example.com",
    })
    assert user is not None
    assert user.id == str(identifier)
    assert user.password_hash == "bcrypt-hash"
    assert user.is_active
    assert user.to_public() == {"id": str(identifier), "email": "Joao@example.com"}


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


def test_normal_app_registers_auth_with_mongo(monkeypatch):
    client: MongoClient[dict[str, Any]] = MongoClient("mongodb://localhost:27017", connect=False)
    calls = []

    def database_factory(uri, name):
        calls.append((uri, name))
        return client["test"]

    monkeypatch.setattr("app.create_database", database_factory)
    try:
        application = create_app({
            "JWT_SECRET_KEY": "application-test-secret-at-least-32-bytes",
            "MONGO_URI": "mongodb://localhost:27017", "MONGO_DB": "test",
        })
        assert calls == [("mongodb://localhost:27017", "test")]
        assert isinstance(application.extensions["user_repository"], MongoUserRepository)
        assert application.extensions["mongo_client"] is client
        assert application.test_client().get("/api/auth/me").status_code == 401
        assert {"/api/auth/login", "/api/auth/me", "/api/auth/logout"} <= {
            rule.rule for rule in application.url_map.iter_rules()
        }
    finally:
        client.close()
