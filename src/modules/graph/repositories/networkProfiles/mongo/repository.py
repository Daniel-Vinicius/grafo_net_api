import logging

from infra.database.documents import attributes
from infra.database.mongo import mongo_errors
from modules.auth.domain.profile import Profile
from modules.graph.domain.catalogs import Catalogs


class MongoNetworkProfileRepository:
    def __init__(self, database, session=None):
        self.database = database
        self.session = session

    @staticmethod
    def _profiles(documents):
        result = []
        for value in documents:
            try:
                result.append(Profile.from_dict(attributes(value)))
            except TypeError, ValueError:
                logging.getLogger(__name__).warning(
                    "Perfil inválido excluído da rede: %s", value["_id"]
                )
        return result

    def list_active(self):
        with mongo_errors(self.session):
            identifiers = [
                user["_id"]
                for user in self.database.users.find(
                    {"is_active": True}, {"_id": 1}, session=self.session
                )
            ]
            return self._profiles(
                self.database.profiles.find(
                    {"_id": {"$in": identifiers}}, session=self.session
                )
            )

    def get_active(self, identifier):
        with mongo_errors(self.session):
            user = self.database.users.find_one(
                {"_id": identifier, "is_active": True}, {"_id": 1}, session=self.session
            )
            value = (
                self.database.profiles.find_one(
                    {"_id": identifier}, session=self.session
                )
                if user
                else None
            )
            result = self._profiles([value]) if value else []
        return result[0] if result else None

    def by_reference(self, kind, identifier):
        field = "entity_ids" if kind == "entity" else "research_project_ids"
        with mongo_errors(self.session):
            documents = list(
                self.database.profiles.find({field: identifier}, session=self.session)
            )
            active = {
                user["_id"]
                for user in self.database.users.find(
                    {
                        "_id": {"$in": [value["_id"] for value in documents]},
                        "is_active": True,
                    },
                    {"_id": 1},
                    session=self.session,
                )
            }
            return self._profiles(
                value for value in documents if value["_id"] in active
            )

    def catalogs(self, profiles):
        entity_ids = sorted({key for profile in profiles for key in profile.entity_ids})
        project_ids = sorted(
            {key for profile in profiles for key in profile.research_project_ids}
        )
        with mongo_errors(self.session):
            entities = {
                str(value["_id"]): attributes(value)
                for value in self.database.entities.find(
                    {"_id": {"$in": entity_ids}}, session=self.session
                )
            }
            projects = {
                str(value["_id"]): attributes(value)
                for value in self.database.research_projects.find(
                    {"_id": {"$in": project_ids}}, session=self.session
                )
            }
        return Catalogs(entities, projects)
