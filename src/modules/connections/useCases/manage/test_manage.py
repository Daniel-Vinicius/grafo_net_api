from dataclasses import replace
from datetime import datetime, timedelta, timezone
import secrets

import pytest

from modules.auth.domain.invite import Invite, token_hash
from modules.auth.domain.user import User
from modules.auth.repositories.in_memory.repository import InMemoryInviteRepository, InMemoryUserRepository
from modules.auth.useCases.register.register import RegisterUseCase
from modules.connections.domain.connection import Connection
from modules.connections.domain.errors import NetworkError
from modules.connections.repositories.in_memory.repository import InMemoryConnectionRepository
from modules.connections.useCases.manage.manage import ConnectionUseCase


@pytest.fixture
def setup():
    users = InMemoryUserRepository([User(key, f"{key}@insper.edu.br", "hash", True) for key in ("a", "b", "c")])
    repository = InMemoryConnectionRepository()
    return users, repository, ConnectionUseCase(repository, users)


def test_connection_lifecycle_permissions_and_duplicate_pair(setup):
    users, repository, service = setup
    pending = service.request("a", "b")
    with pytest.raises(NetworkError):
        service.request("b", "a")
    for actor in ("a", "c"):
        with pytest.raises(NetworkError) as error:
            service.accept(actor, pending.id)
        assert error.value.status == 403
    with pytest.raises(NetworkError):
        service.remove("c", pending.id)
    accepted = service.accept("b", pending.id)
    assert accepted.status == "accepted" and accepted.accepted_at
    assert repository.count_accepted("a") == repository.count_accepted("b") == 1
    service.remove("a", pending.id)
    assert repository.count_accepted("b") == 0
    # Recusa e cancelamento permitem nova solicitação.
    pending = service.request("b", "a")
    service.remove("a", pending.id)
    pending = service.request("b", "a")
    service.remove("b", pending.id)
    assert not repository.list_for("a")


@pytest.mark.parametrize("target", ["a", "missing", None, "", 4])
def test_invalid_connection_targets(setup, target):
    _, _, service = setup
    with pytest.raises(NetworkError):
        service.request("a", target)


def test_inactive_target_and_both_sides_limit(setup):
    users, repository, service = setup
    users._users[1] = replace(users._users[1], is_active=False)
    with pytest.raises(NetworkError):
        service.request("a", "b")
    users._users[1] = replace(users._users[1], is_active=True)
    for full in ("a", "b"):
        repository.records.clear()
        for i in range(10):
            repository.save(Connection.create(full, f"friend-{i}", True))
        pending = service.request("a", "b")
        with pytest.raises(NetworkError) as error:
            service.accept("b", pending.id)
        assert error.value.status == 409
        assert repository.find(pending.id).status == "pending"


def invited_registration(users, repository, sender: str | None = "a"):
    invites = InMemoryInviteRepository(users, repository)
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    invite = Invite("invite", "new@insper.edu.br", token_hash(token), sender, now, now + timedelta(days=1))
    invites.save(invite)
    return RegisterUseCase(users, invites), invites, invite, token


def test_invitation_creates_accepted_friendship_and_bootstrap_does_not(setup):
    users, repository, _ = setup
    service, invites, invite, token = invited_registration(users, repository)
    result = service.register("Nova", invite.email, "senha1234", token)
    friendship = repository.find_pair("a", result["id"])
    assert friendship and friendship.status == "accepted"
    consumed = invites.find_by_hash(invite.token_hash)
    assert consumed is not None and consumed.used_at
    fresh = InMemoryUserRepository([])
    repository = InMemoryConnectionRepository()
    service, invites, invite, token = invited_registration(fresh, repository, None)
    service.register("Primeira", invite.email, "senha1234", token)
    assert repository.accepted() == []


@pytest.mark.parametrize("reason", ["full", "inactive", "deleted"])
def test_unavailable_inviter_preserves_invite_and_does_not_create_user(setup, reason):
    users, repository, _ = setup
    service, invites, invite, token = invited_registration(users, repository)
    if reason == "full":
        for i in range(10):
            repository.save(Connection.create("a", f"friend-{i}", True))
    elif reason == "inactive":
        users._users[0] = replace(users._users[0], is_active=False)
    else:
        users._users.pop(0)
    with pytest.raises(NetworkError):
        service.register("Nova", invite.email, "senha1234", token)
    assert users.find_by_email(invite.email) is None
    pending = invites.find_by_hash(invite.token_hash)
    assert pending is not None and pending.used_at is None
