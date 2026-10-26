from datetime import datetime, timedelta, timezone
import logging
import secrets
from urllib.parse import urlencode
from uuid import uuid4

from modules.auth.domain.errors import (
    AuthenticationRequiredError, BootstrapForbiddenError, DuplicateEmailError, EmailDeliveryError,
)
from modules.auth.domain.invite import Invite, normalize_email, token_hash
from modules.auth.email import EmailSender
from modules.auth.repositories.contract import InviteRepository, UserRepository


class InviteUseCase:
    def __init__(self, users: UserRepository, invites: InviteRepository, mailer: EmailSender,
                 frontend_url: str, bootstrap_key: str | None = None):
        self._users = users
        self._invites = invites
        self._mailer = mailer
        self._frontend_url = frontend_url.rstrip("/")
        self._bootstrap_key = bootstrap_key

    def issue(self, email: object, sender_id: str | None, bootstrap_key: str | None = None) -> dict:
        if sender_id is None:
            if not self._bootstrap_key or not bootstrap_key or not secrets.compare_digest(
                self._bootstrap_key.encode(), bootstrap_key.encode(),
            ):
                raise AuthenticationRequiredError("Autenticação necessária")
            if self._users.has_any():
                raise BootstrapForbiddenError("Bootstrap indisponível após a primeira conta")
        recipient = normalize_email(email)
        if self._users.find_by_email(recipient) is not None:
            raise DuplicateEmailError()
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        invite = Invite(str(uuid4()), recipient, token_hash(token), sender_id, now, now + timedelta(days=7))
        self._invites.save(invite)
        link = f"{self._frontend_url}/register?{urlencode({'token': token})}"
        try:
            self._mailer.send_invite(recipient, link, invite.expires_at)
        except EmailDeliveryError:
            try:
                self._invites.remove_unused(invite.id)
            except Exception:
                logging.getLogger(__name__).warning("Falha ao remover convite após erro SMTP")
            raise
        return invite.to_public()
