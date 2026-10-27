from unittest.mock import MagicMock

from modules.graph.repositories.mongo.repository import MongoProfileRepository
from modules.graph.domain.catalogs import Catalogs
from modules.search.domain.profile_text import searchable_text


def test_public_profile_projection_and_no_credentials_in_search_text():
    database = MagicMock()
    users, profiles = MagicMock(), MagicMock()
    database.__getitem__.side_effect = lambda key: users if key == "users" else profiles
    users.find.return_value = [{"_id": "person"}]
    profiles.find.return_value = [{
        "_id": "person", "name": "Ana", "course_id": "computer-science", "semester": 3,
        "field_id": "technology", "bio": "Dados", "entity_ids": ["insper-code"],
        "research_project_ids": ["research"], "email": "private@insper.edu.br",
        "password_hash": "secret", "photo_id": "private-photo", "private_notes": "hidden",
    }]
    profile = MongoProfileRepository(database).list_active()[0]
    users.find.assert_called_once_with({"is_active": True}, {"_id": 1})
    query, projection = profiles.find.call_args.args
    assert query == {"_id": {"$in": ["person"]}}
    assert not {"email", "password_hash"} & projection.keys()
    text = searchable_text(profile, Catalogs(entities={"insper-code": {"name": "Insper Code"}}, projects={"research": {"title": "Pesquisa exemplo"}}))
    assert all(value in text for value in ("Dados", "Computa", "Tecnologia", "Insper Code", "Pesquisa exemplo"))
    assert not any(value in text for value in ("private@", "secret", "private-photo", "hidden"))
    assert profile.semester == 3
    assert set(profile.to_network_public()) == {"id", "name", "type", "course", "bio", "role", "company", "photo_url"}


def test_missing_profile_excluded_and_logged(caplog):
    database = MagicMock()
    users, profiles = MagicMock(), MagicMock()
    database.__getitem__.side_effect = lambda key: users if key == "users" else profiles
    users.find.return_value = [{"_id": "missing"}]
    profiles.find.return_value = []
    assert MongoProfileRepository(database).list_active() == []
    assert "missing" in caplog.text and "excluded" in caplog.text
