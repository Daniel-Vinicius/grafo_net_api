from modules.graph.domain.catalogs import Catalogs
from modules.auth.domain.profile import Profile


class InMemoryProfileRepository:
    def __init__(self, profiles: list[Profile], catalogs: Catalogs | None = None):
        self.profiles = profiles
        self._catalogs = catalogs or Catalogs()

    def list_active(self) -> list[Profile]:
        return list(self.profiles)

    def catalogs(self) -> Catalogs:
        return self._catalogs
