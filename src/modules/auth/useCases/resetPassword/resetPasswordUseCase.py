import re
from dataclasses import replace
from datetime import datetime, timezone

from infra.database.contract import UnitOfWork
from infra.security.passwords.contract import PasswordHasher
from modules.auth.domain.errors import InvalidPasswordResetError, ValidationError
from modules.auth.domain.invite import token_hash
from modules.auth.policies import password_input


class ResetPasswordUseCase:
    def __init__(self, uow: UnitOfWork, hasher: PasswordHasher):
        self.uow = uow
        self.hasher = hasher

    def execute(self, data):
        if set(data) != {"token", "new_password"}:
            raise ValidationError("Campos de recuperação inválidos")
        token = data["token"]
        if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
            raise InvalidPasswordResetError()
        password = password_input(data["new_password"])

        def reset_password(repos):
            reset = repos.password_resets.get_hash(token_hash(token))
            if reset is None:
                raise InvalidPasswordResetError()
            reset.validate(datetime.now(timezone.utc))
            user = repos.users.get(reset.user_id)
            if user is None or not user.is_active:
                raise InvalidPasswordResetError()
            if self.hasher.verify(password, user.password_hash):
                raise ValidationError("Informe outra senha")
            repos.users.save(
                replace(
                    user,
                    password_hash=self.hasher.hash(password),
                    auth_version=user.auth_version + 1,
                )
            )
            repos.password_resets.delete_for_user(user.id)

        self.uow.run(reset_password)
