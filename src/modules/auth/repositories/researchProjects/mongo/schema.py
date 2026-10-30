from pymongo import IndexModel

VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "additionalProperties": False,
        "required": [
            "_id",
            "creator_id",
            "title",
            "description",
            "advisor",
            "field_id",
            "start_date",
            "end_date",
            "status",
        ],
        "properties": {
            "_id": {"bsonType": "string", "minLength": 1},
            "creator_id": {"bsonType": ["string", "null"]},
            "title": {"bsonType": "string", "minLength": 1, "maxLength": 150},
            "description": {"bsonType": "string", "minLength": 1, "maxLength": 2000},
            "advisor": {"bsonType": "string", "minLength": 1, "maxLength": 100},
            "field_id": {
                "enum": ["finance", "technology", "entrepreneurship", "cybersecurity"]
            },
            "start_date": {"bsonType": "string", "minLength": 1},
            "end_date": {"bsonType": ["string", "null"]},
            "status": {"enum": ["planned", "in_progress", "completed", "cancelled"]},
        },
    }
}
INDEXES = [IndexModel("creator_id", name="projects_creator")]
