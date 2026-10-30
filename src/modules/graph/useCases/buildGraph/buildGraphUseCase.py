from infra.database.context import Repositories
from modules.graph.domain.builder import build_graph


class BuildGraphUseCase:
    def __init__(self, repos: Repositories):
        self.repos = repos

    def execute(self):
        profiles = self.repos.network.list_active()
        return build_graph(
            profiles,
            self.repos.connections.accepted(),
            self.repos.network.catalogs(profiles),
        )
