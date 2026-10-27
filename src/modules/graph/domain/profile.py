"""Visão pública independente do User de autenticação."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class NetworkProfile:
    id: str
    name: str
    type: str = ""
    course: str = ""
    entry_year: int | None = None
    entry_semester: int | None = None
    class_group: str = ""
    bio: str = ""
    role: str = ""
    company: str = ""
    photo_url: str = ""
    interests: tuple[str, ...] = ()
    experiences: tuple[dict[str, Any], ...] = ()
    entity_memberships: tuple[dict[str, Any], ...] = ()
    research_participations: tuple[dict[str, Any], ...] = ()

    def public(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "type": self.type,
                "course": self.course, "bio": self.bio, "role": self.role,
                "company": self.company, "photo_url": self.photo_url}


@dataclass(frozen=True)
class Catalogs:
    entities: dict[str, dict[str, str]] = field(default_factory=dict)
    projects: dict[str, dict[str, str]] = field(default_factory=dict)

