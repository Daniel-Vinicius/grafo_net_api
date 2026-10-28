from infra.database.context import Repositories
from modules.auth.domain.errors import NotFoundError
from modules.auth.policies import require_profile


class GetPhotoUseCase:
    def __init__(self, repos: Repositories):
        self.repos = repos

    def execute(self, identifier):
        profile = require_profile(self.repos, identifier)
        content = self.repos.photos.get(profile.photo_id) if profile.photo_id else None
        if content is None or profile.photo_id is None:
            raise NotFoundError("Foto não encontrada")
        return profile.photo_id, content
