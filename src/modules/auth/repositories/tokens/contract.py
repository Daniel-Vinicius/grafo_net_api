from datetime import datetime
from typing import Protocol


class TokenRepository(Protocol):
    def revoke(self, jti: str, expires_at: datetime) -> None: ...
    def is_revoked(self, jti: str) -> bool: ...
