from pymongo import IndexModel

VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "additionalProperties": False,
        "required": ["_id", "email", "password_hash", "is_active", "auth_version"],
        "properties": {
            "_id": {"bsonType": "string", "minLength": 1},
            "email": {"bsonType": "string", "minLength": 1},
            "password_hash": {
                "bsonType": "string",
                "pattern": r"^\$2[aby]\$(0[4-9]|[12][0-9]|3[01])\$[./A-Za-z0-9]{53}$",
            },
            "is_active": {"bsonType": "bool"},
            "auth_version": {"bsonType": "int", "minimum": 0},
            "network_version": {"bsonType": "int", "minimum": 0},
        },
    }
}
INDEXES = [IndexModel("email", unique=True, name="users_email_unique")]
