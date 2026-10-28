from dataclasses import replace
from datetime import date

import pytest

from modules.auth.domain.errors import NotFoundError
from modules.auth.domain.profile import EntityMembership, ResearchParticipation
from modules.connections.domain.connection import Connection
from modules.graph.domain.builder import build_graph
from modules.graph.domain.catalogs import Catalogs
from modules.graph.domain.graph import Edge, NetworkGraph
from tests.support.profiles import make_profile


def edge(a: str, b: str, kind: str = "close") -> Edge:
    return Edge(f"{kind}:{a}:{b}", a, b, kind, {"label": kind})


def test_trust_priority_over_hops_and_preserves_parallel_context():
    profiles = [make_profile(key, key) for key in "abcd"]
    graph = NetworkGraph(
        profiles,
        [
            edge("a", "b"),
            edge("b", "c"),
            edge("c", "d"),
            edge("a", "d", "entity"),
            edge("a", "b", "class"),
        ],
    )
    tree = graph.paths_from("a")
    path = tree.path_to("d")
    assert path is not None
    assert path.user_ids == ("a", "b", "c", "d")
    assert path.cost == (0, 3)
    assert all(item.type == "close" for item in path.edges)
    assert len(graph.edges) == 5


def test_contextual_count_then_hops_and_deterministic_tie():
    profiles = [make_profile(key, key) for key in "abcdef"]
    edges = [
        edge("a", "b"),
        edge("b", "f", "entity"),
        edge("a", "c"),
        edge("c", "f", "ic"),
        edge("a", "d"),
        edge("d", "e"),
        edge("e", "f", "class"),
    ]
    first = NetworkGraph(profiles, edges).paths_from("a").path_to("f")
    second = (
        NetworkGraph(list(reversed(profiles)), list(reversed(edges)))
        .paths_from("a")
        .path_to("f")
    )
    assert first == second
    assert first is not None and first.cost == (1, 2)
    assert first.user_ids == ("a", "b", "f")


def test_cycle_isolation_same_origin_and_no_depth_cutoff():
    profiles = [make_profile(str(i), str(i)) for i in range(32)]
    edges = [edge(str(i), str(i + 1)) for i in range(30)] + [edge("0", "2")]
    graph = NetworkGraph(profiles, edges)
    tree = graph.paths_from("0")
    own = tree.path_to("0")
    assert own is not None and own.cost == (0, 0) and own.edges == ()
    assert tree.path_to("31") is None
    distant = tree.path_to("30")
    assert distant is not None and distant.cost == (0, 29)
    with pytest.raises(NotFoundError, match="inexistente"):
        graph.paths_from("missing")
    visual = graph.visualization("0", [None], ["31"])
    assert {node["id"] for node in visual["nodes"]} == {"0", "31"}
    assert visual["edges"] == []


def membership(start: str, end: str | None = None) -> tuple[EntityMembership, ...]:
    return (EntityMembership("m", "code", "Integrante", start, end),)


def test_entity_overlap_professors_missing_dates_and_class_fields():
    a = make_profile(
        "a",
        "Ana",
        type="aluno",
        course_id="computer-science",
        entry_year=2024,
        entry_semester=1,
        class_group="A",
        entity_ids=["code"],
        entity_memberships=membership("2024-01-01"),
    )
    b = replace(
        a,
        id="b",
        name="Bruno",
        entity_ids=["code"],
        entity_memberships=membership("2025-01-01", "2025-06-01"),
    )
    c = replace(
        a,
        id="c",
        entry_year=None,
        entity_ids=["code"],
        entity_memberships=membership("2020-01-01", "2020-12-31"),
    )
    d = replace(a, id="d", type="professor")
    e = replace(a, id="e", class_group="", entity_memberships=())
    graph = build_graph(
        [a, b, c, d, e],
        [],
        Catalogs(entities={"code": {"name": "Insper Code"}}),
        date(2026, 1, 1),
    )
    assert sorted(edge.type for edge in graph.edges.values()) == ["class", "entity"]
    contextual = next(edge for edge in graph.edges.values() if edge.type == "entity")
    assert contextual.context["start_date"] == "2025-01-01"
    assert contextual.context["end_date"] == "2025-06-01"
    assert contextual.source == "a" and contextual.target == "b"


@pytest.mark.parametrize("end", ["2024-01-01", "2024-01-02"])
def test_entity_overlap_inclusive_boundary(end):
    a = make_profile(
        "a",
        "A",
        type="alumni",
        entity_ids=["code"],
        entity_memberships=membership("2023-01-01", end),
    )
    b = make_profile(
        "b",
        "B",
        type="aluno",
        entity_ids=["code"],
        entity_memberships=membership("2024-01-01"),
    )
    graph = build_graph([a, b], [], Catalogs(entities={"code": {}}), date(2026, 1, 1))
    assert len(graph.edges) == 1


def test_ic_requires_confirmed_identified_professor_and_project():
    professor = make_profile("p", "Professora", type="professor")
    participation = ResearchParticipation(
        "part", "r", "p", "Pesquisador", "2025-01-01", None, "confirmed"
    )
    student = make_profile(
        "s",
        "Estudante",
        type="aluno",
        research_project_ids=["r"],
        research_participations=(participation,),
    )
    catalogs = Catalogs(projects={"r": {"title": "IA"}})
    assert len(build_graph([professor, student], [], catalogs).edges) == 1
    for change in (
        {"status": "pending"},
        {"advisor_user_id": "missing"},
        {"project_id": "unknown"},
    ):
        changed = replace(
            student,
            research_project_ids=[change.get("project_id", "r")],
            research_participations=(replace(participation, **change),),
        )
        assert not build_graph([professor, changed], [], catalogs).edges
    assert not build_graph(
        [replace(professor, type="alumni"), student], [], catalogs
    ).edges


def test_only_accepted_connections_between_active_profiles_are_used():
    a, b = make_profile("a", "A"), make_profile("b", "B")
    connections = [
        Connection.create("a", "b"),
        Connection.create("a", "inactive", True),
    ]
    assert not build_graph([a, b], connections, Catalogs()).edges
    graph = build_graph([a, b], [Connection.create("a", "b", True)], Catalogs())
    assert len(graph.close_network("a")["nodes"]) == 2
