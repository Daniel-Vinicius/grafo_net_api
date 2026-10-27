import hashlib
import json

from modules.graph.domain.catalogs import Catalogs
from modules.auth.domain.profile import Profile


TEXT_VERSION = 3


def searchable_text(profile: Profile, catalogs: Catalogs) -> str:
    """Whitelist explícita: não incorporar credenciais, foto ou campos futuros do perfil."""
    data = {key: getattr(profile, key) for key in (
        "name", "type", "course", "semester", "field", "bio", "entry_year",
        "entry_semester", "class_group", "role", "company",
    )}
    data["experiences"] = [{key: item.get(key) for key in
                            ("title", "organization", "type", "start_date", "end_date", "description")}
                           for item in profile.experiences]
    for output, ids, details, id_key, catalog, allowed in (
        ("entity_memberships", profile.entity_ids, profile.entity_memberships, "entity_id",
         catalogs.entities, ("name", "description")),
        ("research_participations", profile.research_project_ids, profile.research_participations,
         "project_id", catalogs.projects, ("title", "theme", "description")),
    ):
        data[output] = []
        for identifier in sorted(ids):
            participations = [item for item in details if item.get(id_key) == identifier] or [{}]
            for item in participations:
                data[output].append({
                    **{key: catalog.get(identifier, {}).get(key) for key in allowed},
                    **{key: item.get(key) for key in ("role", "start_date", "end_date")},
                })
    return json.dumps(data, ensure_ascii=False, sort_keys=True, default=str)


def source_hash(profile: Profile, catalogs: Catalogs) -> str:
    return hashlib.sha256(searchable_text(profile, catalogs).encode()).hexdigest()

