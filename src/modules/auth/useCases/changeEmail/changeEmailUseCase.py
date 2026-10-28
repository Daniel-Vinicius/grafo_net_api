from dataclasses import replace

from infra.database.contract import DuplicateRecordError, UnitOfWork
from infra.security.passwords.contract import PasswordHasher
from modules.auth.domain.errors import DuplicateEmailError, ValidationError
from modules.auth.domain.invite import normalize_email
from modules.auth.policies import current_user


class ChangeEmailUseCase:
    def __init__(self, uow: UnitOfWork, hasher: PasswordHasher):
        self.uow = uow
        self.hasher = hasher

    def execute(self, user, data):
        if set(data) != {"current_password", "new_email"}:
            raise ValidationError("Campos de credenciais inválidos")

        def change(repos):
            current_user(repos, user, data["current_password"], self.hasher)
            email = normalize_email(data["new_email"])
            if email == user.email:
                raise ValidationError("Informe outro e-mail")
            other = repos.users.find_email(email)
            if other and other.id != user.id:
                raise DuplicateEmailError()
            updated = replace(user, email=email, auth_version=user.auth_version + 1)
            repos.users.save(updated)

        try:
            self.uow.run(change)
        except DuplicateRecordError:
            raise DuplicateEmailError() from None
