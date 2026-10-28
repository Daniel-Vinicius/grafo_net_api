from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from modules.connections.domain.connection import Connection


def test_connections_lists_only_requesters_records(
    client, ana, create_user, auth_headers, repos
):
    other = create_user("other")
    item = Connection.create(ana.id, other.id)
    repos.connections.save(item, insert=True)
    response = client.get("/connections", headers=auth_headers(ana))
    assert response.status_code == 200 and [
        record["id"] for record in response.json["connections"]
    ] == [item.id]


def test_connection_request_is_pending(client, ana, create_user, auth_headers, repos):
    other = create_user("other")
    response = client.post(
        "/connections", headers=auth_headers(ana), json={"target_user_id": other.id}
    )
    assert response.status_code == 201 and response.json["status"] == "pending"
    assert repos.connections.find_pair(ana.id, other.id) is not None


def test_duplicate_connection_is_rejected(
    client, ana, create_user, auth_headers, repos
):
    other = create_user("other")
    repos.connections.save(Connection.create(ana.id, other.id), insert=True)
    assert (
        client.post(
            "/connections", headers=auth_headers(ana), json={"target_user_id": other.id}
        ).status_code
        == 409
    )


def test_recipient_can_accept(client, ana, create_user, auth_headers, repos):
    other = create_user("other")
    item = Connection.create(ana.id, other.id)
    repos.connections.save(item, insert=True)
    response = client.post(
        f"/connections/{item.id}/accept", headers=auth_headers(other)
    )
    assert (
        response.status_code == 200
        and repos.connections.get(item.id).status == "accepted"
    )


def test_requester_cannot_accept_own_request(
    client, ana, create_user, auth_headers, repos
):
    other = create_user("other")
    item = Connection.create(ana.id, other.id)
    repos.connections.save(item, insert=True)
    assert (
        client.post(
            f"/connections/{item.id}/accept", headers=auth_headers(ana)
        ).status_code
        == 403
    )


def test_participant_can_remove_connection(
    client, ana, create_user, auth_headers, repos
):
    other = create_user("other")
    item = Connection.create(ana.id, other.id)
    repos.connections.save(item, insert=True)
    response = client.delete(f"/connections/{item.id}", headers=auth_headers(ana))
    assert response.status_code == 204 and repos.connections.get(item.id) is None


def test_outsider_cannot_remove_connection(
    client, ana, create_user, auth_headers, repos
):
    first = create_user("first")
    second = create_user("second")
    item = Connection.create(first.id, second.id)
    repos.connections.save(item, insert=True)
    assert (
        client.delete(f"/connections/{item.id}", headers=auth_headers(ana)).status_code
        == 403
    )


def test_concurrent_accepts_never_exceed_ten(
    app, ana, create_user, auth_headers, repos
):
    for i in range(9):
        friend = create_user(f"friend{i}")
        repos.connections.save(
            Connection.create(ana.id, friend.id, accepted=True), insert=True
        )
    people = [create_user("first"), create_user("second")]
    requests = [Connection.create(ana.id, person.id) for person in people]
    for item in requests:
        repos.connections.save(item, insert=True)
    headers = [auth_headers(person) for person in people]
    barrier = Barrier(2)

    def accept(index):
        with app.test_client() as client:
            barrier.wait(timeout=5)
            return client.post(
                f"/connections/{requests[index].id}/accept", headers=headers[index]
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(accept, range(2)))
    assert sorted(statuses) == [200, 409]
    assert repos.connections.count_accepted(ana.id) == 10


def test_removed_request_cannot_be_accepted(
    client, ana, create_user, auth_headers, repos
):
    other = create_user("other")
    item = Connection.create(ana.id, other.id)
    repos.connections.save(item, insert=True)
    assert (
        client.delete(f"/connections/{item.id}", headers=auth_headers(ana)).status_code
        == 204
    )
    assert (
        client.post(
            f"/connections/{item.id}/accept", headers=auth_headers(other)
        ).status_code
        == 404
    )


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/connections"),
        ("post", "/connections"),
        ("post", "/connections/item/accept"),
        ("delete", "/connections/item"),
    ],
)
def test_connection_routes_require_authentication(client, method, path):
    assert getattr(client, method)(path).status_code == 401
