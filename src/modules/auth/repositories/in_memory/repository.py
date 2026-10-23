from modules.auth.domain.user import User

class InMemoryUserRepository:
    def __init__(self, users: list[User]):
        self._users = users

    def find_by_email(self, email: str) -> User | None:
        for user in self._users:
            if user.email == email:
                return user
        return None

    def find_by_id(self, user_id: str) -> User | None:
        for user in self._users:
            if user.id == user_id:
                return user
        return None
