from datetime import datetime
from urllib.parse import parse_qs, urlsplit

import pytest

from modules.auth.domain.errors import (
    AuthenticationRequiredError, BootstrapForbiddenError, DuplicateEmailError, EmailDeliveryError, ValidationError,
)
from modules.auth.domain.invite import token_hash
from modules.auth.domain.user import User
from modules.auth.repositories.in_memory.repository import InMemoryInviteRepository, InMemoryUserRepository
from modules.auth.useCases.invite.invite import InviteUseCase


class RecordingMailer:
    def __init__(self):
        self.messages: list[tuple[str, str, datetime]] = []

    def send_invite(self, email: str, link: str, expires_at: datetime) -> None:
        self.messages.append((email, link, expires_at))


@pytest.fixture
def issuance():
    users = InMemoryUserRepository([])
    invites = InMemoryInviteRepository(users)
    mailer = RecordingMailer()
    service = InviteUseCase(users, invites, mailer, "http://localhost:5173", "b" * 32)
    return service, users, invites, mailer


def test_invite_sends_link_but_stores_only_hash_and_allows_multiple(issuance):
    service, _users, invites, mailer = issuance
    first = service.issue(" Pessoa@AL.INSPER.EDU.BR ", "sender")
    second = service.issue("pessoa@al.insper.edu.br", "sender")
    assert first["id"] != second["id"]
    assert set(first) == {"id", "email", "expires_at"}
    for recipient, link, expiry in mailer.messages:
        token = parse_qs(urlsplit(link).query)["token"][0]
        invite = invites.find_by_hash(token_hash(token))
        assert invite is not None
        assert invite.email == recipient == "pessoa@al.insper.edu.br"
        assert invite.token_hash != token and invite.created_by == "sender"
        assert (expiry - invite.created_at).total_seconds() == 7 * 24 * 60 * 60


@pytest.mark.parametrize("email", [None, "a@example.com", "a@evilinsper.edu.br", "a@insper.edu.br.evil", "a..b@insper.edu.br"])
def test_invite_rejects_invalid_recipient(issuance, email):
    service, _users, _invites, mailer = issuance
    with pytest.raises(ValidationError):
        service.issue(email, "sender")
    assert not mailer.messages


def test_bootstrap_requires_secret_and_empty_users(issuance):
    service, users, _invites, _mailer = issuance
    with pytest.raises(AuthenticationRequiredError):
        service.issue("a@insper.edu.br", None, "wrong")
    service.issue("a@insper.edu.br", None, "b" * 32)
    users._users.append(User("1", "a@insper.edu.br", "hash", True))
    with pytest.raises(BootstrapForbiddenError):
        service.issue("b@insper.edu.br", None, "b" * 32)
    with pytest.raises(DuplicateEmailError):
        service.issue("a@insper.edu.br", "1")


def test_failed_email_removes_only_the_failed_invite(issuance, monkeypatch):
    service, _users, invites, mailer = issuance
    successful = service.issue("a@insper.edu.br", "sender")
    previous = dict(invites._invites)

    def fail(*args):
        raise EmailDeliveryError("SMTP indisponível")

    monkeypatch.setattr(mailer, "send_invite", fail)
    with pytest.raises(EmailDeliveryError):
        service.issue("b@insper.edu.br", "sender")
    assert invites._invites == previous
    assert successful["id"] in invites._invites
