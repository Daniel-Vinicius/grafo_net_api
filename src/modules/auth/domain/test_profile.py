from dataclasses import FrozenInstanceError, replace

import pytest

from modules.auth.domain.errors import ValidationError
from modules.auth.domain.profile import (
    EntityMembership,
    Profile,
    ResearchParticipation,
)


def profile(**changes):
    return replace(
        Profile("p", "Pessoa", "computer-science", 2, "technology", "Bio"), **changes
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"semester": True},
        {"semester": 0},
        {"semester": 9},
        {"name": " "},
        {"bio": "x" * 501},
        {"course_id": "bad"},
        {"field_id": "bad"},
        {"type": "admin"},
        {"entry_year": True},
        {"entry_year": 100},
        {"entry_semester": 3},
        {"experiences_completed": 1},
        {"entity_ids": ["a", "a"]},
        {"company": None},
    ],
)
def test_profile_rejects_invalid_values(changes):
    with pytest.raises(ValidationError):
        profile(**changes)


def test_removing_link_preserves_other_membership_details():
    first = EntityMembership("first", "a", "Membro", "2025-01-01", None)
    second = EntityMembership("second", "b", "Diretor", "2025-01-01", None)
    original = profile(
        entity_ids=("a", "b"), entity_memberships=(first, second), company="Empresa"
    )
    changed = original.with_changes({"entity_ids": ["b"]})
    assert changed.entity_memberships == (second,) and changed.company == "Empresa"
    assert original.entity_memberships == (first, second)


def test_profile_cannot_be_mutated_in_place():
    original = profile(entity_ids=("a",))
    with pytest.raises(FrozenInstanceError):
        setattr(original, "name", "Outro")
    with pytest.raises(AttributeError):
        getattr(original.entity_ids, "append")("b")


@pytest.mark.parametrize(
    "start,end",
    [
        ("20250101", None),
        ("bad", None),
        ("2025-05-01", "2025-01-01"),
        ("2025-02-30", None),
    ],
)
def test_invalid_periods_are_rejected(start, end):
    with pytest.raises(ValidationError):
        EntityMembership("m", "e", "Membro", start, end)


def test_participation_requires_official_link_and_valid_status():
    item = ResearchParticipation(
        "r", "project", "advisor", "Pesquisador", "2025-01-01", None
    )
    with pytest.raises(ValidationError):
        profile(research_participations=(item,))
    with pytest.raises(ValidationError):
        replace(item, status="invented")
