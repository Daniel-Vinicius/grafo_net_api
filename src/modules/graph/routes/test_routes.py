import pytest

from modules.connections.domain.connection import Connection


@pytest.fixture
def path_people(create_user, repos):
    for name in ("origin", "middle", "target", "isolated"):
        create_user(name)
    for first, second in (("origin", "middle"), ("middle", "target")):
        repos.connections.save(
            Connection.create(first, second, accepted=True), insert=True
        )
    return repos.users.get("origin")


def test_graph_returns_only_direct_friends(client, path_people, auth_headers):
    response = client.get("/graph", headers=auth_headers(path_people))
    assert response.status_code == 200
    assert {node["id"] for node in response.json["nodes"]} == {"origin", "middle"}
    assert len(response.json["edges"]) == 1


def test_stats_counts_people_in_the_network(client, path_people, auth_headers):
    response = client.get("/graph/stats", headers=auth_headers(path_people))
    assert response.status_code == 200
    assert response.json == {"people": 4}


def test_stats_requires_authentication(client):
    assert client.get("/graph/stats").status_code == 401


def test_path_contains_complete_intermediaries_and_edge_references(
    client, path_people, auth_headers
):
    response = client.get("/graph/paths/target", headers=auth_headers(path_people))
    assert response.status_code == 200
    assert response.json["path"]["user_ids"] == ["origin", "middle", "target"]
    assert response.json["path"]["cost"] == {"contextual_edges": 0, "hops": 2}
    nodes = {node["id"]: node for node in response.json["graph"]["nodes"]}
    assert (
        len(nodes) == 3
        and {"bio", "course", "experiences", "photo_url"} <= nodes["middle"].keys()
    )
    edge_ids = {edge["id"] for edge in response.json["graph"]["edges"]}
    assert all(step["edge_id"] in edge_ids for step in response.json["path"]["steps"])


def test_unreachable_person_has_null_path(client, path_people, auth_headers):
    response = client.get("/graph/paths/isolated", headers=auth_headers(path_people))
    assert response.status_code == 200 and response.json["path"] is None
    assert {node["id"] for node in response.json["graph"]["nodes"]} == {
        "origin",
        "isolated",
    }


def test_path_to_self_has_zero_cost(client, path_people, auth_headers):
    response = client.get("/graph/paths/origin", headers=auth_headers(path_people))
    assert response.status_code == 200 and response.json["path"]["cost"] == {
        "contextual_edges": 0,
        "hops": 0,
    }


def test_missing_target_returns_404(client, path_people, auth_headers):
    assert (
        client.get(
            "/graph/paths/missing", headers=auth_headers(path_people)
        ).status_code
        == 404
    )


@pytest.mark.parametrize("path", ["/graph", "/graph/paths/person"])
def test_graph_requires_authentication(client, path):
    assert client.get(path).status_code == 401
