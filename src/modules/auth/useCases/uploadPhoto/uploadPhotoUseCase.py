from dataclasses import replace
from uuid import uuid4

from infra.database.context import Repositories
from infra.database.contract import UnitOfWork
from infra.errors import UnavailableError
from infra.images.contract import ImageProcessor
from modules.auth.policies import require_profile
from modules.auth.useCases.cleanupPhotos.cleanupPhotosUseCase import (
    CleanupPhotosUseCase,
)


class UploadPhotoUseCase:
    def __init__(
        self,
        repos: Repositories,
        uow: UnitOfWork,
        images: ImageProcessor,
        cleanup: CleanupPhotosUseCase,
    ):
        self.repos = repos
        self.uow = uow
        self.images = images
        self.cleanup = cleanup

    def execute(self, identifier, content):
        require_profile(self.repos, identifier)
        image = self.images.process(content)
        photo_id = str(uuid4())
        self.repos.cleanup.queue(photo_id, delayed=True)
        try:
            self.repos.photos.put(photo_id, image)

            def attach(repos):
                profile = require_profile(repos, identifier)
                repos.profiles.save(replace(profile, photo_id=photo_id))
                if profile.photo_id:
                    repos.cleanup.queue(profile.photo_id)
                repos.cleanup.finish(photo_id)

            self.uow.run(attach)
        except Exception:
            try:
                self.repos.cleanup.queue(photo_id)
                self.cleanup.execute()
            except UnavailableError:
                pass
            raise
        self.cleanup.execute()
