"""Validação de persistência e índices da coleção users.

O serviço continua responsável por normalizar o e-mail e gerar bcrypt.
O schema não comprova posse do endereço nem vínculo institucional.
"""

from typing import Any

from pymongo import IndexModel


USER_VALIDATOR: dict[str, Any] = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["_id", "email", "password_hash", "is_active"],
        "properties": {
            "_id": {"bsonType": ["objectId", "string"], "minLength": 1},
            "email": {"bsonType": "string", "minLength": 1},
            "password_hash": {
                "bsonType": "string",
                "pattern": r"^\$2[aby]\$(0[4-9]|[12][0-9]|3[01])\$[./A-Za-z0-9]{53}$",
                "description": "Hash bcrypt em texto; nunca a senha original.",
            },
            "is_active": {"bsonType": "bool"},
            "profile": {
                "bsonType": "object",
                "required": ["name"],
                "properties": {"name": {"bsonType": "string", "minLength": 1, "maxLength": 100}},
            },
        },
    }
}

USER_INDEXES = [
    IndexModel(
        "email",
        unique=True,
        name="users_email_unique",
    ),
]


TOKEN_INDEXES = [
    IndexModel("expires_at", expireAfterSeconds=0, name="revoked_tokens_expiry"),
]


INVITE_VALIDATOR: dict[str, Any] = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["_id", "email", "token_hash", "created_by", "created_at", "expires_at", "used_at"],
        "properties": {
            "_id": {"bsonType": "string"},
            "email": {"bsonType": "string", "minLength": 1},
            "token_hash": {"bsonType": "string", "pattern": "^[a-f0-9]{64}$"},
            "created_by": {"bsonType": ["string", "null"]},
            "created_at": {"bsonType": "date"},
            "expires_at": {"bsonType": "date"},
            "used_at": {"bsonType": ["date", "null"]},
        },
    },
}

INVITE_INDEXES = [IndexModel("token_hash", unique=True, name="invites_token_hash_unique")]

# O perfil deixa de ser embutido no documento de autenticação.
USER_VALIDATOR["$jsonSchema"]["properties"].pop("profile", None)
USER_VALIDATOR["$jsonSchema"]["properties"]["auth_version"] = {"bsonType": "int", "minimum": 0}
USER_VALIDATOR["$jsonSchema"]["required"].append("auth_version")
USER_VALIDATOR["$jsonSchema"]["additionalProperties"] = False

from modules.auth.domain.profile import COURSES, FIELDS, STATUSES


def string(maximum: int | None = None) -> dict:
    result = {"bsonType": "string", "minLength": 1}
    if maximum:
        result["maxLength"] = maximum
    return result


PROFILE_VALIDATOR = {"$jsonSchema": {
    "bsonType": "object", "additionalProperties": False,
    "required": ["_id", "name", "course_id", "semester", "field_id", "bio", "photo_id",
                 "entity_ids", "research_project_ids", "experiences_completed"],
    "properties": {
        "_id": string(), "name": string(100), "bio": string(500),
        "course_id": {"enum": [item["id"] for item in COURSES]},
        "field_id": {"enum": [item["id"] for item in FIELDS]},
        "semester": {"bsonType": "int", "minimum": 1, "maximum": 8},
        "photo_id": {"bsonType": ["string", "null"]},
        "entity_ids": {"bsonType": "array", "uniqueItems": True, "items": string()},
        "research_project_ids": {"bsonType": "array", "uniqueItems": True, "items": string()},
        "experiences_completed": {"bsonType": "bool"},
    },
}}
PROJECT_VALIDATOR = {"$jsonSchema": {
    "bsonType": "object", "additionalProperties": False,
    "required": ["_id", "creator_id", "title", "description", "advisor", "field_id", "start_date", "end_date", "status"],
    "properties": {
        "_id": string(), "creator_id": {"bsonType": ["string", "null"]},
        "title": string(150), "description": string(2000), "advisor": string(100),
        "field_id": {"enum": [item["id"] for item in FIELDS]},
        "start_date": {"bsonType": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
        "end_date": {"bsonType": ["string", "null"], "pattern": r"^\d{4}-\d{2}-\d{2}$"},
        "status": {"enum": STATUSES},
    },
}}
ENTITY_VALIDATOR = {"$jsonSchema": {
    "bsonType": "object", "required": ["_id", "name"], "additionalProperties": False,
    "properties": {"_id": string(), "name": string(100)},
}}
PROFILE_INDEXES = [IndexModel("photo_id", sparse=True, name="profiles_photo")]
PROJECT_INDEXES = [IndexModel("creator_id", name="projects_creator")]
ENTITY_INDEXES = [IndexModel("name", unique=True, name="entities_name_unique")]
