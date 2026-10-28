from infra.database.contract import DuplicateRecordError
from infra.database.memory import MemoryDatabase


class InMemoryPhotoRepository:
    def __init__(self, database: MemoryDatabase):
        self.database = database

    def put(self, identifier, content):
        with self.database.lock:
            if identifier in self.database.photos:
                raise DuplicateRecordError("Foto já existe")
            self.database.photos[identifier] = content

    def get(self, identifier):
        with self.database.lock:
            return self.database.photos.get(identifier)

    def delete(self, identifier):
        with self.database.lock:
            self.database.photos.pop(identifier, None)
