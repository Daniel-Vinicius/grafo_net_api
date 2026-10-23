"""Próxima tarefa: comando explícito para preparar as coleções e índices.

Importar schemas dos módulos, criar coleções ausentes e índices declarados.
Não apagar dados. 
"""

from pymongo.database import Database

from .connection import client, database


def preparar_banco(db: Database) -> None:
    colecoes_necessarias = (
        "users",
        "invites",
        "connections",
        "entities",
        "research_projects",
    )


    colecoes_existentes = set(db.list_collection_names())

    for nome in colecoes_necessarias:
        if nome not in colecoes_existentes:
            db.create_collection(nome)
            print(f"Coleção criada: {nome}")

    db["users"].create_index(
        "email_normalized",
        unique=True,
        name="users_email_normalized_unique",
    )

    print("Índice único de email preparado.")


if __name__ == "__main__":
    try:
        client.admin.command("ping")
        preparar_banco(database)
        print("Preparação do banco concluída.")
    finally:
        client.close()