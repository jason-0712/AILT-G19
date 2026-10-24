"""Decode and re-encode uploads; never serve arbitrary uploaded files."""
from io import BytesIO
import warnings
from PIL import Image, ImageOps, UnidentifiedImageError
MAX_UPLOAD = 5 * 1024 * 1024
MAX_STORED = 400_000

def prepare_photo(data):
    if not data:
        return None
    if len(data) > MAX_UPLOAD:
        raise ValueError("Choose an image smaller than 5 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as source:
                if source.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValueError("Use a JPEG, PNG or WebP photo.")
                if source.width * source.height > 16_000_000:
                    raise ValueError("Use a photo with no more than 16 million pixels.")
                source.load()
                picture = ImageOps.exif_transpose(source).convert("RGB")
                picture.thumbnail((1280, 1280))
                clean = Image.new("RGB", picture.size)
                clean.paste(picture)
                output = BytesIO()
                clean.save(output, format="JPEG", quality=80, optimize=True)
                if output.tell() > MAX_STORED:
                    output = BytesIO()
                    clean.thumbnail((800, 800))
                    clean.save(output, format="JPEG", quality=65, optimize=True)
                if output.tell() > MAX_STORED:
                    raise ValueError("This photo is too detailed; choose a smaller image.")
                return output.getvalue()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as exc:
        raise ValueError("The file is not a supported, readable image.") from exc
