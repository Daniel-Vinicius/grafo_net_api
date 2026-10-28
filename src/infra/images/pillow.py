import warnings
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

from infra.images.contract import PHOTO_LIMIT
from modules.auth.domain.errors import PayloadTooLargeError, ValidationError


class PillowImageProcessor:
    def process(self, content: bytes) -> bytes:
        if len(content) > PHOTO_LIMIT:
            raise PayloadTooLargeError("Foto deve ter até 2 MiB")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(content)) as original:
                    if (
                        original.format not in {"JPEG", "PNG"}
                        or original.width * original.height > 16_000_000
                    ):
                        raise ValidationError(
                            "Use JPEG ou PNG com até 16 milhões de pixels"
                        )
                    original.load()
                    image = ImageOps.exif_transpose(original).convert("RGBA")
                    image.thumbnail((512, 512))
                    clean = Image.new("RGBA", image.size)
                    clean.paste(image)
                    output = BytesIO()
                    clean.save(output, format="PNG")
                    return output.getvalue()
        except (
            UnidentifiedImageError,
            OSError,
            ValueError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ):
            raise ValidationError("Imagem inválida") from None
