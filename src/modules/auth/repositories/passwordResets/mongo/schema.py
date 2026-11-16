from pymongo import IndexModel

VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "additionalProperties": False,
        "required": [
            "_id",
            "user_id",
            "token_hash",
            "created_at",
            "expires_at",
        ],
        "properties": {
            "_id": {"bsonType": "string", "minLength": 1},
            "user_id": {"bsonType": "string", "minLength": 1},
            "token_hash": {"bsonType": "string", "minLength": 1},
            "created_at": {"bsonType": "date"},
            "expires_at": {"bsonType": "date"},
        },
    }
}
INDEXES = [
    IndexModel("token_hash", unique=True, name="password_resets_token_hash_unique"),
    IndexModel("user_id", name="password_resets_by_user"),
    IndexModel("expires_at", expireAfterSeconds=0, name="password_resets_expiry"),
]
