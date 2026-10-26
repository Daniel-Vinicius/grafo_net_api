import argparse
import os
from pathlib import Path
import sys
from typing import Any

from dotenv import load_dotenv
from pymongo.database import Database

# A execução direta precisa incluir src para resolver os imports do projeto.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database.connection import create_database
from modules.auth.repositories.mongo.schema import (
    INVITE_INDEXES, INVITE_VALIDATOR, TOKEN_INDEXES, USER_INDEXES, USER_VALIDATOR,
)


def preparar_banco(db: Database[dict[str, Any]]) -> None:
    validators = {"users": USER_VALIDATOR, "invites": INVITE_VALIDATOR}
    collections = ("users", "revoked_tokens", "invites", "connections", "entities", "research_projects")
    existing = set(db.list_collection_names())
    for name in collections:
        if name in validators:
            options = {"validator": validators[name], "validationLevel": "strict", "validationAction": "error"}
            if name in existing:
                db.command("collMod", name, **options)
            else:
                db.create_collection(name, **options)
        elif name not in existing:
            db.create_collection(name)
    db["users"].create_indexes(USER_INDEXES)
    db["invites"].create_indexes(INVITE_INDEXES)
    db["revoked_tokens"].create_indexes(TOKEN_INDEXES)
    print("Coleções, validações e índices preparados.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepara o banco sem apagar dados nem criar contas.")
    parser.parse_args()
    load_dotenv()
    database = create_database(os.getenv("MONGO_URI"), os.getenv("MONGO_DB"))
    try:
        database.client.admin.command("ping")
        preparar_banco(database)
    finally:
        database.client.close()


if __name__ == "__main__":
    main()
