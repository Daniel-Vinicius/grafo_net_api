from infra.database.contract import DuplicateRecordError
from infra.database.memory import MemoryDatabase


class InMemoryPasswordResetRepository:
    def __init__(self, database: MemoryDatabase):
        self.database = database

    def get_hash(self, token_hash):
        with self.database.lock:
            return next(
                (
                    reset
                    for reset in self.database.password_resets.values()
                    if reset.token_hash == token_hash
                ),
                None,
            )

    def latest_for_user(self, user_id):
        with self.database.lock:
            items = [
                reset
                for reset in self.database.password_resets.values()
                if reset.user_id == user_id
            ]
            return max(items, key=lambda item: item.created_at, default=None)

    def save(self, reset):
        with self.database.lock:
            existing = self.get_hash(reset.token_hash)
            if existing and existing.id != reset.id:
                raise DuplicateRecordError("Token de recuperação duplicado")
            self.database.password_resets[reset.id] = reset

    def delete(self, identifier):
        with self.database.lock:
            self.database.password_resets.pop(identifier, None)

    def delete_for_user(self, user_id):
        with self.database.lock:
            for identifier in [
                key
                for key, reset in self.database.password_resets.items()
                if reset.user_id == user_id
            ]:
                self.database.password_resets.pop(identifier, None)
