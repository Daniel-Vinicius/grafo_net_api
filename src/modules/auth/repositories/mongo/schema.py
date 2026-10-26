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
