from typing import Protocol


class TokenIssuer(Protocol):
    def issue(self, identifier: str, version: int) -> str: ...
