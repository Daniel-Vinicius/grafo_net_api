from infra.database.contract import DuplicateRecordError
from infra.database.memory import MemoryDatabase


class InMemoryResearchProjectRepository:
    def __init__(self, database: MemoryDatabase):
        self.database = database

    def get(self, identifier):
        with self.database.lock:
            return self.database.projects.get(identifier)

    def list(self):
        with self.database.lock:
            return sorted(
                self.database.projects.values(),
                key=lambda project: (project.title, project.id),
            )

    def get_many(self, identifiers):
        with self.database.lock:
            return {
                key: self.database.projects[key].to_dict()
                for key in identifiers
                if key in self.database.projects
            }

    def save(self, project, insert=False):
        with self.database.lock:
            if insert and project.id in self.database.projects:
                raise DuplicateRecordError("Pesquisa já existe")
            self.database.projects[project.id] = project
