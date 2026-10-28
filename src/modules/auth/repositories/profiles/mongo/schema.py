from pymongo import IndexModel

VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "additionalProperties": False,
        "required": [
            "_id",
            "name",
            "course_id",
            "semester",
            "field_id",
            "bio",
            "photo_id",
            "entity_ids",
            "research_project_ids",
            "experiences_completed",
        ],
        "properties": {
            "_id": {"bsonType": "string", "minLength": 1},
            "name": {"bsonType": "string", "minLength": 1, "maxLength": 100},
            "course_id": {"enum": ["computer-science", "economics", "law"]},
            "semester": {"bsonType": "int", "minimum": 1, "maximum": 8},
            "field_id": {
                "enum": ["finance", "technology", "entrepreneurship", "cybersecurity"]
            },
            "bio": {"bsonType": "string", "minLength": 1, "maxLength": 500},
            "photo_id": {"bsonType": ["string", "null"]},
            "entity_ids": {
                "bsonType": "array",
                "uniqueItems": True,
                "items": {"bsonType": "string", "minLength": 1},
            },
            "research_project_ids": {
                "bsonType": "array",
                "uniqueItems": True,
                "items": {"bsonType": "string", "minLength": 1},
            },
            "experiences_completed": {"bsonType": "bool"},
            "type": {"enum": ["", "aluno", "alumni", "professor"]},
            "entry_year": {
                "bsonType": ["int", "null"],
                "minimum": 1900,
                "maximum": 2200,
            },
            "entry_semester": {"enum": [None, 1, 2]},
            "class_group": {"bsonType": "string", "maxLength": 150},
            "role": {"bsonType": "string", "maxLength": 150},
            "company": {"bsonType": "string", "maxLength": 150},
            "experiences": {
                "bsonType": "array",
                "items": {
                    "bsonType": "object",
                    "additionalProperties": False,
                    "required": [
                        "id",
                        "title",
                        "organization",
                        "type",
                        "start_date",
                        "end_date",
                        "description",
                    ],
                    "properties": {
                        "id": {"bsonType": "string", "minLength": 1},
                        "title": {
                            "bsonType": "string",
                            "minLength": 1,
                            "maxLength": 150,
                        },
                        "organization": {
                            "bsonType": "string",
                            "minLength": 1,
                            "maxLength": 150,
                        },
                        "type": {"bsonType": "string", "maxLength": 100},
                        "start_date": {"bsonType": "string", "minLength": 1},
                        "end_date": {"bsonType": ["string", "null"]},
                        "description": {"bsonType": "string", "maxLength": 2000},
                    },
                },
            },
            "entity_memberships": {
                "bsonType": "array",
                "items": {
                    "bsonType": "object",
                    "additionalProperties": False,
                    "required": ["id", "role", "start_date", "end_date", "entity_id"],
                    "properties": {
                        "id": {"bsonType": "string", "minLength": 1},
                        "role": {"bsonType": "string", "maxLength": 100},
                        "start_date": {"bsonType": "string", "minLength": 1},
                        "end_date": {"bsonType": ["string", "null"]},
                        "entity_id": {"bsonType": "string", "minLength": 1},
                    },
                },
            },
            "research_participations": {
                "bsonType": "array",
                "items": {
                    "bsonType": "object",
                    "additionalProperties": False,
                    "required": [
                        "id",
                        "role",
                        "start_date",
                        "end_date",
                        "project_id",
                        "advisor_user_id",
                        "status",
                    ],
                    "properties": {
                        "id": {"bsonType": "string", "minLength": 1},
                        "role": {"bsonType": "string", "maxLength": 100},
                        "start_date": {"bsonType": "string", "minLength": 1},
                        "end_date": {"bsonType": ["string", "null"]},
                        "project_id": {"bsonType": "string", "minLength": 1},
                        "advisor_user_id": {"bsonType": ["string", "null"]},
                        "status": {"enum": ["pending", "confirmed", "rejected"]},
                    },
                },
            },
        },
    }
}
INDEXES = [
    IndexModel("photo_id", sparse=True, name="profiles_photo"),
    IndexModel("research_participations.advisor_user_id", name="profiles_by_advisor"),
]
