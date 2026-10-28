from infra.database.registry import COLLECTIONS, SCHEMAS
from modules.auth.domain.catalogs import ENTITIES


def prepare_database(database):
    existing = set(database.list_collection_names())
    for name, schema in SCHEMAS.items():
        options = {
            "validator": schema.VALIDATOR,
            "validationLevel": "strict",
            "validationAction": "error",
        }
        if name in existing:
            database.command("collMod", name, **options)
        else:
            database.create_collection(name, **options)
        if schema.INDEXES:
            database[name].create_indexes(schema.INDEXES)
    for entity in ENTITIES:
        database.entities.update_one(
            {"_id": entity["id"]},
            {"$setOnInsert": {"name": entity["name"]}},
            upsert=True,
        )


def reset_development_data(database):
    for name in COLLECTIONS:
        database[name].delete_many({})
    prepare_database(database)
