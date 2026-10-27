from dataclasses import fields as dataclass_fields
import logging
from typing import Any

from pymongo.database import Database

from modules.auth.domain.errors import ValidationError
from modules.auth.domain.profile import Profile
from modules.auth.repositories.mongo.profiles import profile_from_document
from modules.graph.domain.catalogs import Catalogs


logger = logging.getLogger(__name__)


class MongoProfileRepository:
    """Read canonical profiles of active users; serializers enforce public exposure."""

    def __init__(self, database: Database[dict[str, Any]]):
        self.database = database

    def list_active(self) -> list[Profile]:
        active_ids = [str(user["_id"]) for user in self.database["users"].find(
            {"is_active": True}, {"_id": 1},
        )]
        fields = [item.name for item in dataclass_fields(Profile) if item.name != "id"]
        documents = {str(doc["_id"]): doc for doc in self.database["profiles"].find(
            {"_id": {"$in": active_ids}}, {"_id": 1, **dict.fromkeys(fields, 1)},
        )}
        profiles = []
        for identifier in active_ids:
            document = documents.get(identifier)
            if document is None:
                logger.warning("Active user %s has no profile; excluded from graph/search", identifier)
                continue
            try:
                profile = profile_from_document(document)
            except (TypeError, ValueError, ValidationError):
                logger.warning("Invalid profile for active user %s; excluded from graph/search", identifier)
                continue
            if profile is not None:
                profiles.append(profile)
        return profiles

    def catalogs(self) -> Catalogs:
        def read(collection: str, fields: tuple[str, ...]) -> dict[str, dict[str, str]]:
            return {str(doc["_id"]): {key: doc.get(key) or "" for key in fields}
                    for doc in self.database[collection].find({}, {"_id": 1, **dict.fromkeys(fields, 1)})}
        return Catalogs(read("entities", ("name", "description")),
                        read("research_projects", ("title", "theme", "description")))
