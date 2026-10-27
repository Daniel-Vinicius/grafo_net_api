from dataclasses import asdict, replace

import pytest

from modules.auth.domain.errors import ValidationError
from modules.auth.domain.profile import Profile
from modules.graph.domain.catalogs import Catalogs
from modules.graph.useCases.buildGraph.buildGraph import build_graph
from modules.search.domain.profile_text import TEXT_VERSION, searchable_text, source_hash
from test_profiles import make_profile


def test_same_class_preserves_self_and_network_contracts_and_search_privacy():
    profile = make_profile("u", "Ana", photo_id="PRIVATE_PHOTO", experiences_completed=True,
        type="aluno", entity_ids=["code"], research_project_ids=["r"],
        entity_memberships=({"entity_id": "code", "id": "PRIVATE_MEMBERSHIP", "role": "Diretora"},),
        research_participations=({"project_id": "r", "advisor_user_id": "PRIVATE_ADVISOR",
                                   "id": "PRIVATE_PARTICIPATION", "status": "confirmed"},),
        experiences=({"title": "Pesquisadora", "private_notes": "PRIVATE_NOTES"},))
    graph = build_graph([profile], [], Catalogs())
    assert type(graph.profiles["u"]) is Profile
    assert graph.profiles["u"] is profile
    assert set(profile.to_public()) == {"id", "name", "course_id", "semester", "field_id", "bio",
        "photo_id", "entity_ids", "research_project_ids", "experiences_completed"}
    assert set(profile.to_network_public()) == {"id", "name", "type", "course", "bio", "role", "company", "photo_url"}
    assert profile.to_network_public()["photo_url"] == ""
    catalogs = Catalogs(entities={"code": {"name": "Entidade", "secret": "PRIVATE_CATALOG"}},
                        projects={"r": {"title": "Projeto", "private_notes": "PRIVATE_PROJECT"}})
    text = searchable_text(profile, catalogs)
    assert all(value in text for value in ("Diretora", "Entidade", "Projeto", "Pesquisadora", "Tecnologia"))
    assert "PRIVATE" not in text
    assert "PRIVATE" not in str(graph.visualization("u", [], []))
    assert "experiences_completed" not in text
    assert "course" not in asdict(profile) and "field" not in asdict(profile)
    assert TEXT_VERSION == 3
    assert source_hash(profile, catalogs) == source_hash(replace(profile, photo_id=None, experiences_completed=False), catalogs)


@pytest.mark.parametrize("metadata", [
    {"entity_memberships": ({"entity_id": "unlinked"},)},
    {"research_participations": ({"project_id": "unlinked"},)},
])
def test_details_cannot_create_independent_links(metadata):
    with pytest.raises(ValidationError):
        make_profile("u", "Ana", **metadata)


def test_removing_link_prunes_only_its_metadata_and_preserves_omitted_values():
    profile = make_profile("u", "Ana", entity_ids=["a", "b"],
        entity_memberships=({"entity_id": "a", "role": "A"}, {"entity_id": "b", "role": "B"}),
        research_project_ids=["r"], research_participations=({"project_id": "r"},), company="Empresa")
    updated = profile.with_changes({"entity_ids": ["b"]})
    assert updated.entity_memberships == ({"entity_id": "b", "role": "B"},)
    assert updated.research_participations == profile.research_participations
    assert updated.company == "Empresa"
    assert profile.with_changes({"bio": "Nova bio"}).entity_memberships == profile.entity_memberships
