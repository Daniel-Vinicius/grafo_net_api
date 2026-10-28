from dataclasses import replace

import pytest

from modules.auth.domain.errors import ValidationError
from modules.auth.domain.profile import Experience
from modules.graph.domain.catalogs import Catalogs
from modules.search.domain.profile_text import searchable_text, source_hash
from modules.search.domain.vectors import normalized
from tests.support.profiles import make_profile


def test_search_text_selects_semantic_fields_independently_of_display():
    profile = make_profile(
        "p",
        "Ana",
        photo_id="image-reference",
        experiences_completed=True,
        experiences=(
            Experience(
                "operational-id",
                "Analista",
                "Empresa",
                "trabalho",
                "2025-01-01",
                None,
                "Dados",
            ),
        ),
    )
    text = searchable_text(profile, Catalogs())
    assert "Dados" in text and "Empresa" in text
    assert (
        "image-reference" not in text
        and "operational-id" not in text
        and "experiences_completed" not in text
    )
    assert source_hash(profile, Catalogs()) == source_hash(
        replace(profile, photo_id=None, experiences_completed=False), Catalogs()
    )


@pytest.mark.parametrize(
    "value", [[], [0.0, 0.0], [float("nan"), 1.0], [True, 1.0], [float("inf"), 1.0]]
)
def test_invalid_vectors(value):
    with pytest.raises(ValidationError):
        normalized(value, 2)
