"""Verifica a tradução Mongo/domínio sem exigir servidor externo."""

from unittest.mock import MagicMock

from bson import ObjectId

from modules.auth.repositories.mongo.repository import MongoUserRepository


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
