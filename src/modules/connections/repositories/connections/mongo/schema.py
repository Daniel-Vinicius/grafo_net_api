from pymongo import IndexModel

VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "additionalProperties": False,
        "required": [
            "_id",
            "user_a_id",
            "user_b_id",
            "requested_by",
            "status",
            "created_at",
            "accepted_at",
        ],
        "properties": {
            "_id": {"bsonType": "string", "minLength": 1},
            "user_a_id": {"bsonType": "string", "minLength": 1},
            "user_b_id": {"bsonType": "string", "minLength": 1},
            "requested_by": {"bsonType": "string", "minLength": 1},
            "status": {"enum": ["pending", "accepted"]},
            "created_at": {"bsonType": "date"},
            "accepted_at": {"bsonType": ["date", "null"]},
        },
    }
}
INDEXES = [
    IndexModel(
        [("user_a_id", 1), ("user_b_id", 1)],
        unique=True,
        name="connections_pair_unique",
    ),
    IndexModel([("user_a_id", 1), ("status", 1)], name="connections_by_a"),
    IndexModel([("user_b_id", 1), ("status", 1)], name="connections_by_b"),
]
