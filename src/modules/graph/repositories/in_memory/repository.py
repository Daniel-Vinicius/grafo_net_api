from modules.graph.domain.profile import Catalogs, NetworkProfile


class InMemoryProfileRepository:
    def __init__(self, profiles: list[NetworkProfile], catalogs: Catalogs | None = None):
        self.profiles = profiles
        self._catalogs = catalogs or Catalogs()

    def list_active(self) -> list[NetworkProfile]:
        return list(self.profiles)

    def catalogs(self) -> Catalogs:
        return self._catalogs
