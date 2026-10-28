from dataclasses import replace

import pytest


def test_search_returns_profiles_once_with_references(
    client, search_people, auth_headers, embeddings
):
    response = client.post(
        "/search",
        headers=auth_headers(search_people["origin"]),
        json={"query": "dados"},
    )
    assert response.status_code == 200 and response.json["total"] == 4
    nodes = {node["id"]: node for node in response.json["graph"]["nodes"]}
    assert len(nodes) == len(response.json["graph"]["nodes"]) == 5
    assert all(
        "profile" not in result and result["profile_id"] in nodes
        for result in response.json["results"]
    )
    assert embeddings.queries == 1 and embeddings.documents == 0


def test_proximity_prioritizes_close_friend_over_higher_score(
    client, search_people, auth_headers
):
    response = client.post(
        "/search",
        headers=auth_headers(search_people["origin"]),
        json={"query": "dados", "mode": "proximity"},
    )
    assert (
        response.status_code == 200
        and response.json["results"][0]["profile_id"] == "near"
    )


def test_relevance_prioritizes_score_and_reachability(
    client, search_people, auth_headers
):
    response = client.post(
        "/search",
        headers=auth_headers(search_people["origin"]),
        json={"query": "dados", "mode": "relevance"},
    )
    assert (
        response.status_code == 200
        and response.json["results"][0]["profile_id"] == "far"
    )


def test_pagination_respects_limit_offset_and_total(
    client, search_people, auth_headers
):
    response = client.post(
        "/search",
        headers=auth_headers(search_people["origin"]),
        json={"query": "dados", "limit": 1, "offset": 1},
    )
    assert response.status_code == 200
    assert len(response.json["results"]) == 1 and response.json["total"] == 4
    assert response.json["results"][0]["profile_id"] == "middle"
    assert {node["id"] for node in response.json["graph"]["nodes"]} == {
        "origin",
        "near",
        "middle",
    }


def test_offset_beyond_results_returns_empty_page(client, search_people, auth_headers):
    response = client.post(
        "/search",
        headers=auth_headers(search_people["origin"]),
        json={"query": "dados", "offset": 50},
    )
    assert (
        response.status_code == 200
        and response.json["results"] == []
        and response.json["total"] == 4
    )


def test_pending_vector_is_excluded_from_results_but_not_paths(
    client, search_people, auth_headers, repos
):
    record = repos.embeddings.get_many(["near"])["near"]
    repos.embeddings.save({**record, "status": "pending"})
    response = client.post(
        "/search",
        headers=auth_headers(search_people["origin"]),
        json={"query": "dados"},
    )
    assert response.status_code == 200 and response.json["indexing_pending"] == 1
    assert "near" not in {item["profile_id"] for item in response.json["results"]}
    assert "near" in {node["id"] for node in response.json["graph"]["nodes"]}


def test_changed_profile_does_not_use_stale_embedding(
    client, search_people, auth_headers, repos
):
    repos.profiles.save(replace(repos.profiles.get("near"), bio="Nova bio"))
    response = client.post(
        "/search",
        headers=auth_headers(search_people["origin"]),
        json={"query": "dados"},
    )
    assert response.status_code == 200 and response.json["indexing_pending"] == 1


def test_embedding_service_failure_returns_503(client, ana, auth_headers, embeddings):
    embeddings.fail = True
    assert (
        client.post(
            "/search", headers=auth_headers(ana), json={"query": "dados"}
        ).status_code
        == 503
    )


@pytest.mark.parametrize(
    "data",
    [
        {"query": " "},
        {"query": None},
        {"query": "x" * 4001},
        {"query": "x", "limit": True},
        {"query": "x", "offset": -1},
        {"query": "x", "mode": "bad"},
    ],
)
def test_invalid_search_is_rejected_before_provider_call(
    client, ana, auth_headers, embeddings, data
):
    response = client.post("/search", headers=auth_headers(ana), json=data)
    assert response.status_code == 400 and embeddings.queries == 0


def test_search_requires_authentication(client):
    assert client.post("/search", json={"query": "dados"}).status_code == 401
