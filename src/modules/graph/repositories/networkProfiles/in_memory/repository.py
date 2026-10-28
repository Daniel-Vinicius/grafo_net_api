from copy import deepcopy

from infra.database.memory import MemoryDatabase
from modules.graph.domain.catalogs import Catalogs


class InMemoryNetworkProfileRepository:
    def __init__(self, database: MemoryDatabase):
        self.database = database

    def list_active(self):
        with self.database.lock:
            return [
                profile
                for identifier, profile in self.database.profiles.items()
                if (user := self.database.users.get(identifier)) is not None
                and user.is_active
            ]

    def get_active(self, identifier):
        with self.database.lock:
            user = self.database.users.get(identifier)
            return (
                self.database.profiles.get(identifier)
                if user and user.is_active
                else None
            )

    def by_reference(self, kind, identifier):
        with self.database.lock:
            field = "entity_ids" if kind == "entity" else "research_project_ids"
            return [
                profile
                for profile in self.list_active()
                if identifier in getattr(profile, field)
            ]

    def catalogs(self, profiles):
        with self.database.lock:
            entity_ids = {key for profile in profiles for key in profile.entity_ids}
            project_ids = {
                key for profile in profiles for key in profile.research_project_ids
            }
            return Catalogs(
                {
                    key: deepcopy(self.database.entities[key])
                    for key in entity_ids
                    if key in self.database.entities
                },
                {
                    key: self.database.projects[key].to_dict()
                    for key in project_ids
                    if key in self.database.projects
                },
            )
