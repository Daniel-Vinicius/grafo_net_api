from pymongo import IndexModel

VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "additionalProperties": False,
        "required": ["_id", "expires_at"],
        "properties": {
            "_id": {"bsonType": "string", "minLength": 1},
            "expires_at": {"bsonType": "date"},
        },
    }
}
INDEXES = [IndexModel("expires_at", expireAfterSeconds=0, name="revoked_tokens_expiry")]
