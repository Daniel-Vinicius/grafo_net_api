from dataclasses import replace
from datetime import datetime, timezone
from threading import RLock

from modules.auth.domain.errors import DuplicateEmailError, InvalidInviteError
from modules.auth.domain.invite import Invite
from modules.auth.domain.user import User
from modules.auth.domain.profile import Profile


class InMemoryUserRepository:
    def __init__(self, users: list[User]):
        self._users = users
        self._lock = RLock()
        self._profiles: dict[str, Profile] = {}

    def find_by_email(self, email: str) -> User | None:
        with self._lock:
            return next((user for user in self._users if user.email.strip().lower() == email.strip().lower()), None)

    def find_by_id(self, user_id: str) -> User | None:
        with self._lock:
            return next((user for user in self._users if user.id == user_id), None)

    def has_any(self) -> bool:
        with self._lock:
            return bool(self._users)


class InMemoryTokenRepository:
    def __init__(self):
        self._tokens: dict[str, datetime] = {}

    def revoke(self, jti: str, expires_at: datetime) -> None:
        self._tokens[jti] = expires_at

    def is_revoked(self, jti: str) -> bool:
        return jti in self._tokens


class InMemoryInviteRepository:
    def __init__(self, users: InMemoryUserRepository):
        self._users = users
        self._invites: dict[str, Invite] = {}

    def save(self, invite: Invite) -> None:
        with self._users._lock:
            self._invites[invite.id] = invite

    def find_by_hash(self, token_hash: str) -> Invite | None:
        with self._users._lock:
            return next((invite for invite in self._invites.values() if invite.token_hash == token_hash), None)

    def remove_unused(self, invite_id: str) -> None:
        with self._users._lock:
            invite = self._invites.get(invite_id)
            if invite is not None and invite.used_at is None:
                del self._invites[invite_id]

    def register_with_invite(self, user: User, profile: Profile, token_hash: str) -> None:
        with self._users._lock:
            invite = self.find_by_hash(token_hash)
            if invite is None:
                raise InvalidInviteError()
            now = datetime.now(timezone.utc)
            invite.validate_for(user.email, now)
            if self._users.find_by_email(user.email) is not None:
                raise DuplicateEmailError()
            consumed = replace(invite, used_at=now)
            if profile.id != user.id or user.id in self._users._profiles:
                raise ValueError("Perfil incompatível")
            self._users._profiles[user.id] = profile
            self._users._users.append(user)
            self._invites[invite.id] = consumed
