from infra.database.contract import DuplicateRecordError
from infra.database.memory import MemoryDatabase


class InMemoryConnectionRepository:
    def __init__(self, database: MemoryDatabase):
        self.database = database

    def get(self, identifier):
        with self.database.lock:
            return self.database.connections.get(identifier)

    def find_pair(self, first, second):
        with self.database.lock:
            a, b = sorted((first, second))
            return next(
                (
                    item
                    for item in self.database.connections.values()
                    if (item.user_a_id, item.user_b_id) == (a, b)
                ),
                None,
            )

    def list_for(self, identifier):
        with self.database.lock:
            return sorted(
                (
                    item
                    for item in self.database.connections.values()
                    if identifier in (item.user_a_id, item.user_b_id)
                ),
                key=lambda item: item.id,
            )

    def accepted(self):
        with self.database.lock:
            return [
                item
                for item in self.database.connections.values()
                if item.status == "accepted"
            ]

    def count_accepted(self, identifier):
        with self.database.lock:
            return sum(
                (item.status == "accepted" for item in self.list_for(identifier))
            )

    def save(self, connection, insert=False):
        with self.database.lock:
            if insert and connection.id in self.database.connections:
                raise DuplicateRecordError("Conexão já existe")
            existing = self.find_pair(connection.user_a_id, connection.user_b_id)
            if existing and existing.id != connection.id:
                raise DuplicateRecordError("Conexão duplicada")
            self.database.connections[connection.id] = connection

    def delete(self, identifier):
        with self.database.lock:
            self.database.connections.pop(identifier, None)

    def accept_pending(self, connection):
        with self.database.lock:
            previous = self.get(connection.id)
            if previous is None or previous.status != "pending":
                return False
            self.save(connection)
            return True
