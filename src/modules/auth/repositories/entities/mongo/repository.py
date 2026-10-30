from infra.database.documents import attributes
from infra.database.mongo import mongo_errors


class MongoEntityRepository:
    def __init__(self, database, session=None):
        self.database = database
        self.session = session

    def list(self):
        with mongo_errors(self.session):
            return [
                attributes(value)
                for value in self.database.entities.find(session=self.session).sort(
                    "name", 1
                )
            ]

    def get_many(self, identifiers):
        with mongo_errors(self.session):
            return {
                str(value["_id"]): attributes(value)
                for value in self.database.entities.find(
                    {"_id": {"$in": list(identifiers)}}, session=self.session
                )
            }

    def add_if_absent(self, entity):
        with mongo_errors(self.session):
            self.database.entities.update_one(
                {"_id": entity["id"]},
                {"$setOnInsert": {"name": entity["name"]}},
                upsert=True,
                session=self.session,
            )
