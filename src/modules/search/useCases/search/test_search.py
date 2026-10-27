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


def test_modes_cutoff_pagination_isolation_and_intermediaries(indexed_profiles):
    reader, _, provider, index, graph = indexed_profiles
    service = SearchUseCase(index)
    response = service.search("me", graph, reader.catalogs(), "dados")
    assert [r["profile"]["id"] for r in response["results"]] == ["a", "b", "c"]
    assert response["total"] == 3 and response["results"][-1]["path"] is None
    relevant = service.search("me", graph, reader.catalogs(), "dados", "relevance", 1)
    assert relevant["results"][0]["profile"]["id"] == "c"
    assert relevant["graph"]["edges"] == []
    second = service.search("me", graph, reader.catalogs(), "dados", limit=1, offset=1)
    assert second["total"] == 3
    assert {n["id"] for n in second["graph"]["nodes"]} == {"me", "a", "b"}
    # Mesmo com Ana fora do corte, ela continua sendo intermediária até Bruno.
    strict = SearchUseCase(index, 0.9).search("me", graph, reader.catalogs(), "dados")
    assert strict["results"][0]["path"]["user_ids"] == ["me", "a", "b"]
    assert provider.documents == 5 and provider.queries == 4


def test_one_query_embedding_for_1000_preindexed_profiles(embedding_provider):
    profiles = [Profile(str(i), f"Pessoa {i}") for i in range(1000)]
    reader, repository, provider = InMemoryProfileRepository(profiles), InMemoryEmbeddingRepository(), embedding_provider
    index = IndexProfilesUseCase(reader, repository, provider)
    assert index.refresh()["indexed"] == 1000
    graph = build_graph(profiles, [], Catalogs())
    response = SearchUseCase(index).search("0", graph, Catalogs(), "quero alguém de dados")
    assert response["total"] == 999 and len(response["results"]) == 10
    assert provider.documents == 1000 and provider.queries == 1


@pytest.mark.parametrize("kwargs", [{"query": " "}, {"query": "x" * 4001}, {"query": None},
                                    {"mode": "unknown"}, {"limit": True}, {"limit": 51},
                                    {"offset": -1}, {"offset": 0.5}])
def test_invalid_search_input(indexed_profiles, kwargs):
    reader, _, provider, index, graph = indexed_profiles
    with pytest.raises(NetworkError):
        SearchUseCase(index).search("me", graph, reader.catalogs(), **{"query": "dados", **kwargs})
    assert provider.queries == 0


