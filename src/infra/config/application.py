from dataclasses import dataclass
from typing import Any, Callable

from infra.config.actions import build_actions
from infra.config.repositories import memory_repositories, mongo_repositories
from infra.database.context import Repositories
from infra.database.contract import UnitOfWork
from infra.database.mongo import database_connection
from infra.database.transactions import InMemoryUnitOfWork, MongoUnitOfWork
from infra.email.smtp import SMTPEmailSender
from infra.embeddings.gemini import GeminiEmbeddings
from infra.http.contract import Actions
from infra.images.pillow import PillowImageProcessor
from infra.security.passwords.bcrypt import BcryptPasswordHasher


@dataclass
class Application:
    repositories: Repositories
    transactions: UnitOfWork
    actions: Actions
    close: Callable[[], None]
    database: Any


def compose(
    config, *, memory=None, mailer=None, provider=None, hasher=None, images=None
):
    uow: UnitOfWork
    database: Any
    if memory is not None:
        factory = lambda: memory_repositories(memory)
        uow = InMemoryUnitOfWork(memory, factory)
        close = lambda: None
        database = memory
    else:
        database = database_connection(config["MONGO_URI"], config["MONGO_DB"])
        factory = lambda session=None: mongo_repositories(database, session)
        uow = MongoUnitOfWork(database, factory)
        close = database.client.close
    repos = factory()
    hasher = hasher or BcryptPasswordHasher()
    mailer = mailer or SMTPEmailSender(
        config["SMTP_HOST"],
        config["SMTP_PORT"],
        config["SMTP_FROM"],
        config["SMTP_USERNAME"],
        config["SMTP_PASSWORD"],
        config["SMTP_USE_TLS"],
    )
    provider = provider or GeminiEmbeddings(
        config["GEMINI_API_KEY"], config["GEMINI_TIMEOUT"]
    )
    actions = build_actions(
        repos,
        uow,
        hasher,
        images or PillowImageProcessor(),
        mailer,
        provider,
        config["FRONTEND_URL"],
        config["BOOTSTRAP_KEY"],
        config["SEARCH_MIN_SCORE"],
    )
    return Application(repos, uow, actions, close, database)
