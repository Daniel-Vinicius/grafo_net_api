from infra.database.context import Repositories
from infra.security.passwords.contract import PasswordHasher
from modules.auth.domain.errors import AuthenticationRequiredError, ValidationError


class LoginUseCase:
    def __init__(self, repos: Repositories, hasher: PasswordHasher):
        self.repos = repos
        self.hasher = hasher

    def execute(self, email, password):
        if (
            not isinstance(email, str)
            or not email.strip()
            or not isinstance(password, str)
            or not password
        ):
            raise ValidationError("Informe e-mail e senha")
        user = self.repos.users.find_email(email)
        if (
            user is None
            or not user.is_active
            or not self.hasher.verify(password, user.password_hash)
        ):
            raise AuthenticationRequiredError("Usuário ou senha inválidos")
        return user
