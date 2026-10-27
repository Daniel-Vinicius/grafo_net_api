from modules.connections.domain.connection import Connection
from modules.connections.domain.errors import NetworkError


class InMemoryConnectionRepository:
    def __init__(self):
        self.records: dict[str, Connection] = {}

    def find(self, connection_id: str) -> Connection | None:
        return self.records.get(connection_id)

    def find_pair(self, first: str, second: str) -> Connection | None:
        a, b = sorted((first, second))
        return next((c for c in self.records.values() if (c.user_a_id, c.user_b_id) == (a, b)), None)

    def list_for(self, user_id: str) -> list[Connection]:
        return [c for c in self.records.values() if user_id in (c.user_a_id, c.user_b_id)]

    def accepted(self) -> list[Connection]:
        return [c for c in self.records.values() if c.status == "accepted"]

    def count_accepted(self, user_id: str) -> int:
        return sum(c.status == "accepted" for c in self.list_for(user_id))

    def save(self, connection: Connection) -> None:
        existing = self.find_pair(connection.user_a_id, connection.user_b_id)
        if existing and existing.id != connection.id:
            raise NetworkError("Já existe uma conexão ou solicitação entre essas pessoas", 409)
        self.records[connection.id] = connection

    def delete(self, connection_id: str) -> None:
        self.records.pop(connection_id, None)
