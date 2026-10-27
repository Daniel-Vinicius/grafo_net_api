from typing import Any

from pymongo.database import Database


class MongoEmbeddingRepository:
    def __init__(self, database: Database[dict[str, Any]]):
        self.collection = database["profile_embeddings"]

    def all(self) -> dict[str, dict[str, Any]]:
        return {str(doc["_id"]): doc for doc in self.collection.find({})}

    def save(self, record: dict[str, Any]) -> None:
        self.collection.replace_one({"_id": record["_id"]}, record, upsert=True)

