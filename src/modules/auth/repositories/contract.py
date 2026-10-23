from typing import Protocol
from modules.auth.domain.user import User

class UserRepository(Protocol):
    def find_by_email(self, email: str) -> User | None:
        ...

    def find_by_id(self, user_id: str) -> User | None:
        ...
