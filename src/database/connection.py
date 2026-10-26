"""Cria um cliente MongoDB por aplicação, sem conexão durante o import."""

import os
from typing import Any

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database


def create_database(uri: str | None, name: str | None) -> Database[dict[str, Any]]:
    if not uri or not name:
        raise ValueError("MONGO_URI e MONGO_DB devem ser definidos no .env")
    client: MongoClient[dict[str, Any]] = MongoClient(
        uri, serverSelectionTimeoutMS=5000, connect=False, tz_aware=True
    )
    return client[name]


if __name__ == "__main__":
    load_dotenv()
    database = create_database(os.getenv("MONGO_URI"), os.getenv("MONGO_DB"))
    try:
        database.client.admin.command("ping")
        print("Conexão com o MongoDB estabelecida com sucesso.")
    finally:
        database.client.close()
