from dataclasses import dataclass, field


@dataclass(frozen=True)
class Catalogs:
    entities: dict[str, dict[str, str]] = field(default_factory=dict)
    projects: dict[str, dict[str, str]] = field(default_factory=dict)

