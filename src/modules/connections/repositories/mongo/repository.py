from dataclasses import asdict
from typing import Any

from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from modules.connections.domain.connection import Connection
from modules.connections.domain.errors import NetworkError


def connection_document(connection: Connection) -> dict[str, Any]:
    doc = asdict(connection)
    doc["_id"] = doc.pop("id")
    return doc


class MongoConnectionRepository:
    def __init__(self, database: Database[dict[str, Any]]):
        self.collection = database["connections"]

    @staticmethod
    def _map(doc: dict[str, Any] | None) -> Connection | None:
        if doc is None:
            return None
        return Connection(str(doc["_id"]), doc["user_a_id"], doc["user_b_id"],
                          doc["requested_by"], doc["status"], doc["created_at"], doc.get("accepted_at"))

    def find(self, connection_id: str) -> Connection | None:
        return self._map(self.collection.find_one({"_id": connection_id}))

    def find_pair(self, first: str, second: str) -> Connection | None:
        a, b = sorted((first, second))
        return self._map(self.collection.find_one({"user_a_id": a, "user_b_id": b}))

    def list_for(self, user_id: str) -> list[Connection]:
        return [item for doc in self.collection.find(self._participant(user_id))
                if (item := self._map(doc)) is not None]

    def accepted(self) -> list[Connection]:
        return [item for doc in self.collection.find({"status": "accepted"})
                if (item := self._map(doc)) is not None]

    @staticmethod
    def _participant(user_id: str) -> dict:
        return {"$or": [{"user_a_id": user_id}, {"user_b_id": user_id}]}

    def count_accepted(self, user_id: str) -> int:
        return self.collection.count_documents({**self._participant(user_id), "status": "accepted"})

    def save(self, connection: Connection) -> None:
        try:
            self.collection.replace_one({"_id": connection.id}, connection_document(connection), upsert=True)
        except DuplicateKeyError:
            raise NetworkError("Já existe uma conexão ou solicitação entre essas pessoas", 409) from None

    def delete(self, connection_id: str) -> None:
        self.collection.delete_one({"_id": connection_id})
