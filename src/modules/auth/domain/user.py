from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    id: str
    email: str
    password_hash: str
    is_active: bool = False

    def to_public(self) -> dict:
        return {
            "id": self.id,
            "email": self.email
        }
