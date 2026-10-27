from dataclasses import replace

import pytest

from modules.connections.domain.errors import NetworkError
from modules.graph.domain.profile import Catalogs, NetworkProfile as Profile
from modules.graph.repositories.in_memory.repository import InMemoryProfileRepository
from modules.graph.useCases.buildGraph.buildGraph import build_graph
from modules.search.repositories.in_memory.repository import InMemoryEmbeddingRepository
from modules.search.useCases.index.index import IndexProfilesUseCase
from modules.search.useCases.search.search import SearchUseCase
from modules.search.domain.profile_text import searchable_text


def test_index_hash_invalidation_failure_recovery_and_no_photo_invalidation(indexed_profiles):
    reader, repository, provider, index, graph = indexed_profiles
    assert index.refresh() == {"indexed": 0, "unchanged": 5, "pending": 0}
    reader.profiles[1] = replace(reader.profiles[1], photo_url="new-photo")
    assert index.refresh(user_id="a")["unchanged"] == 1
    reader.profiles[1] = replace(reader.profiles[1], bio="Experiência em dados")
    # Hash antigo não entra nos resultados, mesmo antes de o hook ser chamado.
    graph = build_graph(reader.profiles, [], reader.catalogs())
    response = SearchUseCase(index).search("me", graph, reader.catalogs(), "dados")
    assert "a" not in [r["profile"]["id"] for r in response["results"]]
    assert response["indexing_pending"] == 1
    provider.fail = True
    assert index.refresh(user_id="a")["pending"] == 1
    assert repository.records["a"]["status"] == "pending"
    provider.fail = False
    assert index.refresh(user_id="a")["indexed"] == 1
    assert index.refresh(force=True)["indexed"] == 5


@pytest.mark.parametrize("field,value", [("model", "different"), ("dimensions", 99),
                                        ("text_version", 999), ("status", "pending"), ("vector", [0, 0, 0])])
def test_incompatible_or_corrupt_embeddings_excluded(indexed_profiles, field, value):
    reader, repository, _, index, graph = indexed_profiles
    repository.records["a"][field] = value
    response = SearchUseCase(index).search("me", graph, reader.catalogs(), "dados")
    assert "a" not in [r["profile"]["id"] for r in response["results"]]


def test_catalog_changes_and_targeted_reindex(embedding_provider):
    reader = InMemoryProfileRepository([
        Profile("a", "Ana", entity_memberships=({"entity_id": "e"},)), Profile("b", "Bruno")
    ], Catalogs(entities={"e": {"name": "Entidade", "description": "Dados"}}))
    provider, repository = embedding_provider, InMemoryEmbeddingRepository()
    index = IndexProfilesUseCase(reader, repository, provider)
    index.refresh()
    reader._catalogs.entities["e"]["description"] = "Robótica"
    assert index.refresh(reference=("entity", "e")) == {"indexed": 1, "unchanged": 0, "pending": 0}
    assert provider.documents == 3
    text = searchable_text(reader.profiles[0], reader.catalogs())
    assert "Robótica" in text


