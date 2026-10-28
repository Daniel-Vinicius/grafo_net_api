from datetime import datetime, timezone

from infra.database.context import Repositories
from infra.embeddings.contract import EmbeddingProvider, EmbeddingUnavailable
from modules.auth.domain.errors import ValidationError
from modules.search.domain.profile_text import (
    TEXT_VERSION,
    current_embedding,
    searchable_text,
    source_hash,
)
from modules.search.domain.vectors import normalized


class IndexProfilesUseCase:
    def __init__(self, repos: Repositories, provider: EmbeddingProvider):
        self.repos = repos
        self.provider = provider

    def execute(self, user_id=None, reference=None, force=False):
        profiles = (
            ([profile] if (profile := self.repos.network.get_active(user_id)) else [])
            if user_id
            else (
                self.repos.network.by_reference(*reference)
                if reference
                else self.repos.network.list_active()
            )
        )
        catalogs = self.repos.network.catalogs(profiles)
        records = self.repos.embeddings.get_many([profile.id for profile in profiles])
        counts = {"indexed": 0, "unchanged": 0, "pending": 0}
        for profile in profiles:
            if not force and current_embedding(
                records.get(profile.id), profile, catalogs, self.provider
            ):
                counts["unchanged"] += 1
                continue
            record = {
                "_id": profile.id,
                "model": self.provider.model,
                "dimensions": self.provider.dimensions,
                "text_version": TEXT_VERSION,
                "source_hash": source_hash(profile, catalogs),
                "status": "pending",
                "vector": [],
                "updated_at": datetime.now(timezone.utc),
            }
            self.repos.embeddings.save(record)
            try:
                vector = normalized(
                    self.provider.document(
                        searchable_text(profile, catalogs), profile.name
                    ),
                    self.provider.dimensions,
                )
            except EmbeddingUnavailable, ValidationError:
                counts["pending"] += 1
                continue
            self.repos.embeddings.save({**record, "status": "ready", "vector": vector})
            counts["indexed"] += 1
        return counts
