from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Any

from gridfs import GridFSBucket, NoFile
from pymongo import ReturnDocument
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError
from pymongo.write_concern import WriteConcern

from modules.auth.domain.errors import AuthenticationRequiredError, DuplicateEmailError, ForbiddenError, NotFoundError, ValidationError
from modules.auth.domain.profile import Profile, ResearchProject
from modules.auth.domain.user import User


def document(value: Profile | ResearchProject) -> dict:
    result = asdict(value)
    result["_id"] = result.pop("id")
    return result


def profile_from_document(value: dict | None) -> Profile | None:
    if value is None:
        return None
    data = dict(value)
    data["id"] = str(data.pop("_id"))
    return Profile(**data)


def project_from_document(value: dict | None) -> ResearchProject | None:
    if value is None:
        return None
    data = dict(value)
    data["id"] = str(data.pop("_id"))
    return ResearchProject(**data)


class MongoProfileRepository:
    def __init__(self, database: Database[dict[str, Any]]):
        self._db = database

    def _transaction(self, callback):
        with self._db.client.start_session() as session:
            return session.with_transaction(callback, write_concern=WriteConcern("majority"))

    def get_profile(self, user_id: str) -> Profile | None:
        return profile_from_document(self._db.profiles.find_one({"_id": user_id}))

    def patch_profile(self, user_id: str, changes: dict) -> Profile:
        def update(session):
            for field, collection in [("entity_ids", "entities"), ("research_project_ids", "research_projects")]:
                ids = changes.get(field, [])
                if self._db[collection].count_documents({"_id": {"$in": ids}}, session=session) != len(ids):
                    raise ValidationError("Experiência inexistente")
            result = self._db.profiles.find_one_and_update(
                {"_id": user_id}, {"$set": changes}, return_document=ReturnDocument.AFTER, session=session,
            ) if changes else self._db.profiles.find_one({"_id": user_id}, session=session)
            profile = profile_from_document(result)
            if profile is None:
                raise NotFoundError("Perfil não encontrado")
            return profile
        return self._transaction(update)

    def list_entities(self) -> list[dict]:
        return [{"id": str(item["_id"]), "name": item["name"]} for item in self._db.entities.find().sort("name", 1)]

    def list_projects(self) -> list[ResearchProject]:
        return [ResearchProject(id=str(item["_id"]), **{k: v for k, v in item.items() if k != "_id"})
                for item in self._db.research_projects.find().sort([("title", 1), ("_id", 1)])]

    def get_project(self, project_id: str) -> ResearchProject | None:
        return project_from_document(self._db.research_projects.find_one({"_id": project_id}))

    def create_project(self, user_id: str, project: ResearchProject) -> None:
        def create(session):
            if self._db.users.find_one({"_id": user_id}, session=session) is None:
                raise NotFoundError("Usuário não encontrado")
            result = self._db.profiles.update_one(
                {"_id": user_id}, {"$addToSet": {"research_project_ids": project.id}}, session=session,
            )
            if result.matched_count != 1:
                raise NotFoundError("Perfil não encontrado")
            self._db.research_projects.insert_one(document(project), session=session)
        self._transaction(create)

    def update_project(self, user_id: str, project: ResearchProject) -> None:
        result = self._db.research_projects.replace_one(
            {"_id": project.id, "creator_id": user_id}, document(project),
        )
        if not result.matched_count:
            if self.get_project(project.id) is None:
                raise NotFoundError("Pesquisa não encontrada")
            raise ForbiddenError("Somente o criador pode editar a pesquisa")

    @staticmethod
    def _credentials_filter(user: User) -> dict:
        return {"_id": user.id, "auth_version": user.auth_version, "password_hash": user.password_hash}

    def change_credentials(self, user: User, changes: dict) -> None:
        try:
            result = self._db.users.update_one(self._credentials_filter(user), {
                "$set": changes, "$inc": {"auth_version": 1},
            })
        except DuplicateKeyError:
            raise DuplicateEmailError() from None
        if not result.matched_count:
            raise AuthenticationRequiredError("Credenciais alteradas; entre novamente")

    def delete_account(self, user: User) -> None:
        def delete(session):
            result = self._db.users.delete_one(self._credentials_filter(user), session=session)
            if not result.deleted_count:
                raise AuthenticationRequiredError("Credenciais alteradas; entre novamente")
            profile = self._db.profiles.find_one_and_delete({"_id": user.id}, session=session)
            if profile and profile.get("photo_id"):
                self._db.photo_cleanup.update_one({"_id": profile["photo_id"]}, {
                    "$set": {"ready_at": datetime.now(timezone.utc)},
                }, upsert=True, session=session)
            self._db.profile_embeddings.delete_one({"_id": user.id}, session=session)
            self._db.connections.delete_many({"$or": [{"user_a_id": user.id}, {"user_b_id": user.id}]}, session=session)
            self._db.research_projects.update_many({"creator_id": user.id}, {"$set": {"creator_id": None}}, session=session)
            self._db.invites.delete_many({"created_by": user.id, "used_at": None}, session=session)
            self._db.invites.update_many({"created_by": user.id}, {"$set": {"created_by": None}}, session=session)
        self._transaction(delete)

    def set_photo(self, user_id: str, photo_id: str | None) -> None:
        def update(session):
            previous = self._db.profiles.find_one_and_update(
                {"_id": user_id}, {"$set": {"photo_id": photo_id}}, session=session,
            )
            if previous is None:
                raise NotFoundError("Perfil não encontrado")
            if previous.get("photo_id"):
                self._db.photo_cleanup.update_one({"_id": previous["photo_id"]}, {
                    "$set": {"ready_at": datetime.now(timezone.utc)},
                }, upsert=True, session=session)
            if photo_id:
                self._db.photo_cleanup.delete_one({"_id": photo_id}, session=session)
        self._transaction(update)

    def queue_photo(self, photo_id: str, delayed: bool = False) -> None:
        self._db.photo_cleanup.update_one({"_id": photo_id}, {
            "$set": {"ready_at": datetime.now(timezone.utc) + timedelta(hours=1 if delayed else 0)},
        }, upsert=True)

    def pending_photos(self) -> list[str]:
        return [item["_id"] for item in self._db.photo_cleanup.find({"ready_at": {"$lte": datetime.now(timezone.utc)}})]

    def finish_photo_cleanup(self, photo_id: str) -> None:
        self._db.photo_cleanup.delete_one({"_id": photo_id})

    def photo_referenced(self, photo_id: str) -> bool:
        return self._db.profiles.find_one({"photo_id": photo_id}, {"_id": 1}) is not None


class MongoPhotoStore:
    def __init__(self, database: Database[dict[str, Any]]):
        self._bucket = GridFSBucket(database, bucket_name="profile_photos")

    def put(self, photo_id: str, content: bytes) -> None:
        self._bucket.upload_from_stream_with_id(photo_id, "profile.png", content, metadata={"content_type": "image/png"})

    def get(self, photo_id: str) -> bytes | None:
        try:
            return self._bucket.open_download_stream(photo_id).read()
        except NoFile:
            return None

    def delete(self, photo_id: str) -> None:
        try:
            self._bucket.delete(photo_id)
        except NoFile:
            pass
