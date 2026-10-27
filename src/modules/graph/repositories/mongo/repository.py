from typing import Any

from pymongo.database import Database

from modules.graph.domain.profile import Catalogs, NetworkProfile


class MongoProfileRepository:
    def __init__(self, database: Database[dict[str, Any]]):
        self.database = database

    def list_active(self) -> list[NetworkProfile]:
        fields = tuple(NetworkProfile.__dataclass_fields__)
        projection = {"_id": 1, **{f"profile.{key}": 1 for key in fields if key != "id"}}
        return [self.from_document(doc) for doc in self.database["users"].find(
            {"is_active": True}, projection
        )]

    @staticmethod
    def from_document(document: dict[str, Any]) -> NetworkProfile:
        profile = document.get("profile") or {}
        text_fields = ("type", "course", "class_group", "bio", "role", "company", "photo_url")
        return NetworkProfile(
            id=str(document["_id"]), name=profile.get("name") or "Perfil",
            **{key: profile.get(key) or "" for key in text_fields},
            entry_year=profile.get("entry_year"), entry_semester=profile.get("entry_semester"),
            interests=tuple(profile.get("interests") or ()),
            experiences=tuple(profile.get("experiences") or ()),
            entity_memberships=tuple(profile.get("entity_memberships") or ()),
            research_participations=tuple(profile.get("research_participations") or ()),
        )

    def catalogs(self) -> Catalogs:
        def read(collection: str, fields: tuple[str, ...]) -> dict[str, dict[str, str]]:
            return {str(doc["_id"]): {key: doc.get(key) or "" for key in fields}
                    for doc in self.database[collection].find({}, {"_id": 1, **dict.fromkeys(fields, 1)})}
        return Catalogs(read("entities", ("name", "description")),
                        read("research_projects", ("title", "theme", "description")))

