from dataclasses import dataclass
import heapq
from typing import Any

from modules.connections.domain.errors import NetworkError
from modules.auth.domain.profile import Profile


@dataclass(frozen=True)
class Edge:
    id: str
    source: str
    target: str
    type: str
    context: dict[str, Any]

    @property
    def contextual(self) -> int:
        return int(self.type != "close")

    def public(self) -> dict[str, Any]:
        return {"id": self.id, "source": self.source, "target": self.target,
                "type": self.type, "context": self.context}


@dataclass(frozen=True)
class Path:
    user_ids: tuple[str, ...]
    edges: tuple[Edge, ...]
    cost: tuple[int, int]

    def public(self) -> dict[str, Any]:
        return {"user_ids": list(self.user_ids),
                "steps": [{**edge.public(), "order": i + 1,
                           "source": self.user_ids[i], "target": self.user_ids[i + 1]}
                          for i, edge in enumerate(self.edges)],
                "cost": {"contextual_edges": self.cost[0], "hops": self.cost[1]}}


class PathTree:
    def __init__(self, origin: str, costs: dict[str, tuple[int, int]],
                 previous: dict[str, tuple[str, Edge]]):
        self.origin, self.costs, self.previous = origin, costs, previous

    def path_to(self, target: str) -> Path | None:
        if target not in self.costs:
            return None
        users, edges = [target], []
        while users[-1] != self.origin:
            parent, edge = self.previous[users[-1]]
            users.append(parent)
            edges.append(edge)
        return Path(tuple(reversed(users)), tuple(reversed(edges)), self.costs[target])


class NetworkGraph:
    def __init__(self, profiles: list[Profile], edges: list[Edge]):
        self.profiles = {p.id: p for p in profiles}
        self.edges = {edge.id: edge for edge in edges}
        self.adjacency: dict[str, list[tuple[str, Edge]]] = {p.id: [] for p in profiles}
        for edge in self.edges.values():
            if edge.source in self.profiles and edge.target in self.profiles:
                self.adjacency[edge.source].append((edge.target, edge))
                self.adjacency[edge.target].append((edge.source, edge))
        for neighbors in self.adjacency.values():
            neighbors.sort(key=lambda item: (item[0], item[1].type, item[1].id))

    def require(self, user_id: str) -> Profile:
        if user_id not in self.profiles:
            raise NetworkError("Perfil inexistente ou inativo", 404)
        return self.profiles[user_id]

    def paths_from(self, origin: str) -> PathTree:
        self.require(origin)
        costs = {origin: (0, 0)}
        previous: dict[str, tuple[str, Edge]] = {}
        queue = [(0, 0, origin)]
        while queue:
            contextual, hops, current = heapq.heappop(queue)
            if costs[current] != (contextual, hops):
                continue
            for neighbor, edge in self.adjacency[current]:
                candidate = (contextual + edge.contextual, hops + 1)
                if neighbor not in costs or candidate < costs[neighbor]:
                    costs[neighbor] = candidate
                    previous[neighbor] = current, edge
                    heapq.heappush(queue, (*candidate, neighbor))
        return PathTree(origin, costs, previous)

    def visualization(self, origin: str, paths: list[Path | None],
                      targets: list[str]) -> dict[str, Any]:
        users = {origin, *targets}
        edges: dict[str, Edge] = {}
        for path in paths:
            if path:
                users.update(path.user_ids)
                edges.update((edge.id, edge) for edge in path.edges)
        return {"nodes": [self.profiles[key].to_network_public() for key in sorted(users)],
                "edges": [edges[key].public() for key in sorted(edges)]}

    def close_network(self, origin: str) -> dict[str, Any]:
        self.require(origin)
        edges = [edge for _, edge in self.adjacency[origin] if edge.type == "close"]
        users = {origin, *(neighbor for neighbor, edge in self.adjacency[origin] if edge.type == "close")}
        return {"nodes": [self.profiles[key].to_network_public() for key in sorted(users)],
                "edges": [edge.public() for edge in edges]}

