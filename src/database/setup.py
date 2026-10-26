"""Prepara coleções, validação e índices sem apagar dados ou criar contas."""

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
from modules.auth.repositories.mongo.schema import TOKEN_INDEXES, USER_INDEXES, USER_VALIDATOR


def preparar_banco(db: Database[dict[str, Any]]) -> None:
    colecoes_necessarias = (
        "users",
        "revoked_tokens",
        "invites",
        "connections",
        "entities",
        "research_projects",
    )
    colecoes_existentes = set(db.list_collection_names())

    for nome in colecoes_necessarias:
        if nome == "users":
            if nome in colecoes_existentes:
                db.command(
                    "collMod",
                    nome,
                    validator=USER_VALIDATOR,
                    validationLevel="strict",
                    validationAction="error",
                )
            else:
                db.create_collection(
                    nome,
                    validator=USER_VALIDATOR,
                    validationLevel="strict",
                    validationAction="error",
                )
                print(f"Coleção criada: {nome}")
        elif nome not in colecoes_existentes:
            db.create_collection(nome)
            print(f"Coleção criada: {nome}")

    db["users"].create_indexes(USER_INDEXES)
    db["revoked_tokens"].create_indexes(TOKEN_INDEXES)
    print("Validação e índices de autenticação preparados.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    load_dotenv()
    database = create_database(os.getenv("MONGO_URI"), os.getenv("MONGO_DB"))
    client = database.client
    try:
        client.admin.command("ping")
        preparar_banco(database)
        print("Preparação do banco concluída.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
