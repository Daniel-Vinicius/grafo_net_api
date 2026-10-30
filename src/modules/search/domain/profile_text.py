import hashlib
import json
from dataclasses import asdict

from modules.auth.domain.profile import Profile
from modules.graph.domain.catalogs import Catalogs

TEXT_VERSION = 4


def searchable_text(profile: Profile, catalogs: Catalogs) -> str:
    data = {
        key: getattr(profile, key)
        for key in (
            "name",
            "type",
            "course",
            "semester",
            "field",
            "bio",
            "entry_year",
            "entry_semester",
            "class_group",
            "role",
            "company",
        )
    }
    data["experiences"] = [
        {key: value for key, value in asdict(item).items() if key != "id"}
        for item in profile.experiences
    ]
    for name, identifiers, details, reference, catalog, keys in (
        (
            "entities",
            profile.entity_ids,
            profile.entity_memberships,
            "entity_id",
            catalogs.entities,
            ("name", "description"),
        ),
        (
            "projects",
            profile.research_project_ids,
            profile.research_participations,
            "project_id",
            catalogs.projects,
            ("title", "description"),
        ),
    ):
        data[name] = []
        for identifier in sorted(identifiers):
            records = [
                item for item in details if getattr(item, reference) == identifier
            ]
            data[name].append(
                {
                    **{key: catalog.get(identifier, {}).get(key) for key in keys},
                    "participations": [
                        {
                            key: getattr(item, key)
                            for key in ("role", "start_date", "end_date")
                        }
                        for item in records
                    ],
                }
            )
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


def source_hash(profile: Profile, catalogs: Catalogs) -> str:
    return hashlib.sha256(searchable_text(profile, catalogs).encode()).hexdigest()


def current_embedding(record, profile, catalogs, provider):
    return bool(
        record
        and record.get("status") == "ready"
        and record.get("model") == provider.model
        and record.get("dimensions") == provider.dimensions
        and record.get("text_version") == TEXT_VERSION
        and record.get("source_hash") == source_hash(profile, catalogs)
    )
