from copy import deepcopy

from infra.database.memory import MemoryDatabase


class InMemoryEntityRepository:
    def __init__(self, database: MemoryDatabase):
        self.database = database

    def list(self):
        with self.database.lock:
            return sorted(
                deepcopy(list(self.database.entities.values())),
                key=lambda item: item["name"],
            )

    def get_many(self, identifiers):
        with self.database.lock:
            return {
                key: deepcopy(self.database.entities[key])
                for key in identifiers
                if key in self.database.entities
            }

    def add_if_absent(self, entity):
        with self.database.lock:
            self.database.entities.setdefault(entity["id"], deepcopy(entity))
