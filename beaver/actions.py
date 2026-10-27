"""Local file actions for the floating-widget prototype.

Own implementation, written from scratch for this project.
No network, no accounts, no telemetry.

Every action writes a NEW file next to the original and never
overwrites it. If the target name already exists, a number is
appended (``_2``, ``_3``, ...) so the original stays untouched.
"""

from __future__ import annotations

import html as html_lib
import os
import re
from datetime import date
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


# ---------------------------------------------------------------------------
# Markdown / text actions (v0.2). Own code except the `markdown` package
# itself, which renders MD -> HTML. The MD -> TXT stripping below is a
# small hand-written routine, not a copied library. All outputs are new
# files next to the original (or, for pasted text, in the folder the
# user picks); the original is never overwritten.
# ---------------------------------------------------------------------------


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Fall back to latin-1 so a .md file with odd bytes still converts
        # instead of crashing; content bytes are preserved one-to-one.
        return path.read_text(encoding="latin-1")


def _unique_named(directory: Path, stem: str, suffix: str, extension: str) -> Path:
    """Return a non-existing path in ``directory`` (same _2/_3 rule)."""
    candidate = directory / f"{stem}{suffix}.{extension}"
    counter = 2
    while candidate.exists():
        candidate = directory / f"{stem}{suffix}_{counter}.{extension}"
        counter += 1
    return candidate


def default_text_filename(extension: str) -> str:
    """Sensible default name for pasted text, e.g. ``text-2026-10-27.md``."""
    return f"text-{date.today().isoformat()}.{extension}"


def unique_for_chosen(chosen: Path) -> Path:
    """Apply the _2/_3 rule to a user-chosen save path, never overwriting."""
    if not chosen.exists():
        return chosen
    counter = 2
    while True:
        candidate = chosen.with_name(f"{chosen.stem}_{counter}{chosen.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def md_to_html(source: str | os.PathLike) -> Path:
    """Convert a .md file to a standalone .html file, next to it."""
    import markdown

    original = Path(source)
    text = _read_text(original)
    body = markdown.markdown(
        text, extensions=["fenced_code", "tables", "sane_lists"]
    )
    title = html_lib.escape(original.stem)
    document = (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        f"<title>{title}</title>\n</head>\n<body>\n{body}\n</body>\n</html>\n"
    )
    target = _unique_output(original, "_converted", "html")
    target.write_text(document, encoding="utf-8")
    return target


def strip_markdown(text: str) -> str:
    """Strip common Markdown syntax, keeping the readable text.

    Hand-written, deliberately simple: code fences and inline code keep
    their contents, images/links keep their visible text, headings,
    emphasis, list markers, blockquotes and rules are removed.
    No content words are dropped on purpose.
    """
    lines = []
    in_fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            lines.append(line)
            continue
        # Images: ![alt](url) -> alt ; links: [text](url) -> text
        line = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", line)
        line = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", line)
        # Headings, blockquotes, list markers, horizontal rules
        line = re.sub(r"^#{1,6}\s+", "", line)
        line = re.sub(r"^>\s?", "", line)
        line = re.sub(r"^\s*[-*+]\s+", "", line)
        line = re.sub(r"^\s*\d+[.)]\s+", "", line)
        if re.fullmatch(r"[-*_]{3,}", line.strip()):
            continue
        # Inline code keeps its contents, emphasis markers go away
        line = line.replace("`", "")
        line = re.sub(r"(\*\*|__)(.*?)\1", r"\2", line)
        line = re.sub(r"(\*|_)(.*?)\1", r"\2", line)
        # Raw HTML tags are dropped, their text stays
        line = re.sub(r"<[^>]+>", "", line)
        lines.append(line.rstrip())
    return "\n".join(lines).strip() + "\n"


def md_to_txt(source: str | os.PathLike) -> Path:
    """Convert a .md file to plain .txt, next to the original."""
    original = Path(source)
    target = _unique_output(original, "_converted", "txt")
    target.write_text(strip_markdown(_read_text(original)), encoding="utf-8")
    return target


def clean_md(source: str | os.PathLike) -> Path:
    """Write a cleaned copy of a .md file: no trailing whitespace.

    Only whitespace is changed: trailing spaces/tabs per line are
    removed, runs of 3+ blank lines collapse to at most 2, and the
    file ends with exactly one newline. No content lines are removed.
    """
    original = Path(source)
    lines = [line.rstrip() for line in _read_text(original).splitlines()]
    cleaned: list[str] = []
    blank_run = 0
    for line in lines:
        if line == "":
            blank_run += 1
            if blank_run > 2:
                continue
        else:
            blank_run = 0
        cleaned.append(line)
    while cleaned and cleaned[-1] == "":
        cleaned.pop()
    target = _unique_output(original, "_clean", "md")
    target.write_text("\n".join(cleaned) + "\n", encoding="utf-8")
    return target


def save_text_as_md(text: str, directory: str | os.PathLike) -> Path:
    """Save pasted text as a .md file in ``directory`` (no overwrite)."""
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    target = _unique_named(folder, f"text-{date.today().isoformat()}", "", "md")
    target.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    return target


def save_text_to_path(
    text: str, chosen: str | os.PathLike, kind: str
) -> Path:
    """Save pasted text to a user-chosen path, never overwriting it.

    ``kind`` is "md", "txt" or "html" (Markdown text is rendered to HTML
    for "html"). The _2/_3 rule applies if the chosen path exists.
    """
    import markdown

    target = unique_for_chosen(Path(chosen))
    target.parent.mkdir(parents=True, exist_ok=True)
    if kind == "html":
        body = markdown.markdown(
            text, extensions=["fenced_code", "tables", "sane_lists"]
        )
        content = (
            "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<title>text</title>\n</head>\n<body>\n"
            f"{body}\n</body>\n</html>\n"
        )
    else:
        content = text if text.endswith("\n") else text + "\n"
    target.write_text(content, encoding="utf-8")
    return target


def default_text_dir() -> Path:
    """Default folder for pasted-text saves: Documents, else home."""
    documents = Path.home() / "Documents"
    return documents if documents.is_dir() else Path.home()


def save_text_as_txt(text: str, directory: str | os.PathLike) -> Path:
    """Save pasted text as a plain .txt file in ``directory``."""
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    target = _unique_named(folder, f"text-{date.today().isoformat()}", "", "txt")
    target.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    return target


def text_to_html(text: str, directory: str | os.PathLike) -> Path:
    """Convert pasted Markdown text to a standalone .html file."""
    import markdown

    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    body = markdown.markdown(text, extensions=["fenced_code", "tables", "sane_lists"])
    document = (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<title>text</title>\n</head>\n<body>\n"
        f"{body}\n</body>\n</html>\n"
    )
    target = _unique_named(folder, f"text-{date.today().isoformat()}", "", "html")
    target.write_text(document, encoding="utf-8")
    return target


# Action id -> (button label, function), used by the ring menu.
ACTIONS = [
    ("PNG", convert_to_png),
    ("JPG", convert_to_jpg),
    ("Compress", compress_image),
    ("Strip metadata", strip_metadata),
    ("White background", add_white_background),
]

# .md files get their own ring (v0.2) instead of the image ring.
MD_ACTIONS = [
    ("MD → HTML", md_to_html),
    ("MD → TXT", md_to_txt),
    ("Clean MD", clean_md),
]
