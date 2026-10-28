from dataclasses import replace

from infra.database.contract import DuplicateRecordError, UnitOfWork
from infra.security.passwords.contract import PasswordHasher
from modules.auth.domain.errors import DuplicateEmailError, ValidationError
from modules.auth.policies import current_user, password_input


class ChangePasswordUseCase:
    def __init__(self, uow: UnitOfWork, hasher: PasswordHasher):
        self.uow = uow
        self.hasher = hasher

    def execute(self, user, data):
        if set(data) != {"current_password", "new_password"}:
            raise ValidationError("Campos de credenciais inválidos")

        def change(repos):
            current_user(repos, user, data["current_password"], self.hasher)
            password = password_input(data["new_password"])
            if self.hasher.verify(password, user.password_hash):
                raise ValidationError("Informe outra senha")
            updated = replace(
                user,
                password_hash=self.hasher.hash(password),
                auth_version=user.auth_version + 1,
            )
            repos.users.save(updated)

        try:
            self.uow.run(change)
        except DuplicateRecordError:
            raise DuplicateEmailError() from None
