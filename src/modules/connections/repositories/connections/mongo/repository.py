from infra.database.documents import attributes, document
from infra.database.mongo import mongo_errors
from modules.connections.domain.connection import Connection


class MongoConnectionRepository:
    def __init__(self, database, session=None):
        self.database = database
        self.session = session

    def get(self, identifier):
        with mongo_errors(self.session):
            value = self.database.connections.find_one(
                {"_id": identifier}, session=self.session
            )
        return Connection(**attributes(value)) if value else None

    def find_pair(self, first, second):
        a, b = sorted((first, second))
        with mongo_errors(self.session):
            value = self.database.connections.find_one(
                {"user_a_id": a, "user_b_id": b}, session=self.session
            )
        return Connection(**attributes(value)) if value else None

    def list_for(self, identifier):
        with mongo_errors(self.session):
            return [
                Connection(**attributes(value))
                for value in self.database.connections.find(
                    {"$or": [{"user_a_id": identifier}, {"user_b_id": identifier}]},
                    session=self.session,
                ).sort("_id", 1)
            ]

    def accepted(self):
        with mongo_errors(self.session):
            return [
                Connection(**attributes(value))
                for value in self.database.connections.find(
                    {"status": "accepted"}, session=self.session
                )
            ]

    def count_accepted(self, identifier):
        with mongo_errors(self.session):
            return self.database.connections.count_documents(
                {
                    "$or": [{"user_a_id": identifier}, {"user_b_id": identifier}],
                    "status": "accepted",
                },
                session=self.session,
            )

    def save(self, connection, insert=False):
        with mongo_errors(self.session):
            if insert:
                self.database.connections.insert_one(
                    document(connection), session=self.session
                )
            else:
                self.database.connections.replace_one(
                    {"_id": connection.id},
                    document(connection),
                    upsert=True,
                    session=self.session,
                )

    def delete(self, identifier):
        with mongo_errors(self.session):
            self.database.connections.delete_one(
                {"_id": identifier}, session=self.session
            )

    def accept_pending(self, connection):
        with mongo_errors(self.session):
            result = self.database.connections.replace_one(
                {"_id": connection.id, "status": "pending"},
                document(connection),
                upsert=False,
                session=self.session,
            )
        return result.matched_count == 1
