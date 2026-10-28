import secrets
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from io import BytesIO
from uuid import uuid4

import pytest
from PIL import Image

from app import create_app
from infra.config.application import compose
from infra.config.repositories import memory_repositories
from infra.config.settings import settings
from infra.database.memory import MemoryDatabase
from infra.email.contract import EmailDeliveryError
from infra.embeddings.contract import EmbeddingUnavailable
from infra.security.tokens.flask import FlaskTokenIssuer
from modules.auth.domain.invite import Invite, token_hash
from modules.auth.domain.profile import Profile, ResearchParticipation
from modules.auth.domain.research_project import ResearchProject
from modules.auth.domain.user import User
from modules.connections.domain.connection import Connection
from modules.search.domain.profile_text import TEXT_VERSION, source_hash
from modules.search.domain.vectors import normalized

PASSWORD = "senha-teste-123"
PROFILE = {
    "name": "Pessoa",
    "course_id": "computer-science",
    "semester": 2,
    "field_id": "technology",
    "bio": "Estudo computação",
}
PROJECT = {
    "title": "Pesquisa de dados",
    "description": "Dados e tecnologia",
    "advisor": "Professora",
    "field_id": "technology",
    "start_date": "2025-01-01",
    "end_date": None,
    "status": "in_progress",
}


class FakePasswords:
    def hash(self, password):
        return "test-hash:" + password

    def verify(self, password, password_hash):
        return password_hash == self.hash(password)


class FakeMailer:
    def __init__(self):
        self.messages = []
        self.fail = False

    def send_invite(self, email, link, expires_at):
        if self.fail:
            raise EmailDeliveryError("E-mail indisponível")
        self.messages.append((email, link, expires_at))


class FakeEmbeddings:
    model = "test"
    dimensions = 2

    def __init__(self):
        self.documents = 0
        self.queries = 0
        self.fail = False
        self.vectors = {}

    def document(self, text, title):
        self.documents += 1
        if self.fail:
            raise EmbeddingUnavailable("Provedor indisponível")
        return self.vectors.get(title, [1.0, 0.0])

    def query(self, text):
        self.queries += 1
        if self.fail:
            raise EmbeddingUnavailable("Provedor indisponível")
        return [1.0, 0.0]


def image_bytes(size=(20, 20), fmt="PNG"):
    output = BytesIO()
    Image.new("RGB", size, "red").save(output, format=fmt)
    return output.getvalue()


@pytest.fixture
def database():
    return MemoryDatabase()


@pytest.fixture
def repos(database):
    return memory_repositories(database)


@pytest.fixture
def passwords():
    return FakePasswords()


@pytest.fixture
def mailer():
    return FakeMailer()


@pytest.fixture
def embeddings():
    return FakeEmbeddings()


@pytest.fixture
def app(database, mailer, embeddings, passwords):
    config = {
        "TESTING": True,
        "JWT_SECRET_KEY": "tests-only-secret-at-least-32-bytes",
        "BOOTSTRAP_KEY": "bootstrap-tests-at-least-32-bytes",
        "FRONTEND_URL": "http://localhost:5173",
        "SEARCH_MIN_SCORE": 0.5,
        "GEMINI_TIMEOUT": 15,
        "GEMINI_API_KEY": None,
        "SMTP_PORT": 1025,
    }
    application = compose(
        settings(config),
        memory=database,
        mailer=mailer,
        provider=embeddings,
        hasher=passwords,
    )
    return create_app(config, application)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def create_user(repos, passwords):
    def create(identifier, **changes):
        user = User(
            identifier, f"{identifier}@insper.edu.br", passwords.hash(PASSWORD), True
        )
        profile = Profile(
            identifier,
            **{**PROFILE, "name": identifier.capitalize(), "type": "aluno", **changes},
        )
        repos.users.save(user, insert=True)
        repos.profiles.save(profile, insert=True)
        return user

    return create


@pytest.fixture
def ana(create_user):
    return create_user("ana")


@pytest.fixture
def auth_headers(app):
    def headers(user):
        with app.app_context():
            token = FlaskTokenIssuer().issue(user.id, user.auth_version)
        return {"Authorization": "Bearer " + token}

    return headers


@pytest.fixture
def invite(repos):
    def create(email="nova@insper.edu.br", creator=None):
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        item = Invite(
            str(uuid4()),
            email,
            token_hash(token),
            creator,
            now,
            now + timedelta(days=7),
        )
        repos.invites.save(item)
        return token, item

    return create


@pytest.fixture
def create_project(repos):
    def create(owner, identifier="project"):
        project = ResearchProject.create(owner.id, PROJECT, identifier)
        repos.projects.save(project, insert=True)
        return project

    return create


@pytest.fixture
def photo(repos, ana):
    content = image_bytes()
    repos.photos.put("photo-ana", content)
    repos.profiles.save(replace(repos.profiles.get(ana.id), photo_id="photo-ana"))
    return content


@pytest.fixture
def orientation(create_user, create_project, repos):
    student = create_user("student")
    advisor = create_user("advisor", type="professor")
    project = create_project(advisor)
    participation = ResearchParticipation(
        "participation", project.id, advisor.id, "Pesquisador", "2025-01-01", None
    )
    repos.profiles.save(
        replace(
            repos.profiles.get(student.id),
            research_project_ids=(project.id,),
            research_participations=(participation,),
        )
    )
    return student, advisor, participation


@pytest.fixture
def search_people(create_user, repos):
    people = {
        key: create_user(key) for key in ("origin", "near", "middle", "far", "isolated")
    }
    for first, second in (("origin", "near"), ("near", "middle"), ("middle", "far")):
        repos.connections.save(
            Connection.create(first, second, accepted=True), insert=True
        )
    profiles = repos.network.list_active()
    catalogs = repos.network.catalogs(profiles)
    vectors = {
        "origin": [1.0, 0.0],
        "near": [0.6, 0.8],
        "middle": [0.8, 0.6],
        "far": [1.0, 0.0],
        "isolated": [1.0, 0.0],
    }
    for profile in profiles:
        repos.embeddings.save(
            {
                "_id": profile.id,
                "model": "test",
                "dimensions": 2,
                "text_version": TEXT_VERSION,
                "source_hash": source_hash(profile, catalogs),
                "status": "ready",
                "vector": normalized(vectors[profile.id], 2),
            }
        )
    return people
