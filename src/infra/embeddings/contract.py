from typing import Protocol

from infra.errors import UnavailableError


class EmbeddingUnavailable(UnavailableError):
    pass


class EmbeddingProvider(Protocol):
    model: str
    dimensions: int

    def document(self, text: str, title: str) -> list[float]: ...
    def query(self, text: str) -> list[float]: ...
