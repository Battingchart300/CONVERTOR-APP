"""Local file actions for the floating-widget prototype.

Own implementation, written from scratch for this project.
No network, no accounts, no telemetry.

Every action writes a NEW file next to the original and never
overwrites it. If the target name already exists, a number is
appended (``_2``, ``_3``, ...) so the original stays untouched.
"""

from __future__ import annotations

import os
from pathlib import Path

from PIL import Image


def _unique_output(original: Path, suffix: str, extension: str) -> Path:
    """Return a non-existing output path next to ``original``."""
    candidate = original.with_name(f"{original.stem}{suffix}.{extension}")
    counter = 2
    while candidate.exists():
        candidate = original.with_name(
            f"{original.stem}{suffix}_{counter}.{extension}"
        )
        counter += 1
    return candidate


def _open_image(path: Path) -> Image.Image:
    try:
        image = Image.open(path)
        image.load()
    except Exception as exc:  # Pillow raises several types for bad files
        raise ValueError(f"Not a readable image file: {path.name}") from exc
    return image


def convert_to_png(source: str | os.PathLike) -> Path:
    """Convert an image to PNG, next to the original."""
    original = Path(source)
    image = _open_image(original)
    target = _unique_output(original, "_converted", "png")
    image.convert("RGBA").save(target, format="PNG")
    return target


def convert_to_jpg(source: str | os.PathLike) -> Path:
    """Convert an image to JPG (quality 92), next to the original."""
    original = Path(source)
    image = _open_image(original)
    target = _unique_output(original, "_converted", "jpg")
    image.convert("RGB").save(target, format="JPEG", quality=92)
    return target


def compress_image(source: str | os.PathLike) -> Path:
    """Save a smaller version of the image, next to the original.

    JPEGs are re-saved at quality 70. Other formats are re-saved
    with Pillow's ``optimize`` flag. Dimensions are unchanged in v0.1.
    """
    original = Path(source)
    image = _open_image(original)
    extension = original.suffix.lstrip(".").lower() or "png"
    if extension in ("jpg", "jpeg"):
        extension = "jpg"
    target = _unique_output(original, "_compressed", extension)
    if extension == "jpg":
        image.convert("RGB").save(target, format="JPEG", quality=70, optimize=True)
    else:
        image.save(target, optimize=True)
    return target


def strip_metadata(source: str | os.PathLike) -> Path:
    """Save a copy of the image with no EXIF / GPS / text metadata.

    The pixel data is copied into a fresh image object and saved
    without any EXIF block, so no camera model, GPS location or
    other embedded tags travel with the output file.
    """
    original = Path(source)
    image = _open_image(original)
    extension = original.suffix.lstrip(".").lower() or "png"
    if extension in ("jpg", "jpeg"):
        extension = "jpg"
    target = _unique_output(original, "_clean", extension)
    clean = Image.new(image.mode, image.size)
    clean.paste(image)
    if extension == "jpg":
        clean.convert("RGB").save(target, format="JPEG", quality=92, exif=b"")
    else:
        clean.save(target, format="PNG")
    return target


def add_white_background(source: str | os.PathLike) -> Path:
    """Composite a (possibly transparent) image onto white.

    Images without transparency are simply copied under a new name,
    so the original is still never overwritten.
    """
    original = Path(source)
    image = _open_image(original)
    target = _unique_output(original, "_whitebg", "png")
    if image.mode in ("RGBA", "LA") or (
        image.mode == "P" and "transparency" in image.info
    ):
        rgba = image.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        background.alpha_composite(rgba)
        background.convert("RGB").save(target, format="PNG")
    else:
        image.convert("RGB").save(target, format="PNG")
    return target


# Action id -> (button label, function), used by the ring menu.
ACTIONS = [
    ("PNG", convert_to_png),
    ("JPG", convert_to_jpg),
    ("Compress", compress_image),
    ("Strip metadata", strip_metadata),
    ("White background", add_white_background),
]
