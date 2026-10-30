from pymongo import IndexModel

VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "additionalProperties": False,
        "required": ["_id", "name"],
        "properties": {
            "_id": {"bsonType": "string", "minLength": 1},
            "name": {"bsonType": "string", "minLength": 1, "maxLength": 100},
        },
    }
}
INDEXES = [IndexModel("name", unique=True, name="entities_name_unique")]
