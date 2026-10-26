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
from modules.auth.domain.user import Profile, User
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
    user = User(str(uuid4()), email, password_hash, True, Profile("Pessoa"))
    return invite, user


def test_mongo_register_consumes_once_and_rolls_back_duplicate_email(mongo_registration):
    database, repository = mongo_registration
    invite, user = pending_registration(repository)
    repository.register_with_invite(user, invite.token_hash)
    assert repository.find_by_hash(invite.token_hash).used_at is not None
    assert database["users"].find_one({"_id": user.id})["profile"] == {"name": "Pessoa"}
    with pytest.raises(InvalidInviteError):
        repository.register_with_invite(user, invite.token_hash)
    second, duplicate = pending_registration(repository, user.email)
    with pytest.raises(DuplicateEmailError):
        repository.register_with_invite(duplicate, second.token_hash)
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
            repository.register_with_invite(user, invite.token_hash)
    assert repository.find_by_hash(invite.token_hash).used_at is None
    assert database["users"].find_one({"_id": user.id}) is None
    repository.register_with_invite(user, invite.token_hash)
    assert database["users"].find_one({"_id": user.id}) is not None


def test_mongo_concurrent_registration_has_one_winner(mongo_registration):
    database, repository = mongo_registration
    invite, user = pending_registration(repository)
    barrier = Barrier(2)

    def register():
        barrier.wait(timeout=10)
        try:
            repository.register_with_invite(replace(user, id=str(uuid4())), invite.token_hash)
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
        repository.register_with_invite(user, invite.token_hash)
    assert database["users"].find_one({"_id": user.id}) is None
    assert database["invites"].find_one({"_id": invite.id}) == before
