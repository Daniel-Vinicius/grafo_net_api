from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo.client_session import ClientSession
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError
from pymongo.write_concern import WriteConcern

from modules.auth.domain.errors import DuplicateEmailError, InvalidInviteError
from modules.auth.domain.invite import Invite
from modules.auth.domain.user import Profile, User


class MongoUserRepository:
    def __init__(self, database: Database[dict[str, Any]]):
        self._users = database["users"]

    def find_by_email(self, email: str) -> User | None:
        document = self._users.find_one({"email": email.strip().lower()})
        return self._to_user(document)

    def find_by_id(self, user_id: str) -> User | None:
        identifiers: list[str | ObjectId] = [user_id]
        if ObjectId.is_valid(user_id):
            identifiers.append(ObjectId(user_id))
        document = self._users.find_one({"_id": {"$in": identifiers}})
        return self._to_user(document)

    def has_any(self) -> bool:
        return self._users.find_one({}, {"_id": 1}) is not None

    @staticmethod
    def _to_user(document: dict[str, Any] | None) -> User | None:
        if document is None:
            return None
        return User(
            id=str(document["_id"]),
            email=document["email"],
            password_hash=document["password_hash"],
            is_active=document.get("is_active") is True,
            profile=Profile(document["profile"]["name"]) if document.get("profile") else None,
        )


class MongoTokenRepository:
    def __init__(self, database: Database[dict[str, Any]]):
        self._tokens = database["revoked_tokens"]

    def revoke(self, jti: str, expires_at: datetime) -> None:
        self._tokens.update_one(
            {"_id": jti}, {"$set": {"expires_at": expires_at}}, upsert=True,
        )

    def is_revoked(self, jti: str) -> bool:
        return self._tokens.find_one({"_id": jti}, {"_id": 1}) is not None


class MongoInviteRepository:
    def __init__(self, database: Database[dict[str, Any]]):
        self._database = database
        self._invites = database["invites"]
        self._users = database["users"]

    def save(self, invite: Invite) -> None:
        document = asdict(invite)
        document["_id"] = document.pop("id")
        self._invites.insert_one(document)

    def find_by_hash(self, token_hash: str) -> Invite | None:
        document = self._invites.find_one({"token_hash": token_hash})
        if document is None:
            return None
        return Invite(
            id=str(document["_id"]), email=document["email"], token_hash=document["token_hash"],
            created_by=document["created_by"], created_at=document["created_at"],
            expires_at=document["expires_at"], used_at=document["used_at"],
        )

    def remove_unused(self, invite_id: str) -> None:
        self._invites.delete_one({"_id": invite_id, "used_at": None})

    def register_with_invite(self, user: User, token_hash: str) -> None:
        def register(session: ClientSession) -> None:
            now = datetime.now(timezone.utc)
            invite = self._invites.find_one_and_update(
                {"token_hash": token_hash, "email": user.email, "used_at": None,
                 "expires_at": {"$gt": now}},
                {"$set": {"used_at": now}}, session=session,
            )
            if invite is None:
                raise InvalidInviteError()
            document = asdict(user)
            document["_id"] = document.pop("id")
            self._users.insert_one(document, session=session)

        try:
            with self._database.client.start_session() as session:
                session.with_transaction(register, write_concern=WriteConcern("majority"))
        except DuplicateKeyError:
            raise DuplicateEmailError() from None
