from contextlib import contextmanager
from typing import Any, Callable, TypeVar

from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError

from infra.database.contract import DuplicateRecordError
from infra.errors import UnavailableError

T = TypeVar("T")


def database_connection(uri: str, name: str):
    if not uri or not name:
        raise ValueError("Configure MONGO_URI e MONGO_DB")
    client: MongoClient[dict[str, Any]] = MongoClient(
        uri, connect=False, tz_aware=True, serverSelectionTimeoutMS=5000
    )
    return client[name]


@contextmanager
def mongo_errors(session=None):
    """Translate errors outside transactions; keep driver errors available for retry."""
    try:
        yield
    except DuplicateKeyError:
        if session is not None:
            raise
        raise DuplicateRecordError("Registro duplicado") from None
    except PyMongoError:
        if session is not None:
            raise
        raise UnavailableError("Banco indisponível") from None


def translate(callback: Callable[[], T]) -> T:
    with mongo_errors():
        return callback()
