from typing import Protocol

PHOTO_LIMIT = 2 * 1024 * 1024


class ImageProcessor(Protocol):
    def process(self, content: bytes) -> bytes: ...
