from typing import Callable, Protocol, TypeVar

from infra.database.context import Repositories
from infra.errors import ConflictError

T = TypeVar("T")


class DuplicateRecordError(ConflictError):
    pass


class UnitOfWork(Protocol):
    def run(self, callback: Callable[[Repositories], T]) -> T: ...
