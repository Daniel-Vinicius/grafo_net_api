from datetime import datetime
from typing import Protocol

from infra.errors import UnavailableError


class EmailDeliveryError(UnavailableError):
    pass


class EmailSender(Protocol):
    def send_invite(self, email: str, link: str, expires_at: datetime) -> None: ...
