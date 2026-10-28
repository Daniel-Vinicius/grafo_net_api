from infra.database.context import Repositories
from infra.errors import UnavailableError


class CleanupPhotosUseCase:
    def __init__(self, repos: Repositories):
        self.repos = repos

    def execute(self):
        count = 0
        try:
            pending = self.repos.cleanup.pending()
        except UnavailableError:
            return count
        for identifier in pending:
            try:
                if self.repos.cleanup.referenced(identifier):
                    continue
                self.repos.photos.delete(identifier)
                self.repos.cleanup.finish(identifier)
                count += 1
            except UnavailableError:
                continue
        return count
