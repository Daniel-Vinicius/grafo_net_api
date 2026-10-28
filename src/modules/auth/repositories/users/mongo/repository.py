from dataclasses import asdict

from infra.database.mongo import mongo_errors
from modules.auth.domain.user import User


class MongoUserRepository:
    def __init__(self, database, session=None):
        self.database = database
        self.session = session

    @staticmethod
    def _map(value):
        if value is None:
            return None
        return User(
            str(value["_id"]),
            value["email"],
            value["password_hash"],
            value["is_active"],
            value.get("auth_version", 0),
        )

    def get(self, identifier):
        with mongo_errors(self.session):
            return self._map(
                self.database.users.find_one({"_id": identifier}, session=self.session)
            )

    def find_email(self, email):
        with mongo_errors(self.session):
            return self._map(
                self.database.users.find_one(
                    {"email": email.strip().lower()}, session=self.session
                )
            )

    def list_active(self):
        with mongo_errors(self.session):
            return [
                user
                for value in self.database.users.find(
                    {"is_active": True}, session=self.session
                )
                if (user := self._map(value)) is not None
            ]

    def has_any(self):
        with mongo_errors(self.session):
            return (
                self.database.users.find_one({}, {"_id": 1}, session=self.session)
                is not None
            )

    def save(self, user, insert=False):
        values = asdict(user)
        identifier = values.pop("id")
        with mongo_errors(self.session):
            if insert:
                self.database.users.insert_one(
                    {"_id": identifier, **values, "network_version": 0},
                    session=self.session,
                )
            else:
                self.database.users.update_one(
                    {"_id": identifier},
                    {"$set": values, "$setOnInsert": {"network_version": 0}},
                    upsert=True,
                    session=self.session,
                )

    def delete(self, identifier):
        with mongo_errors(self.session):
            self.database.users.delete_one({"_id": identifier}, session=self.session)

    def lock_network(self, identifiers):
        with mongo_errors(self.session):
            for identifier in sorted(set(identifiers)):
                self.database.users.update_one(
                    {"_id": identifier},
                    {"$inc": {"network_version": 1}},
                    session=self.session,
                )
