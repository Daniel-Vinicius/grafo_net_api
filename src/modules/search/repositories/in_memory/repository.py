from typing import Any


class InMemoryEmbeddingRepository:
    def __init__(self):
        self.records: dict[str, dict[str, Any]] = {}

    def all(self) -> dict[str, dict[str, Any]]:
        return dict(self.records)

    def save(self, record: dict[str, Any]) -> None:
        self.records[record["_id"]] = dict(record)

