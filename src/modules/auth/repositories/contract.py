from datetime import datetime
from typing import Protocol
from modules.auth.domain.user import User

class UserRepository(Protocol):
    def find_by_email(self, email: str) -> User | None:
        ...

    def find_by_id(self, user_id: str) -> User | None:
        ...


class TokenRepository(Protocol):
    def revoke(self, jti: str, expires_at: datetime) -> None:
        ...

    def is_revoked(self, jti: str) -> bool:
        ...
