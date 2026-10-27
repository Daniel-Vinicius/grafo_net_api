"""Complete canonical profiles for graph/search fixtures; no alternate model."""
from typing import Any
from modules.auth.domain.profile import Profile


def make_profile(identifier: str, name: str, **metadata: Any) -> Profile:
    return Profile(id=identifier, name=name, **{
        "course_id": "computer-science", "semester": 1, "field_id": "technology",
        "bio": "Estudante de computação", **metadata,
    })
