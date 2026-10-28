from modules.graph.useCases.buildGraph.buildGraphUseCase import BuildGraphUseCase


class GetCloseNetworkUseCase:
    def __init__(self, graph: BuildGraphUseCase):
        self.graph = graph

    def execute(self, identifier):
        return self.graph.execute().close_network(identifier)
