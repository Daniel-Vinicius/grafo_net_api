from dataclasses import replace
from unittest.mock import Mock

import pytest
from flask import Flask
from flask_jwt_extended import create_access_token

from config import configure_app, configure_cors
from modules.auth.domain.user import User
from modules.auth.email import EmailSender
from modules.auth.repositories.in_memory.repository import (
    InMemoryInviteRepository, InMemoryTokenRepository, InMemoryUserRepository,
)
from modules.auth.routes.routes import create_auth_routes
from modules.connections.domain.connection import Connection
from modules.connections.routes.routes import create_connections_routes
from modules.graph.domain.profile import NetworkProfile
from modules.graph.repositories.in_memory.repository import InMemoryProfileRepository
from modules.graph.routes.routes import create_graph_routes
from modules.search.embeddings import EmbeddingUnavailable
from modules.search.repositories.in_memory.repository import InMemoryEmbeddingRepository
from modules.search.useCases.index.index import IndexProfilesUseCase
from modules.search.routes.routes import create_search_routes


class TestEmbeddings:
    __test__ = False
    model = "test"
    dimensions = 2
    unavailable = False

    def document(self, text: str, title: str) -> list[float]:
        if self.unavailable:
            raise EmbeddingUnavailable()
        return [1, 0]

    def query(self, text: str) -> list[float]:
        return self.document(text, "")


@pytest.fixture
def network():
    app = Flask(__name__)
    configure_app(app, {"TESTING": True, "JWT_SECRET_KEY": "network-test-at-least-32-byte-secret",
                        "FRONTEND_URL": "http://localhost:5173"})
    users = InMemoryUserRepository([User(key, f"{key}@insper.edu.br", "hash", True) for key in "abc"])
    invites = InMemoryInviteRepository(users)
    app.register_blueprint(create_auth_routes(app, users, InMemoryTokenRepository(), invites, Mock(spec=EmailSender)))
    profiles = InMemoryProfileRepository([NetworkProfile(key, key) for key in "abc"])
    provider = TestEmbeddings()
    index = IndexProfilesUseCase(profiles, InMemoryEmbeddingRepository(), provider)
    index.refresh()
    configure_cors(app)
    app.register_blueprint(create_connections_routes(app))
    app.register_blueprint(create_graph_routes(app, profiles, invites.connections))
    app.register_blueprint(create_search_routes(app, index))
    with app.app_context():
        headers = {key: {"Authorization": "Bearer " + create_access_token(identity=key)} for key in "abc"}
    return app, app.test_client(), headers, users, invites.connections, profiles, provider


def test_http_connection_lifecycle_and_unprefixed_routes(network):
    app, client, headers, users, repository, profiles, provider = network
    assert client.post("/connections", json={"target_user_id": "b"}).status_code == 401
    result = client.post("/connections", json={"target_user_id": "b"}, headers=headers["a"])
    assert result.status_code == 201
    identifier = result.json["id"]
    assert result.json["status"] == "pending"
    assert client.get("/connections", headers=headers["b"]).json["connections"][0]["id"] == identifier
    assert client.post(f"/connections/{identifier}/accept", headers=headers["a"]).status_code == 403
    assert client.delete(f"/connections/{identifier}", headers=headers["c"]).status_code == 403
    assert client.post(f"/connections/{identifier}/accept", headers=headers["b"]).status_code == 200
    assert len(client.get("/graph", headers=headers["a"]).json["edges"]) == 1
    path = client.get("/graph/paths/b", headers=headers["a"])
    assert path.json["path"]["cost"] == {"contextual_edges": 0, "hops": 1}
    assert client.delete(f"/connections/{identifier}", headers=headers["b"]).status_code == 204
    assert client.get("/api/graph", headers=headers["a"]).status_code == 404


@pytest.mark.parametrize("method,path", [("get", "/connections"), ("post", "/connections"),
    ("post", "/connections/id/accept"), ("delete", "/connections/id"),
    ("get", "/graph"), ("get", "/graph/paths/b"), ("post", "/search")])
def test_all_network_routes_require_authentication(network, method, path):
    _, client, *_ = network
    assert getattr(client, method)(path).status_code == 401


def test_search_unreachable_target_and_provider_outage(network):
    app, client, headers, users, repository, profiles, provider = network
    result = client.post("/search", json={"query": "dados"}, headers=headers["a"])
    assert result.status_code == 200 and result.json["total"] == 2
    assert all(item["path"] is None for item in result.json["results"])
    assert result.json["graph"]["edges"] == []
    assert client.get("/graph/paths/c", headers=headers["a"]).json["path"] is None
    assert client.get("/graph/paths/missing", headers=headers["a"]).status_code == 404
    profiles.profiles = profiles.profiles[:2]  # Adaptador só retorna ativos.
    assert client.get("/graph/paths/c", headers=headers["a"]).status_code == 404
    provider.unavailable = True
    assert client.post("/search", json={"query": "dados"}, headers=headers["a"]).status_code == 503
    assert client.get("/graph", headers=headers["a"]).status_code == 200
    assert client.get("/connections", headers=headers["a"]).status_code == 200
    users._users[0] = replace(users._users[0], is_active=False)
    assert client.get("/graph", headers=headers["a"]).status_code == 401


def test_cors_preflight_and_error_responses(network):
    _, client, *_ = network
    result = client.options("/search", headers={"Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "authorization,content-type"})
    assert result.status_code == 200
    assert result.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
    assert "Authorization" in result.headers["Access-Control-Allow-Headers"]
    assert "Access-Control-Allow-Credentials" not in result.headers
    unauthorized = client.get("/graph", headers={"Origin": "http://localhost:5173"})
    assert unauthorized.status_code == 401
    assert unauthorized.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
    denied = client.options("/search", headers={"Origin": "http://other.example"})
    assert "Access-Control-Allow-Origin" not in denied.headers


def test_reindex_cli_idempotence_filters_and_failure(network):
    app, _, _, _, _, profiles, provider = network
    runner = app.test_cli_runner()
    result = runner.invoke(args=["reindex-profiles"])
    assert result.exit_code == 0 and "atuais: 3" in result.output
    assert runner.invoke(args=["reindex-profiles", "--entity-id", "e", "--user-id", "a"]).exit_code != 0
    provider.unavailable = True
    result = runner.invoke(args=["reindex-profiles", "--user-id", "a", "--force"])
    assert result.exit_code != 0 and "pendentes: 1" in result.output
    provider.unavailable = False
    assert runner.invoke(args=["reindex-profiles", "--user-id", "a"]).exit_code == 0


def test_registration_hook_runs_after_save_and_index_failure_preserves_user(network):
    app, client, headers, users, repository, profiles, provider = network
    # Testa o ponto de integração sem depender de envio SMTP real.
    from datetime import datetime, timedelta, timezone
    import secrets
    from modules.auth.domain.invite import Invite, token_hash
    from modules.auth.repositories.in_memory.repository import InMemoryInviteRepository
    from modules.auth.useCases.register.register import RegisterUseCase
    from modules.search.hooks import profile_saved

    invites = InMemoryInviteRepository(users, repository)
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    invites.save(Invite("i", "new@insper.edu.br", token_hash(token), "a", now, now + timedelta(days=1)))
    created = RegisterUseCase(users, invites).register("Nova", "new@insper.edu.br", "senha1234", token)
    profiles.profiles.append(NetworkProfile(created["id"], "Nova"))
    provider.unavailable = True
    profile_saved(app, created["id"])
    assert users.find_by_id(created["id"]) is not None
    assert app.extensions["index_profiles_use_case"].repository.all()[created["id"]]["status"] == "pending"
    app.extensions["profile_saved"] = Mock(side_effect=RuntimeError("failure"))
    profile_saved(app, created["id"])
    assert users.find_by_id(created["id"]) is not None
