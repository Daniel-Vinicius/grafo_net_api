from infra.database.memory import MemoryDatabase


class InMemoryTokenRepository:
    def __init__(self, database: MemoryDatabase):
        self.database = database

    def revoke(self, jti, expires_at):
        with self.database.lock:
            self.database.tokens[jti] = expires_at

    def is_revoked(self, jti):
        with self.database.lock:
            return jti in self.database.tokens
