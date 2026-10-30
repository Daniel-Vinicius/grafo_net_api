from modules.graph.useCases.buildGraph.buildGraphUseCase import BuildGraphUseCase


class GetNetworkStatsUseCase:
    def __init__(self, graph: BuildGraphUseCase):
        self.graph = graph

    def execute(self):
        return {"people": len(self.graph.execute().profiles)}
