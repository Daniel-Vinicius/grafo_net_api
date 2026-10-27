from typing import Any, Protocol


class EmbeddingRepository(Protocol):
    def all(self) -> dict[str, dict[str, Any]]: ...
    def save(self, record: dict[str, Any]) -> None: ...

