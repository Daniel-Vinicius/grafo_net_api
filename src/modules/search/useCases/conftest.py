import math

import pytest

from modules.connections.domain.connection import Connection
from modules.graph.domain.profile import Catalogs, NetworkProfile as Profile
from modules.graph.repositories.in_memory.repository import InMemoryProfileRepository
from modules.graph.useCases.buildGraph.buildGraph import build_graph
from modules.search.embeddings import EmbeddingUnavailable
from modules.search.repositories.in_memory.repository import InMemoryEmbeddingRepository
from modules.search.useCases.index.index import IndexProfilesUseCase


class FakeEmbeddings:
    model = "fake-embedding"
    dimensions = 3

    def __init__(self):
        self.documents = 0
        self.queries = 0
        self.fail = False
        self.vectors = {"Ana": [0.8, 0.6, 0], "Bruno": [0.95, math.sqrt(1 - 0.95 ** 2), 0],
                        "Carla": [1, 0, 0], "Diego": [0, 1, 0]}

    def document(self, text: str, title: str) -> list[float]:
        self.documents += 1
        if self.fail:
            raise EmbeddingUnavailable()
        return self.vectors.get(title, [1, 0, 0])

    def query(self, text: str) -> list[float]:
        self.queries += 1
        if self.fail:
            raise EmbeddingUnavailable()
        return [1, 0, 0]


@pytest.fixture
def indexed_profiles():
    profiles = [Profile(key, name) for key, name in
                (("me", "Você"), ("a", "Ana"), ("b", "Bruno"), ("c", "Carla"), ("d", "Diego"))]
    reader = InMemoryProfileRepository(profiles)
    repository, provider = InMemoryEmbeddingRepository(), FakeEmbeddings()
    index = IndexProfilesUseCase(reader, repository, provider)
    index.refresh()
    connections = [Connection.create("me", "a", True), Connection.create("a", "b", True)]
    return reader, repository, provider, index, build_graph(profiles, connections, Catalogs())


@pytest.fixture
def embedding_provider():
    return FakeEmbeddings()
