import hashlib
import json
from datetime import date, datetime
from itertools import combinations
from typing import Any
from zoneinfo import ZoneInfo

from modules.auth.domain.profile import Profile
from modules.connections.domain.connection import Connection
from modules.graph.domain.catalogs import Catalogs
from modules.graph.domain.graph import Edge, NetworkGraph


def _date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def build_graph(
    profiles: list[Profile],
    connections: list[Connection],
    catalogs: Catalogs,
    today: date | None = None,
) -> NetworkGraph:
    today = today or datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    by_id = {p.id: p for p in profiles}
    edges: dict[str, Edge] = {}

    def add(
        a: str, b: str, kind: str, context: dict[str, Any], identifier: str = ""
    ) -> None:
        if a == b or a not in by_id or b not in by_id:
            return
        a, b = sorted((a, b))
        digest = hashlib.sha256(
            json.dumps([a, b, kind, context], sort_keys=True).encode()
        ).hexdigest()
        key = f"{kind}:{identifier or digest}"
        edges[key] = Edge(key, a, b, kind, context)

    for connection in connections:
        if connection.status == "accepted":
            add(
                connection.user_a_id,
                connection.user_b_id,
                "close",
                {"label": "Conexão próxima confirmada", "connection_id": connection.id},
                connection.id,
            )

    classes: dict[tuple, list[str]] = {}
    memberships: dict[str, list[tuple[str, date, date]]] = {}
    for profile in profiles:
        if profile.type in ("aluno", "alumni"):
            if (
                profile.course
                and profile.entry_year
                and profile.entry_semester in (1, 2)
                and profile.class_group
            ):
                group = (
                    profile.course,
                    profile.entry_year,
                    profile.entry_semester,
                    profile.class_group,
                )
                classes.setdefault(group, []).append(profile.id)
            for membership in profile.entity_memberships:
                entity_id = str(membership.entity_id)
                start = _date(membership.start_date)
                end = (
                    today if membership.end_date is None else _date(membership.end_date)
                )
                if entity_id in catalogs.entities and start and end and start <= end:
                    memberships.setdefault(entity_id, []).append(
                        (profile.id, start, end)
                    )
            for participation in profile.research_participations:
                advisor = by_id.get(participation.advisor_user_id or "")
                project_id = str(participation.project_id)
                if (
                    advisor
                    and advisor.type == "professor"
                    and project_id in catalogs.projects
                    and participation.id
                    and participation.status == "confirmed"
                ):
                    add(
                        profile.id,
                        advisor.id,
                        "ic",
                        {
                            "label": "Orientação de IC confirmada",
                            "project_id": project_id,
                            "title": catalogs.projects[project_id].get("title", ""),
                            "participation_id": participation.id,
                        },
                    )

    for group, members in classes.items():
        for a, b in combinations(sorted(members), 2):
            add(
                a,
                b,
                "class",
                {
                    "label": "Mesma turma",
                    "course": group[0],
                    "entry_year": group[1],
                    "entry_semester": group[2],
                    "class_group": group[3],
                },
            )
    for entity_id, members in memberships.items():
        for (a, start_a, end_a), (b, start_b, end_b) in combinations(members, 2):
            start, end = max(start_a, start_b), min(end_a, end_b)
            if start <= end:
                add(
                    a,
                    b,
                    "entity",
                    {
                        "label": "Mesma entidade",
                        "entity_id": entity_id,
                        "name": catalogs.entities[entity_id].get("name", ""),
                        "start_date": start.isoformat(),
                        "end_date": end.isoformat(),
                    },
                )
    return NetworkGraph(profiles, list(edges.values()), catalogs)
