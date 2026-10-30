from modules.connections.domain.connection import Connection


def test_pair_is_canonical_and_requester_is_preserved():
    connection = Connection.create("z", "a")
    assert (connection.user_a_id, connection.user_b_id) == ("a", "z")
    assert connection.requested_by == "z" and connection.status == "pending"


def test_invitation_connection_is_already_accepted():
    connection = Connection.create("a", "b", accepted=True)
    assert connection.status == "accepted" and connection.accepted_at is not None
