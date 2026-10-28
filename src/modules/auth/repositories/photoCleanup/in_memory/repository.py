from datetime import datetime, timedelta, timezone

from infra.database.memory import MemoryDatabase


class InMemoryPhotoCleanupRepository:
    def __init__(self, database: MemoryDatabase):
        self.database = database

    def queue(self, identifier, delayed=False):
        with self.database.lock:
            self.database.photo_cleanup[identifier] = datetime.now(
                timezone.utc
            ) + timedelta(hours=1 if delayed else 0)

    def pending(self):
        with self.database.lock:
            now = datetime.now(timezone.utc)
            return [
                identifier
                for identifier, ready in self.database.photo_cleanup.items()
                if ready <= now
            ]

    def finish(self, identifier):
        with self.database.lock:
            self.database.photo_cleanup.pop(identifier, None)

    def referenced(self, identifier):
        with self.database.lock:
            return any(
                (
                    profile.photo_id == identifier
                    for profile in self.database.profiles.values()
                )
            )
