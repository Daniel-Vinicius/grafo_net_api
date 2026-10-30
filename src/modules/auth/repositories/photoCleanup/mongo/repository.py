from datetime import datetime, timedelta, timezone

from infra.database.mongo import mongo_errors


class MongoPhotoCleanupRepository:
    def __init__(self, database, session=None):
        self.database = database
        self.session = session

    def queue(self, identifier, delayed=False):
        ready = datetime.now(timezone.utc) + timedelta(hours=1 if delayed else 0)
        with mongo_errors(self.session):
            self.database.photo_cleanup.update_one(
                {"_id": identifier},
                {"$set": {"ready_at": ready}},
                upsert=True,
                session=self.session,
            )

    def pending(self):
        with mongo_errors(self.session):
            return [
                value["_id"]
                for value in self.database.photo_cleanup.find(
                    {"ready_at": {"$lte": datetime.now(timezone.utc)}},
                    {"_id": 1},
                    session=self.session,
                )
            ]

    def finish(self, identifier):
        with mongo_errors(self.session):
            self.database.photo_cleanup.delete_one(
                {"_id": identifier}, session=self.session
            )

    def referenced(self, identifier):
        with mongo_errors(self.session):
            return (
                self.database.profiles.find_one(
                    {"photo_id": identifier}, {"_id": 1}, session=self.session
                )
                is not None
            )
