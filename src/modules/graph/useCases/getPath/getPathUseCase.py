from modules.graph.useCases.buildGraph.buildGraphUseCase import BuildGraphUseCase


class GetPathUseCase:
    def __init__(self, graph: BuildGraphUseCase):
        self.graph = graph

    def execute(self, identifier, target):
        graph = self.graph.execute()
        graph.require(target)
        path = graph.paths_from(identifier).path_to(target)
        return {
            "path": path.public() if path else None,
            "graph": graph.visualization(identifier, [path], [target]),
        }
