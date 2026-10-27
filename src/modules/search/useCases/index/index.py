from datetime import datetime, timezone
from typing import Any

from modules.graph.domain.catalogs import Catalogs
from modules.auth.domain.profile import Profile
from modules.graph.repositories.contract import ProfileRepository
from modules.search.domain.profile_text import TEXT_VERSION, searchable_text, source_hash
from modules.search.embeddings import EmbeddingProvider, EmbeddingUnavailable, normalized
from modules.search.repositories.contract import EmbeddingRepository


class IndexProfilesUseCase:
    def __init__(self, profiles: ProfileRepository, repository: EmbeddingRepository, provider: EmbeddingProvider):
        self.profiles, self.repository, self.provider = profiles, repository, provider

    def current(self, record: dict[str, Any] | None, profile: Profile, catalogs: Catalogs) -> bool:
        return bool(record and record.get("status") == "ready"
                    and record.get("model") == self.provider.model
                    and record.get("dimensions") == self.provider.dimensions
                    and record.get("text_version") == TEXT_VERSION
                    and record.get("source_hash") == source_hash(profile, catalogs))

    def refresh(self, user_id: str | None = None, force: bool = False,
                reference: tuple[str, str] | None = None) -> dict[str, int]:
        profiles, catalogs, records = self.profiles.list_active(), self.profiles.catalogs(), self.repository.all()
        counts = {"indexed": 0, "unchanged": 0, "pending": 0}
        for profile in profiles:
            if user_id is not None and profile.id != user_id:
                continue
            if reference:
                kind, identifier = reference
                links = profile.entity_ids if kind == "entity" else profile.research_project_ids
                if identifier not in links:
                    continue
            if not force and self.current(records.get(profile.id), profile, catalogs):
                counts["unchanged"] += 1
                continue
            record = {"_id": profile.id, "model": self.provider.model,
                      "dimensions": self.provider.dimensions, "text_version": TEXT_VERSION,
                      "source_hash": source_hash(profile, catalogs), "status": "pending", "vector": [],
                      "updated_at": datetime.now(timezone.utc)}
            self.repository.save(record)
            try:
                vector = normalized(self.provider.document(searchable_text(profile, catalogs), profile.name),
                                    self.provider.dimensions)
            except EmbeddingUnavailable:
                counts["pending"] += 1
                continue
            self.repository.save({**record, "status": "ready", "vector": vector})
            counts["indexed"] += 1
        return counts

