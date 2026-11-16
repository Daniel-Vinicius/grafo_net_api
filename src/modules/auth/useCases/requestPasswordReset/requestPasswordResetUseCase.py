import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from uuid import uuid4

from infra.database.contract import UnitOfWork
from infra.email.contract import EmailDeliveryError, EmailSender
from infra.errors import UnavailableError
from modules.auth.domain.invite import normalize_email, token_hash
from modules.auth.domain.password_reset import PasswordReset


class RequestPasswordResetUseCase:
    def __init__(self, uow: UnitOfWork, mailer: EmailSender, frontend: str):
        self.uow = uow
        self.mailer = mailer
        self.frontend = frontend

    def execute(self, email):
        recipient = normalize_email(email)
        now = datetime.now(timezone.utc)
        token = secrets.token_urlsafe(32)
        reset = None

        def issue(repos):
            nonlocal reset
            user = repos.users.find_email(recipient)
            if user is None or not user.is_active:
                return
            latest = repos.password_resets.latest_for_user(user.id)
            if latest and latest.created_at > now - timedelta(seconds=60):
                return
            repos.password_resets.delete_for_user(user.id)
            reset = PasswordReset(
                str(uuid4()),
                user.id,
                token_hash(token),
                now,
                now + timedelta(minutes=30),
            )
            repos.password_resets.save(reset)

        self.uow.run(issue)
        if reset is None:
            return
        issued = reset
        try:
            self.mailer.send_password_reset(
                recipient,
                f"{self.frontend.rstrip('/')}/reset-password?{urlencode({'token': token})}",
                issued.expires_at,
            )
        except EmailDeliveryError:

            def discard(repos):
                saved = repos.password_resets.get_hash(issued.token_hash)
                if saved:
                    repos.password_resets.delete(saved.id)

            try:
                self.uow.run(discard)
            except UnavailableError:
                pass
            raise
