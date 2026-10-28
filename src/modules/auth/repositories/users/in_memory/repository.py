from infra.database.contract import DuplicateRecordError
from infra.database.memory import MemoryDatabase


class InMemoryUserRepository:
    def __init__(self, database: MemoryDatabase):
        self.database = database

    def get(self, identifier):
        with self.database.lock:
            return self.database.users.get(identifier)

    def find_email(self, email):
        with self.database.lock:
            normalized = email.strip().lower()
            return next(
                (
                    user
                    for user in self.database.users.values()
                    if user.email == normalized
                ),
                None,
            )

    def list_active(self):
        with self.database.lock:
            return [user for user in self.database.users.values() if user.is_active]

    def has_any(self):
        with self.database.lock:
            return bool(self.database.users)

    def save(self, user, insert=False):
        with self.database.lock:
            if insert and user.id in self.database.users:
                raise DuplicateRecordError("Usuário já existe")
            existing = self.find_email(user.email)
            if existing and existing.id != user.id:
                raise DuplicateRecordError("E-mail já cadastrado")
            self.database.users[user.id] = user

    def delete(self, identifier):
        with self.database.lock:
            self.database.users.pop(identifier, None)

    def lock_network(self, identifiers):
        """A transação in-memory já serializa as operações com um lock global."""
        with self.database.lock:
            return None
