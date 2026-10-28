from copy import deepcopy

from infra.database.memory import MemoryDatabase


class InMemoryEmbeddingRepository:
    def __init__(self, database: MemoryDatabase):
        self.database = database

    def get_many(self, identifiers):
        with self.database.lock:
            return {
                identifier: deepcopy(self.database.embeddings[identifier])
                for identifier in identifiers
                if identifier in self.database.embeddings
            }

    def save(self, record):
        with self.database.lock:
            self.database.embeddings[record["_id"]] = deepcopy(record)

    def delete(self, identifier):
        with self.database.lock:
            self.database.embeddings.pop(identifier, None)
