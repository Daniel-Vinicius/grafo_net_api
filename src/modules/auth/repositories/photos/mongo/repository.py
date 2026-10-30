from gridfs import GridFSBucket, NoFile

from infra.database.mongo import translate


class MongoPhotoRepository:
    def __init__(self, database, session=None):
        self.bucket = GridFSBucket(database, bucket_name="profile_photos")

    def put(self, identifier, content):
        translate(
            lambda: self.bucket.upload_from_stream_with_id(
                identifier, "profile.png", content
            )
        )

    def get(self, identifier):
        def read():
            try:
                return self.bucket.open_download_stream(identifier).read()
            except NoFile:
                return None

        return translate(read)

    def delete(self, identifier):
        def remove():
            try:
                self.bucket.delete(identifier)
            except NoFile:
                pass

        translate(remove)
