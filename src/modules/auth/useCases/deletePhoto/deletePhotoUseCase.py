from dataclasses import replace

from infra.database.contract import UnitOfWork
from modules.auth.policies import require_profile
from modules.auth.useCases.cleanupPhotos.cleanupPhotosUseCase import (
    CleanupPhotosUseCase,
)


class DeletePhotoUseCase:
    def __init__(self, uow: UnitOfWork, cleanup: CleanupPhotosUseCase):
        self.uow = uow
        self.cleanup = cleanup

    def execute(self, identifier):
        def remove(repos):
            profile = require_profile(repos, identifier)
            repos.profiles.save(replace(profile, photo_id=None))
            if profile.photo_id:
                repos.cleanup.queue(profile.photo_id)

        self.uow.run(remove)
        self.cleanup.execute()
