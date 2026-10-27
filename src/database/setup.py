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
    PROFILE_VALIDATOR, PROJECT_VALIDATOR, ENTITY_VALIDATOR,
    PROFILE_INDEXES, PROJECT_INDEXES, ENTITY_INDEXES,
)

from modules.connections.repositories.mongo.schema import CONNECTION_INDEXES, CONNECTION_VALIDATOR
from modules.search.repositories.mongo.schema import EMBEDDING_VALIDATOR


def preparar_banco(db: Database[dict[str, Any]]) -> None:
    validators = {"users": USER_VALIDATOR, "invites": INVITE_VALIDATOR,
                  "connections": CONNECTION_VALIDATOR, "profile_embeddings": EMBEDDING_VALIDATOR,
                  "profiles": PROFILE_VALIDATOR, "research_projects": PROJECT_VALIDATOR, "entities": ENTITY_VALIDATOR}
    collections = ("users", "revoked_tokens", "invites", "connections", "entities", "research_projects", "profiles", "photo_cleanup", "profile_embeddings")
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
    db["connections"].create_indexes(CONNECTION_INDEXES)
    db["profiles"].create_indexes(PROFILE_INDEXES)
    db["research_projects"].create_indexes(PROJECT_INDEXES)
    db["entities"].create_indexes(ENTITY_INDEXES)
    from modules.auth.domain.profile import ENTITIES
    for entity in ENTITIES:
        db["entities"].update_one({"_id": entity["id"]}, {"$set": {"name": entity["name"]}}, upsert=True)
    print("Coleções, validações, índices e entidades preparados.")


def reset_test_data(db: Database[dict[str, Any]]) -> None:
    """Limpa exclusivamente as coleções de auth autorizadas pelo flag explícito."""
    for name in ("users", "profiles", "invites", "revoked_tokens", "entities", "research_projects",
                 "photo_cleanup", "profile_photos.files", "profile_photos.chunks"):
        db[name].delete_many({})


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepara o banco sem apagar dados nem criar contas.")
    parser.add_argument("--reset-test-data", action="store_true", help="Apaga os dados de teste das coleções auth e fotos antes de preparar")
    parser.add_argument("--cleanup-photos", action="store_true", help="Repete a remoção de fotos pendentes")
    args = parser.parse_args()
    load_dotenv()
    database = create_database(os.getenv("MONGO_URI"), os.getenv("MONGO_DB"))
    try:
        database.client.admin.command("ping")
        if args.reset_test_data:
            reset_test_data(database)
            print("Dados de teste de auth removidos; demais coleções preservadas.")
        preparar_banco(database)
        if args.cleanup_photos:
            from modules.auth.repositories.mongo.profiles import MongoProfileRepository, MongoPhotoStore
            from modules.auth.useCases.profile.profile import clean_photos
            cleaned = clean_photos(MongoProfileRepository(database), MongoPhotoStore(database))
            print(f"Fotos pendentes removidas: {cleaned}")
    finally:
        database.client.close()


if __name__ == "__main__":
    main()
