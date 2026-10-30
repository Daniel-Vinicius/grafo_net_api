from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Catalogs:
    entities: dict[str, dict[str, Any]] = field(default_factory=dict)
    projects: dict[str, dict[str, Any]] = field(default_factory=dict)
