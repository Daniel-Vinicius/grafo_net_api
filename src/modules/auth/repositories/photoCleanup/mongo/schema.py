VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "additionalProperties": False,
        "required": ["_id", "ready_at"],
        "properties": {
            "_id": {"bsonType": "string", "minLength": 1},
            "ready_at": {"bsonType": "date"},
        },
    }
}
INDEXES = []
