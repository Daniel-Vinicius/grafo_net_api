from datetime import datetime

from modules.auth.domain.user import User

class InMemoryUserRepository:
    def __init__(self, users: list[User]):
        self._users = users

    def find_by_email(self, email: str) -> User | None:
        for user in self._users:
            if user.email.strip().lower() == email.strip().lower():
                return user
        return None

    def find_by_id(self, user_id: str) -> User | None:
        for user in self._users:
            if user.id == user_id:
                return user
        return None


class InMemoryTokenRepository:
    def __init__(self):
        self._tokens: dict[str, datetime] = {}

    def revoke(self, jti: str, expires_at: datetime) -> None:
        self._tokens[jti] = expires_at

    def is_revoked(self, jti: str) -> bool:
        return jti in self._tokens
