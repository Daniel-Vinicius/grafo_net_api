from infra.database.documents import attributes, document
from infra.database.mongo import mongo_errors
from modules.auth.domain.invite import Invite


class MongoInviteRepository:
    def __init__(self, database, session=None):
        self.database = database
        self.session = session

    def get_hash(self, token_hash):
        with mongo_errors(self.session):
            value = self.database.invites.find_one(
                {"token_hash": token_hash}, session=self.session
            )
        return Invite(**attributes(value)) if value else None

    def save(self, invite):
        with mongo_errors(self.session):
            self.database.invites.replace_one(
                {"_id": invite.id}, document(invite), upsert=True, session=self.session
            )

    def delete(self, identifier):
        with mongo_errors(self.session):
            self.database.invites.delete_one({"_id": identifier}, session=self.session)

    def by_creator(self, identifier):
        with mongo_errors(self.session):
            return [
                Invite(**attributes(value))
                for value in self.database.invites.find(
                    {"created_by": identifier}, session=self.session
                )
            ]
