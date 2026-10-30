import re
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256

from modules.auth.domain.errors import InvalidInviteError, ValidationError


def normalize_email(value: object) -> str:
    if not isinstance(value, str):
        raise ValidationError("E-mail deve ser texto")
    email = value.strip().lower()
    if not re.fullmatch(
        r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@(insper\.edu\.br|al\.insper\.edu\.br)", email
    ):
        raise ValidationError("Informe um e-mail institucional do Insper")
    local = email.split("@")[0]
    if local.startswith(".") or local.endswith(".") or ".." in local:
        raise ValidationError("E-mail inválido")
    return email


def token_hash(token: str) -> str:
    return sha256(token.encode()).hexdigest()


@dataclass(frozen=True)
class Invite:
    id: str
    email: str
    token_hash: str
    created_by: str | None
    created_at: datetime
    expires_at: datetime
    used_at: datetime | None = None

    def validate_for(self, email: str, now: datetime) -> None:
        if self.email != email or self.used_at is not None or self.expires_at <= now:
            raise InvalidInviteError()

    def to_public(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "expires_at": self.expires_at.isoformat(),
        }
