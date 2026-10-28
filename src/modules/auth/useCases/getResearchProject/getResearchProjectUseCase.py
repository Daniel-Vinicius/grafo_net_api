from infra.database.context import Repositories
from modules.auth.domain.errors import NotFoundError


class GetResearchProjectUseCase:
    def __init__(self, repos: Repositories):
        self.repos = repos

    def execute(self, identifier):
        project = self.repos.projects.get(identifier)
        if project is None:
            raise NotFoundError("Pesquisa não encontrada")
        return project.to_dict()
