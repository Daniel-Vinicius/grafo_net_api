VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "additionalProperties": False,
        "required": [
            "_id",
            "model",
            "dimensions",
            "text_version",
            "source_hash",
            "status",
            "vector",
            "updated_at",
        ],
        "properties": {
            "_id": {"bsonType": "string", "minLength": 1},
            "model": {"bsonType": "string", "minLength": 1},
            "dimensions": {"bsonType": "int"},
            "text_version": {"bsonType": "int"},
            "source_hash": {"bsonType": "string", "minLength": 1},
            "status": {"enum": ["pending", "ready"]},
            "vector": {"bsonType": "array", "items": {"bsonType": ["double", "int"]}},
            "updated_at": {"bsonType": "date"},
        },
    }
}
INDEXES = []
