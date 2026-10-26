from dataclasses import replace
from datetime import datetime, timedelta, timezone
import secrets

import pytest

from modules.auth.domain.errors import DuplicateEmailError, InvalidInviteError, ValidationError
from modules.auth.domain.invite import Invite, token_hash
from modules.auth.domain.user import User
from modules.auth.repositories.in_memory.repository import InMemoryInviteRepository, InMemoryUserRepository
from modules.auth.useCases.register.register import RegisterUseCase


@pytest.fixture
def registration():
    users = InMemoryUserRepository([])
    invites = InMemoryInviteRepository(users)
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    invite = Invite("invite", "pessoa@insper.edu.br", token_hash(token), None, now, now + timedelta(days=7))
    invites.save(invite)
    return RegisterUseCase(users, invites), users, invites, invite, token


@pytest.mark.parametrize("case", ["expired", "used", "different_email", "missing", "boundary"])
def test_register_rejects_invalid_invite_without_creating_account(registration, case):
    service, users, invites, invite, token = registration
    email = invite.email
    if case in ("expired", "boundary"):
        invite = replace(invite, expires_at=datetime.now(timezone.utc) - timedelta(seconds=case == "expired"))
    elif case == "used":
        invite = replace(invite, used_at=datetime.now(timezone.utc))
    elif case == "different_email":
        email = "outra@insper.edu.br"
    else:
        token = secrets.token_urlsafe(32)
    invites.save(invite)
    with pytest.raises(InvalidInviteError):
        service.register("Pessoa", email, "senha1234", token)
    assert not users.has_any()
    assert invites.find_by_hash(invite.token_hash) == invite


@pytest.mark.parametrize("name,password", [(" ", "senha1234"), ("x" * 101, "senha1234"),
    ("Pessoa", "curta"), ("Pessoa", "á" * 37), (None, "senha1234"), ("Pessoa", 12345678)])
def test_register_validates_name_and_password_before_consuming(registration, name, password):
    service, users, invites, invite, token = registration
    with pytest.raises(ValidationError):
        service.register(name, invite.email, password, token)
    assert not users.has_any()
    assert invites.find_by_hash(invite.token_hash) == invite


def test_existing_email_does_not_consume_invite(registration):
    service, users, invites, invite, token = registration
    users._users.append(User("existing", invite.email, "hash", True))
    with pytest.raises(DuplicateEmailError):
        service.register("Pessoa", invite.email, "senha1234", token)
    assert invites.find_by_hash(invite.token_hash) == invite


def test_repository_rechecks_invite_after_password_hash(registration, monkeypatch):
    service, users, invites, invite, token = registration

    def hash_and_consume(password):
        invites.save(replace(invite, used_at=datetime.now(timezone.utc)))
        return "hash"

    monkeypatch.setattr("modules.auth.useCases.register.register.hash_password", hash_and_consume)
    with pytest.raises(InvalidInviteError):
        service.register("Pessoa", invite.email, "senha1234", token)
    assert not users.has_any()
