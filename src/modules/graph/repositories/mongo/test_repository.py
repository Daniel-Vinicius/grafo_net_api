from unittest.mock import MagicMock

from modules.graph.repositories.mongo.repository import MongoProfileRepository
from modules.search.domain.profile_text import searchable_text


def test_public_profile_projection_and_no_credentials_in_search_text():
    database = MagicMock()
    database.__getitem__.return_value.find.return_value = [{
        "_id": "person", "email": "private@insper.edu.br", "password_hash": "secret",
        "profile": {"name": "Ana", "photo_url": "private-photo", "private_notes": "hidden",
                    "experiences": [{"title": "Dados", "private_notes": "private-experience"}]},
    }]
    reader = MongoProfileRepository(database)
    profile = reader.list_active()[0]
    query, projection = database.__getitem__.return_value.find.call_args.args
    assert query == {"is_active": True}
    assert "email" not in projection and "password_hash" not in projection
    from modules.graph.domain.profile import Catalogs
    text = searchable_text(profile, Catalogs())
    assert "Dados" in text
    assert not any(value in text for value in ("private@", "secret", "private-photo", "hidden", "private-experience"))
    assert set(profile.public()) == {"id", "name", "type", "course", "bio", "role", "company", "photo_url"}


def test_null_or_missing_profile_remains_a_graph_vertex():
    assert MongoProfileRepository.from_document({"_id": "id", "profile": None}).name == "Perfil"
