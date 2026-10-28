from infra.database.contract import DuplicateRecordError
from infra.database.memory import MemoryDatabase


class InMemoryProfileRepository:
    def __init__(self, database: MemoryDatabase):
        self.database = database

    def get(self, identifier):
        with self.database.lock:
            return self.database.profiles.get(identifier)

    def save(self, profile, insert=False):
        with self.database.lock:
            if insert and profile.id in self.database.profiles:
                raise DuplicateRecordError("Perfil já existe")
            self.database.profiles[profile.id] = profile

    def delete(self, identifier):
        with self.database.lock:
            self.database.profiles.pop(identifier, None)

    def by_advisor(self, identifier):
        with self.database.lock:
            return [
                profile
                for profile in self.database.profiles.values()
                if any(
                    (
                        item.advisor_user_id == identifier
                        for item in profile.research_participations
                    )
                )
            ]
