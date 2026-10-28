from infra.database.context import Repositories


class ListEntitiesUseCase:
    def __init__(self, repos: Repositories):
        self.repos = repos

    def execute(self):
        return self.repos.entities.list()
