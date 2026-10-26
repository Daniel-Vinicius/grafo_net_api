from datetime import datetime

from modules.auth.passwords import check_password
from modules.auth.repositories.contract import TokenRepository, UserRepository

class AuthUseCase:
    def __init__(self, users: UserRepository, tokens: TokenRepository):
        self._users = users
        self._tokens = tokens

    def authenticate(self, email: str, password: str):
        user = self._users.find_by_email(email)
        if user is None:
            raise ValueError("Usuario ou Senha inválidas")

        valid_password = check_password(password, user.password_hash)
        if not valid_password:
            raise ValueError("Usuario ou Senha inválidas")

        if not user.is_active:
            raise ValueError("Usuario ou Senha inválidas")
        return user.to_public()

    def logout(self, jti: str, expires_at: datetime) -> None:
        self._tokens.revoke(jti, expires_at)
