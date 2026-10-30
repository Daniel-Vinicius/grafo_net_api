import pytest

from modules.auth.domain.errors import ValidationError
from modules.auth.domain.research_project import ResearchProject

PROJECT = {
    "title": "Pesquisa",
    "description": "Dados",
    "advisor": "Professora",
    "field_id": "technology",
    "start_date": "2025-01-01",
    "end_date": None,
    "status": "in_progress",
}


def test_project_supports_open_ended_period_and_no_creator():
    project = ResearchProject.create(None, PROJECT)
    assert project.id and project.creator_id is None and project.end_date is None


@pytest.mark.parametrize(
    "changes",
    [
        {"end_date": "2024-01-01"},
        {"status": "unknown"},
        {"title": " "},
        {"field_id": "unknown"},
        {"start_date": "20250101"},
    ],
)
def test_project_rejects_invalid_values(changes):
    with pytest.raises(ValidationError):
        ResearchProject.create("owner", {**PROJECT, **changes})
