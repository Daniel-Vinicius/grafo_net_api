from typing import Protocol

from modules.graph.domain.profile import Catalogs, NetworkProfile


class ProfileRepository(Protocol):
    def list_active(self) -> list[NetworkProfile]: ...
    def catalogs(self) -> Catalogs: ...

