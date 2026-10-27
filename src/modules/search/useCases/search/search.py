import math
from typing import Any

from modules.connections.domain.errors import NetworkError
from modules.graph.domain.catalogs import Catalogs
from modules.auth.domain.profile import Profile
from modules.graph.domain.graph import NetworkGraph, Path
from modules.search.embeddings import EmbeddingUnavailable, normalized
from modules.search.useCases.index.index import IndexProfilesUseCase


class SearchUseCase:
    def __init__(self, index: IndexProfilesUseCase, min_score: float = 0.5):
        self.index, self.min_score = index, min_score

    def search(self, origin: str, graph: NetworkGraph, catalogs: Catalogs,
               query: object, mode: object = "proximity", limit: object = 10,
               offset: object = 0) -> dict[str, Any]:
        if not isinstance(query, str) or not query.strip() or len(query) > 4000:
            raise NetworkError("Envie query com 1 a 4000 caracteres")
        if mode not in ("proximity", "relevance"):
            raise NetworkError("mode deve ser proximity ou relevance")
        if type(limit) is not int or not 1 <= limit <= 50:
            raise NetworkError("limit deve ser inteiro entre 1 e 50")
        if type(offset) is not int or offset < 0:
            raise NetworkError("offset deve ser inteiro não negativo")
        tree = graph.paths_from(origin)
        vector = normalized(self.index.provider.query(query.strip()), self.index.provider.dimensions)
        records = self.index.repository.all()
        candidates: list[tuple[Profile, float]] = []
        pending = 0
        for profile in graph.profiles.values():
            if profile.id == origin:
                continue
            record = records.get(profile.id)
            if not self.index.current(record, profile, catalogs) or record is None:
                pending += 1
                continue
            try:
                stored = normalized(record["vector"], self.index.provider.dimensions)
            except (EmbeddingUnavailable, KeyError, TypeError):
                pending += 1
                continue
            score = max(-1.0, min(1.0, sum(a * b for a, b in zip(vector, stored, strict=True))))
            if score >= self.min_score:
                candidates.append((profile, score))

        def key(item: tuple[Profile, float]) -> tuple:
            profile, score = item
            cost = tree.costs.get(profile.id)
            proximity = (cost is None, *(cost or (math.inf, math.inf)))
            if mode == "proximity":
                return (*proximity, -score, profile.id)
            return (-score, *proximity, profile.id)

        candidates.sort(key=key)
        selected = candidates[offset:offset + limit]
        paths: list[Path | None] = [tree.path_to(profile.id) for profile, _ in selected]
        results = []
        for (profile, score), path in zip(selected, paths, strict=True):
            public_path = path.public() if path else None
            results.append({"profile": profile.to_network_public(), "similarity": score,
                            "cost": public_path["cost"] if public_path else None,
                            "path": public_path})
        return {"results": results, "total": len(candidates), "mode": mode,
                "limit": limit, "offset": offset, "indexing_pending": pending,
                "graph": graph.visualization(origin, paths, [p.id for p, _ in selected])}
