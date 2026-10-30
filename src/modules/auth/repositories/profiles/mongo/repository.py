from infra.database.documents import attributes, document
from infra.database.mongo import mongo_errors
from modules.auth.domain.profile import Profile


class MongoProfileRepository:
    def __init__(self, database, session=None):
        self.database = database
        self.session = session

    def get(self, identifier):
        with mongo_errors(self.session):
            value = self.database.profiles.find_one(
                {"_id": identifier}, session=self.session
            )
        return Profile.from_dict(attributes(value)) if value else None

    def save(self, profile, insert=False):
        with mongo_errors(self.session):
            if insert:
                self.database.profiles.insert_one(
                    document(profile), session=self.session
                )
            else:
                self.database.profiles.replace_one(
                    {"_id": profile.id},
                    document(profile),
                    upsert=True,
                    session=self.session,
                )

    def delete(self, identifier):
        with mongo_errors(self.session):
            self.database.profiles.delete_one({"_id": identifier}, session=self.session)

    def by_advisor(self, identifier):
        with mongo_errors(self.session):
            return [
                Profile.from_dict(attributes(value))
                for value in self.database.profiles.find(
                    {"research_participations.advisor_user_id": identifier},
                    session=self.session,
                )
            ]
