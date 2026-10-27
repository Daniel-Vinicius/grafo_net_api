from pymongo import IndexModel


CONNECTION_INDEXES = [
    IndexModel([("user_a_id", 1), ("user_b_id", 1)], unique=True, name="connections_pair_unique"),
    IndexModel([("user_a_id", 1), ("status", 1)], name="connections_by_a"),
    IndexModel([("user_b_id", 1), ("status", 1)], name="connections_by_b"),
]

CONNECTION_VALIDATOR = {"$jsonSchema": {
    "bsonType": "object",
    "required": ["_id", "user_a_id", "user_b_id", "requested_by", "status", "created_at"],
    "properties": {
        **{key: {"bsonType": "string", "minLength": 1}
           for key in ("_id", "user_a_id", "user_b_id", "requested_by")},
        "status": {"enum": ["pending", "accepted"]},
        "created_at": {"bsonType": "date"},
        "accepted_at": {"bsonType": ["date", "null"]},
    },
}}
