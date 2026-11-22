"""Read display-oriented dimensions without resizing or modifying an upload."""

import warnings

from PIL import Image, UnidentifiedImageError


def image_dimensions(file):
    position = file.tell()
    try:
        file.seek(0)
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(file) as image:
                width, height = image.size
                if image.getexif().get(274) in {5, 6, 7, 8}:
                    width, height = height, width
                return {"width": width, "height": height}
    except (
        OSError,
        ValueError,
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        # Existing upload validation still determines whether a file is accepted.
        return {}
    finally:
        file.seek(position)
