from infra.database.documents import attributes, document
from infra.database.mongo import mongo_errors
from modules.auth.domain.password_reset import PasswordReset


class MongoPasswordResetRepository:
    def __init__(self, database, session=None):
        self.database = database
        self.session = session

    def get_hash(self, token_hash):
        with mongo_errors(self.session):
            value = self.database.password_resets.find_one(
                {"token_hash": token_hash}, session=self.session
            )
        return PasswordReset(**attributes(value)) if value else None

    def latest_for_user(self, user_id):
        with mongo_errors(self.session):
            value = self.database.password_resets.find_one(
                {"user_id": user_id}, sort=[("created_at", -1)], session=self.session
            )
        return PasswordReset(**attributes(value)) if value else None

    def save(self, reset):
        with mongo_errors(self.session):
            self.database.password_resets.replace_one(
                {"_id": reset.id}, document(reset), upsert=True, session=self.session
            )

    def delete(self, identifier):
        with mongo_errors(self.session):
            self.database.password_resets.delete_one(
                {"_id": identifier}, session=self.session
            )

    def delete_for_user(self, user_id):
        with mongo_errors(self.session):
            self.database.password_resets.delete_many(
                {"user_id": user_id}, session=self.session
            )
