import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from uuid import uuid4

from infra.database.contract import UnitOfWork
from infra.email.contract import EmailDeliveryError, EmailSender
from infra.errors import UnavailableError
from modules.auth.domain.errors import (
    AuthenticationRequiredError,
    BootstrapForbiddenError,
    DuplicateEmailError,
)
from modules.auth.domain.invite import Invite, normalize_email, token_hash


class IssueInvitationUseCase:
    def __init__(
        self, uow: UnitOfWork, mailer: EmailSender, frontend: str, bootstrap: str | None
    ):
        self.uow = uow
        self.mailer = mailer
        self.frontend = frontend
        self.bootstrap = bootstrap

    def execute(self, email, sender_id=None, bootstrap_key=None):
        recipient = normalize_email(email)
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        invite = Invite(
            str(uuid4()),
            recipient,
            token_hash(token),
            sender_id,
            now,
            now + timedelta(days=7),
        )

        def issue(repos):
            if sender_id is None:
                if (
                    not self.bootstrap
                    or not bootstrap_key
                    or not isinstance(bootstrap_key, str)
                    or not secrets.compare_digest(
                        self.bootstrap.encode(), bootstrap_key.encode()
                    )
                ):
                    raise AuthenticationRequiredError("Autenticação necessária")
                if repos.users.has_any():
                    raise BootstrapForbiddenError(
                        "Bootstrap indisponível após a primeira conta"
                    )
            else:
                sender = repos.users.get(sender_id)
                if sender is None or not sender.is_active:
                    raise AuthenticationRequiredError("Usuário inativo")
            if repos.users.find_email(recipient):
                raise DuplicateEmailError()
            repos.invites.save(invite)

        self.uow.run(issue)
        try:
            self.mailer.send_invite(
                recipient,
                f"{self.frontend.rstrip('/')}/register?{urlencode({'token': token})}",
                invite.expires_at,
            )
        except EmailDeliveryError:

            def discard(repos):
                saved = repos.invites.get_hash(invite.token_hash)
                if saved and saved.used_at is None:
                    repos.invites.delete(saved.id)

            try:
                self.uow.run(discard)
            except UnavailableError:
                pass
            raise
        return invite.to_public()
