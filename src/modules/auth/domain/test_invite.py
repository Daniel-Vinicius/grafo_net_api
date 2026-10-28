from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from modules.auth.domain.errors import InvalidInviteError, ValidationError
from modules.auth.domain.invite import Invite, normalize_email


@pytest.mark.parametrize(
    "email", ["a@gmail.com", ".a@insper.edu.br", "a..b@insper.edu.br", None]
)
def test_email_rejects_invalid_institutional_address(email):
    with pytest.raises(ValidationError):
        normalize_email(email)


def test_email_normalizes_whitespace_and_case():
    assert normalize_email(" Ana@AL.INSPER.EDU.BR ") == "ana@al.insper.edu.br"


@pytest.fixture
def invitation():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return Invite(
        "invite", "ana@insper.edu.br", "token-hash", None, now, now + timedelta(days=1)
    )


def test_invite_accepts_correct_recipient_before_expiration(invitation):
    invitation.validate_for(invitation.email, invitation.created_at)


@pytest.mark.parametrize("condition", ["expired", "used", "wrong_recipient"])
def test_invite_rejects_unusable_token(invitation, condition):
    now = invitation.created_at
    item = replace(invitation, used_at=now) if condition == "used" else invitation
    if condition == "expired":
        now = invitation.expires_at
    email = "other@insper.edu.br" if condition == "wrong_recipient" else item.email
    with pytest.raises(InvalidInviteError):
        item.validate_for(email, now)


def test_invite_public_data_does_not_expose_token_hash(invitation):
    result = invitation.to_public()
    assert set(result) == {"id", "email", "expires_at"}
    assert invitation.token_hash not in result.values()
