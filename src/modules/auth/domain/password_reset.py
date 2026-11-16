from dataclasses import dataclass
from datetime import datetime

from modules.auth.domain.errors import InvalidPasswordResetError


@dataclass(frozen=True)
class PasswordReset:
    id: str
    user_id: str
    token_hash: str
    created_at: datetime
    expires_at: datetime

    def validate(self, now: datetime) -> None:
        if self.expires_at <= now:
            raise InvalidPasswordResetError()
