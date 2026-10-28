from infra.database.documents import attributes, document
from infra.database.mongo import mongo_errors
from modules.auth.domain.research_project import ResearchProject


class MongoResearchProjectRepository:
    def __init__(self, database, session=None):
        self.database = database
        self.session = session

    def get(self, identifier):
        with mongo_errors(self.session):
            value = self.database.research_projects.find_one(
                {"_id": identifier}, session=self.session
            )
        return ResearchProject(**attributes(value)) if value else None

    def list(self):
        with mongo_errors(self.session):
            return [
                ResearchProject(**attributes(value))
                for value in self.database.research_projects.find(
                    session=self.session
                ).sort([("title", 1), ("_id", 1)])
            ]

    def get_many(self, identifiers):
        with mongo_errors(self.session):
            return {
                str(value["_id"]): attributes(value)
                for value in self.database.research_projects.find(
                    {"_id": {"$in": list(identifiers)}}, session=self.session
                )
            }

    def save(self, project, insert=False):
        with mongo_errors(self.session):
            if insert:
                self.database.research_projects.insert_one(
                    document(project), session=self.session
                )
            else:
                self.database.research_projects.replace_one(
                    {"_id": project.id},
                    document(project),
                    upsert=True,
                    session=self.session,
                )
