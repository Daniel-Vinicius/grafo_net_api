from typing import Any

from pymongo.database import Database

from modules.auth.domain.profile import COURSES, FIELDS
from modules.graph.domain.profile import Catalogs, NetworkProfile


class MongoProfileRepository:
    """Visão de rede dos perfis ativos, sem credenciais nem fotos privadas."""

    def __init__(self, database: Database[dict[str, Any]]):
        self.database = database

    def list_active(self) -> list[NetworkProfile]:
        active_ids = [str(user["_id"]) for user in self.database["users"].find(
            {"is_active": True}, {"_id": 1},
        )]
        fields = ("name", "course_id", "semester", "field_id", "bio", "entity_ids", "research_project_ids")
        profiles = {str(doc["_id"]): doc for doc in self.database["profiles"].find(
            {"_id": {"$in": active_ids}}, {"_id": 1, **dict.fromkeys(fields, 1)},
        )}
        return [self.from_document(profiles.get(identifier, {"_id": identifier})) for identifier in active_ids]

    @staticmethod
    def from_document(document: dict[str, Any]) -> NetworkProfile:
        courses = {item["id"]: item["name"] for item in COURSES}
        fields = {item["id"]: item["name"] for item in FIELDS}
        return NetworkProfile(
            id=str(document["_id"]), name=document.get("name") or "Perfil",
            course=courses.get(document.get("course_id", ""), ""),
            semester=document.get("semester"), field=fields.get(document.get("field_id", ""), ""),
            bio=document.get("bio") or "",
            entity_memberships=tuple({"entity_id": identifier} for identifier in document.get("entity_ids", [])),
            research_participations=tuple({"project_id": identifier} for identifier in document.get("research_project_ids", [])),
        )

    def catalogs(self) -> Catalogs:
        def read(collection: str, fields: tuple[str, ...]) -> dict[str, dict[str, str]]:
            return {str(doc["_id"]): {key: doc.get(key) or "" for key in fields}
                    for doc in self.database[collection].find({}, {"_id": 1, **dict.fromkeys(fields, 1)})}
        return Catalogs(read("entities", ("name", "description")),
                        read("research_projects", ("title", "theme", "description")))
