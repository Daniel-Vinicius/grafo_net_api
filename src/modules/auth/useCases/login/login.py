from datetime import datetime

import bcrypt
from modules.auth.repositories.contract import TokenRepository, UserRepository

class AuthUseCase:
    def __init__(self, users: UserRepository, tokens: TokenRepository):
        self._users = users
        self._tokens = tokens

    def authenticate(self, email: str, password: str):
        user = self._users.find_by_email(email)
        if user is None:
            raise ValueError("Usuario ou Senha inválidas")

        try:
            valid_password = bcrypt.checkpw(
                password.encode("utf-8"), user.password_hash.encode("utf-8")
            )
        except ValueError:
            valid_password = False
        if not valid_password:
            raise ValueError("Usuario ou Senha inválidas")

        if not user.is_active:
            raise ValueError("Usuario ou Senha inválidas")
        return user.to_public()

    def logout(self, jti: str, expires_at: datetime) -> None:
        self._tokens.revoke(jti, expires_at)
