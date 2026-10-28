from infra.database.mongo import mongo_errors


class MongoTokenRepository:
    def __init__(self, database, session=None):
        self.database = database
        self.session = session

    def revoke(self, jti, expires_at):
        with mongo_errors(self.session):
            self.database.revoked_tokens.update_one(
                {"_id": jti},
                {"$set": {"expires_at": expires_at}},
                upsert=True,
                session=self.session,
            )

    def is_revoked(self, jti):
        with mongo_errors(self.session):
            return (
                self.database.revoked_tokens.find_one(
                    {"_id": jti}, {"_id": 1}, session=self.session
                )
                is not None
            )
