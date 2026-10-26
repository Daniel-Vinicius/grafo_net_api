from typing import Any

from bson import ObjectId
from pymongo.database import Database

from modules.auth.domain.user import User


class MongoUserRepository:
    def __init__(self, database: Database[dict[str, Any]]):
        self._users = database["users"]

    def find_by_email(self, email: str) -> User | None:
        document = self._users.find_one({"email_normalized": email.strip().lower()})
        return self._to_user(document)

    def find_by_id(self, user_id: str) -> User | None:
        identifiers: list[str | ObjectId] = [user_id]
        if ObjectId.is_valid(user_id):
            identifiers.append(ObjectId(user_id))
        document = self._users.find_one({"_id": {"$in": identifiers}})
        return self._to_user(document)

    @staticmethod
    def _to_user(document: dict[str, Any] | None) -> User | None:
        if document is None:
            return None
        return User(
            id=str(document["_id"]),
            email=document["email"],
            password_hash=document["password_hash"],
            is_active=document.get("is_active") is True,
        )
