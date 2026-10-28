from infra.database.contract import DuplicateRecordError
from infra.database.memory import MemoryDatabase


class InMemoryInviteRepository:
    def __init__(self, database: MemoryDatabase):
        self.database = database

    def get_hash(self, token_hash):
        with self.database.lock:
            return next(
                (
                    invite
                    for invite in self.database.invites.values()
                    if invite.token_hash == token_hash
                ),
                None,
            )

    def save(self, invite):
        with self.database.lock:
            existing = self.get_hash(invite.token_hash)
            if existing and existing.id != invite.id:
                raise DuplicateRecordError("Token de convite duplicado")
            self.database.invites[invite.id] = invite

    def delete(self, identifier):
        with self.database.lock:
            self.database.invites.pop(identifier, None)

    def by_creator(self, identifier):
        with self.database.lock:
            return [
                invite
                for invite in self.database.invites.values()
                if invite.created_by == identifier
            ]
