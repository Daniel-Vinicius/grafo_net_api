from infra.database.mongo import mongo_errors


class MongoEmbeddingRepository:
    def __init__(self, database, session=None):
        self.database = database
        self.session = session

    def get_many(self, identifiers):
        with mongo_errors(self.session):
            return {
                str(value["_id"]): value
                for value in self.database.profile_embeddings.find(
                    {"_id": {"$in": identifiers}}, session=self.session
                )
            }

    def save(self, record):
        with mongo_errors(self.session):
            self.database.profile_embeddings.replace_one(
                {"_id": record["_id"]}, dict(record), upsert=True, session=self.session
            )

    def delete(self, identifier):
        with mongo_errors(self.session):
            self.database.profile_embeddings.delete_one(
                {"_id": identifier}, session=self.session
            )
