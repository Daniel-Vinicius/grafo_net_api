from infra.database.context import Repositories


class ListConnectionsUseCase:
    def __init__(self, repos: Repositories):
        self.repos = repos

    def execute(self, identifier):
        return {
            "connections": [
                item.public() for item in self.repos.connections.list_for(identifier)
            ]
        }
