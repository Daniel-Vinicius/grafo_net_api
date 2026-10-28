from infra.database.context import Repositories
from infra.embeddings.contract import EmbeddingProvider, EmbeddingUnavailable
from modules.auth.domain.errors import ValidationError
from modules.graph.useCases.buildGraph.buildGraphUseCase import BuildGraphUseCase
from modules.search.domain.profile_text import current_embedding
from modules.search.domain.vectors import normalized


class SearchProfilesUseCase:
    def __init__(
        self,
        repos: Repositories,
        provider: EmbeddingProvider,
        graph: BuildGraphUseCase,
        min_score: float,
    ):
        self.repos = repos
        self.provider = provider
        self.graph = graph
        self.min_score = min_score

    def execute(self, identifier, data):
        if set(data) - {"query", "mode", "limit", "offset"}:
            raise ValidationError("Campos de busca inválidos")
        query, mode, limit, offset = (
            data.get("query"),
            data.get("mode", "proximity"),
            data.get("limit", 10),
            data.get("offset", 0),
        )
        if not isinstance(query, str) or not query.strip() or len(query) > 4000:
            raise ValidationError("Query deve ter 1 a 4000 caracteres")
        if mode not in ("proximity", "relevance"):
            raise ValidationError("Modo inválido")
        if (
            type(limit) is not int
            or not 1 <= limit <= 50
            or type(offset) is not int
            or offset < 0
        ):
            raise ValidationError("Paginação inválida")
        graph = self.graph.execute()
        tree = graph.paths_from(identifier)
        try:
            vector = normalized(
                self.provider.query(query.strip()), self.provider.dimensions
            )
        except ValidationError:
            raise EmbeddingUnavailable("Vetor da consulta inválido") from None
        records = self.repos.embeddings.get_many(list(graph.profiles))
        candidates, pending = [], 0
        for profile in graph.profiles.values():
            if profile.id == identifier:
                continue
            record = records.get(profile.id)
            if record is None or not current_embedding(
                record, profile, graph.catalogs, self.provider
            ):
                pending += 1
                continue
            try:
                stored = normalized(record["vector"], self.provider.dimensions)
            except ValidationError, KeyError, TypeError:
                pending += 1
                continue
            score = max(
                -1.0, min(1.0, sum(a * b for a, b in zip(vector, stored, strict=True)))
            )
            if score >= self.min_score:
                candidates.append((profile.id, score))

        def order(item):
            person, score = item
            cost = tree.costs.get(person)
            proximity = (cost is None, *(cost or (float("inf"), float("inf"))))
            return (
                (*proximity, -score, person)
                if mode == "proximity"
                else (-score, *proximity, person)
            )

        candidates.sort(key=order)
        selected = candidates[offset : offset + limit]
        paths = [tree.path_to(person) for person, _ in selected]
        results = [
            {
                "profile_id": person,
                "similarity": score,
                "cost": path.public()["cost"] if path else None,
                "path": path.public() if path else None,
            }
            for (person, score), path in zip(selected, paths, strict=True)
        ]
        return {
            "results": results,
            "total": len(candidates),
            "mode": mode,
            "limit": limit,
            "offset": offset,
            "indexing_pending": pending,
            "graph": graph.visualization(
                identifier, paths, [person for person, _ in selected]
            ),
        }
