from pymongo.write_concern import WriteConcern

from infra.database.mongo import translate


class InMemoryUnitOfWork:
    def __init__(self, database, factory):
        self.database, self.factory = database, factory

    def run(self, callback):
        with self.database.lock:
            snapshot = self.database.snapshot()
            try:
                return callback(self.factory())
            except Exception:
                self.database.restore(snapshot)
                raise


class MongoUnitOfWork:
    def __init__(self, database, factory):
        self.database, self.factory = database, factory

    def run(self, callback):
        def transact():
            with self.database.client.start_session() as session:
                return session.with_transaction(
                    lambda active: callback(self.factory(active)),
                    write_concern=WriteConcern("majority"),
                )

        return translate(transact)
