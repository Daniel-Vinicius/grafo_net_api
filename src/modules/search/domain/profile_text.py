from dataclasses import asdict
import hashlib
import json

from modules.graph.domain.profile import Catalogs, NetworkProfile


TEXT_VERSION = 1


def searchable_text(profile: NetworkProfile, catalogs: Catalogs) -> str:
    """Whitelist explícita: não incorporar credenciais, foto ou campos futuros do perfil."""
    data = asdict(profile)
    data.pop("id")
    data.pop("photo_url")
    # Dados de participação privados/operacionais não entram no embedding.
    data["experiences"] = [{key: item.get(key) for key in
                            ("title", "organization", "type", "start_date", "end_date", "description")}
                           for item in profile.experiences]
    data["entity_memberships"] = [{
        **catalogs.entities.get(str(item.get("entity_id", "")), {}),
        **{key: item.get(key) for key in ("role", "start_date", "end_date")},
    } for item in profile.entity_memberships]
    data["research_participations"] = [{
        **catalogs.projects.get(str(item.get("project_id", "")), {}),
        **{key: item.get(key) for key in ("role", "start_date", "end_date")},
    } for item in profile.research_participations]
    return json.dumps(data, ensure_ascii=False, sort_keys=True, default=str)


def source_hash(profile: NetworkProfile, catalogs: Catalogs) -> str:
    return hashlib.sha256(searchable_text(profile, catalogs).encode()).hexdigest()

