from copy import deepcopy
from dataclasses import dataclass, field, fields
from datetime import datetime
from threading import RLock
from typing import Any

from modules.auth.domain.invite import Invite
from modules.auth.domain.profile import Profile
from modules.auth.domain.research_project import ResearchProject
from modules.auth.domain.user import User
from modules.connections.domain.connection import Connection


@dataclass
class MemoryDatabase:
    users: dict[str, User] = field(default_factory=dict)
    profiles: dict[str, Profile] = field(default_factory=dict)
    invites: dict[str, Invite] = field(default_factory=dict)
    tokens: dict[str, datetime] = field(default_factory=dict)
    entities: dict[str, dict] = field(default_factory=dict)
    projects: dict[str, ResearchProject] = field(default_factory=dict)
    photos: dict[str, bytes] = field(default_factory=dict)
    photo_cleanup: dict[str, datetime] = field(default_factory=dict)
    connections: dict[str, Connection] = field(default_factory=dict)
    embeddings: dict[str, dict] = field(default_factory=dict)
    lock: Any = field(default_factory=RLock)

    def snapshot(self):
        return {
            item.name: deepcopy(getattr(self, item.name))
            for item in fields(self)
            if item.name != "lock"
        }

    def restore(self, snapshot):
        for name, value in snapshot.items():
            setattr(self, name, value)
