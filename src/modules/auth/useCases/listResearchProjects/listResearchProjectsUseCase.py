from infra.database.context import Repositories


class ListResearchProjectsUseCase:
    def __init__(self, repos: Repositories):
        self.repos = repos

    def execute(self):
        return [project.to_dict() for project in self.repos.projects.list()]
