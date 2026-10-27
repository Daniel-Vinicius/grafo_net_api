from typing import Protocol

from modules.graph.domain.catalogs import Catalogs
from modules.auth.domain.profile import Profile


class ProfileRepository(Protocol):
    def list_active(self) -> list[Profile]: ...
    def catalogs(self) -> Catalogs: ...

