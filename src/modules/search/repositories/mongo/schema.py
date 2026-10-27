EMBEDDING_VALIDATOR = {"$jsonSchema": {
    "bsonType": "object",
    "required": ["_id", "model", "dimensions", "text_version", "source_hash", "status", "vector"],
    "properties": {
        "_id": {"bsonType": "string"},
        "model": {"bsonType": "string"},
        "dimensions": {"bsonType": "int"},
        "text_version": {"bsonType": "int"},
        "source_hash": {"bsonType": "string"},
        "status": {"enum": ["pending", "ready"]},
        "vector": {"bsonType": "array", "items": {"bsonType": "double"}},
    },
}}
