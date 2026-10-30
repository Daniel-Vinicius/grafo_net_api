from pymongo import IndexModel

VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "additionalProperties": False,
        "required": [
            "_id",
            "email",
            "token_hash",
            "created_by",
            "created_at",
            "expires_at",
            "used_at",
        ],
        "properties": {
            "_id": {"bsonType": "string", "minLength": 1},
            "email": {"bsonType": "string", "minLength": 1},
            "token_hash": {"bsonType": "string", "minLength": 1},
            "created_by": {"bsonType": ["string", "null"]},
            "created_at": {"bsonType": "date"},
            "expires_at": {"bsonType": "date"},
            "used_at": {"bsonType": ["date", "null"]},
        },
    }
}
INDEXES = [IndexModel("token_hash", unique=True, name="invites_token_hash_unique")]
