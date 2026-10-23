"""Próxima tarefa: configurar um MongoClient compartilhado por aplicação.

Receber URI e nome do banco pelo .env. Entregar Database aos repositories.
"""
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError
load_dotenv()

MONGO_URI = os.environ.get("MONGO_URI")
MONGO_DB = os.environ.get("MONGO_DB")

if not MONGO_URI or not MONGO_DB:
    raise ValueError("MONGO_URI e MONGO_DB devem ser definidos no .env")

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
database: Database = client[MONGO_DB]

def verificar_conexao() -> None:
    client.admin.command("ping")






if __name__ == "__main__":
    print(f"MONGO_URI: {MONGO_URI}")
    print(f"MONGO_DB: {MONGO_DB}")

    try:
        verificar_conexao()
        print("Conexão com o MongoDB estabelecida com sucesso.")
    except PyMongoError as e:
        print(f"Erro ao conectar ao MongoDB: {e}")

