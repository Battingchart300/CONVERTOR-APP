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


def _unique_output(
    original: Path, suffix: str, extension: str, output_dir=None
) -> Path:
    """Return a non-existing output path.

    By default next to ``original``; if ``output_dir`` is given, in
    that folder instead (created if needed). The original is never
    overwritten: an existing target name gets ``_2``, ``_3``, ...
    """
    directory = Path(output_dir) if output_dir is not None else original.parent
    if output_dir is not None:
        directory.mkdir(parents=True, exist_ok=True)
    candidate = directory / f"{original.stem}{suffix}.{extension}"
    counter = 2
    while candidate.exists():
        candidate = directory / f"{original.stem}{suffix}_{counter}.{extension}"
        counter += 1
    return candidate


def _resolve_target(
    original: Path,
    suffix: str,
    extension: str,
    output_dir=None,
    output_path=None,
) -> Path:
    """Central output resolution for every file action (v0.3).

    ``output_path`` (a user-chosen Save-dialog path) wins over
    ``output_dir`` (a chosen output folder), which wins over the
    default (next to the original). In all cases the extension is
    forced to the action's real output format, the parent folder is
    created if needed, and the _2/_3 rule applies — so a chosen path
    that already exists is never overwritten either.
    """
    if output_path is not None:
        chosen = Path(output_path)
        if chosen.suffix.lower() != f".{extension}":
            chosen = chosen.with_suffix(f".{extension}")
        chosen.parent.mkdir(parents=True, exist_ok=True)
        return unique_for_chosen(chosen)
    return _unique_output(original, suffix, extension, output_dir=output_dir)


def _image_extension(original: Path) -> str:
    """Normalised image extension for compress / strip (jpg/jpeg -> jpg)."""
    extension = original.suffix.lstrip(".").lower() or "png"
    if extension in ("jpg", "jpeg"):
        extension = "jpg"
    return extension


def _open_image(path: Path) -> Image.Image:
    try:
        image = Image.open(path)
        image.load()
    except Exception as exc:  # Pillow raises several types for bad files
        raise ValueError(f"Not a readable image file: {path.name}") from exc
    return image


def convert_to_png(
    source: str | os.PathLike, output_dir=None, output_path=None
) -> Path:
    """Convert an image to PNG (default: next to the original)."""
    original = Path(source)
    image = _open_image(original)
    target = _resolve_target(original, "_converted", "png", output_dir, output_path)
    image.convert("RGBA").save(target, format="PNG")
    return target


def _clamp_quality(value, default: int) -> int:
    """Clamp a quality setting to 10-100, falling back to ``default``."""
    try:
        return max(10, min(int(value), 100))
    except (TypeError, ValueError):
        return default


def convert_to_jpg(
    source: str | os.PathLike, output_dir=None, output_path=None,
    jpg_quality=92,
) -> Path:
    """Convert an image to JPG (default quality 92; next to original)."""
    original = Path(source)
    image = _open_image(original)
    target = _resolve_target(original, "_converted", "jpg", output_dir, output_path)
    image.convert("RGB").save(
        target, format="JPEG", quality=_clamp_quality(jpg_quality, 92)
    )
    return target


def compress_image(
    source: str | os.PathLike, output_dir=None, output_path=None,
    compress_quality=70,
) -> Path:
    """Save a smaller version of the image (default: next to original).

    JPEGs are re-saved at ``compress_quality`` (default 70). Other
    formats are re-saved with Pillow's ``optimize`` flag.
    Dimensions are unchanged in v0.1.
    """
    original = Path(source)
    image = _open_image(original)
    extension = _image_extension(original)
    target = _resolve_target(original, "_compressed", extension, output_dir, output_path)
    if extension == "jpg":
        image.convert("RGB").save(
            target, format="JPEG",
            quality=_clamp_quality(compress_quality, 70), optimize=True,
        )
    else:
        image.save(target, optimize=True)
    return target


def convert_to_webp(
    source: str | os.PathLike, output_dir=None, output_path=None
) -> Path:
    """Convert an image to WEBP (quality 90; next to original)."""
    original = Path(source)
    image = _open_image(original)
    target = _resolve_target(original, "_converted", "webp", output_dir, output_path)
    image.convert("RGB").save(target, format="WEBP", quality=90)
    return target


def image_to_pdf(
    source: str | os.PathLike, output_dir=None, output_path=None
) -> Path:
    """Render an image into a single-page PDF (next to original)."""
    original = Path(source)
    image = _open_image(original)
    target = _resolve_target(original, "_converted", "pdf", output_dir, output_path)
    if image.mode in ("RGBA", "LA") or (
        image.mode == "P" and "transparency" in image.info
    ):
        rgba = image.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        background.alpha_composite(rgba)
        image = background.convert("RGB")
    else:
        image = image.convert("RGB")
    image.save(target, format="PDF")
    return target


def strip_metadata(
    source: str | os.PathLike, output_dir=None, output_path=None
) -> Path:
    """Save a copy of the image with no EXIF / GPS / text metadata.

    The pixel data is copied into a fresh image object and saved
    without any EXIF block, so no camera model, GPS location or
    other embedded tags travel with the output file.
    """
    original = Path(source)
    image = _open_image(original)
    extension = _image_extension(original)
    target = _resolve_target(original, "_clean", extension, output_dir, output_path)
    clean = Image.new(image.mode, image.size)
    clean.paste(image)
    if extension == "jpg":
        clean.convert("RGB").save(target, format="JPEG", quality=92, exif=b"")
    else:
        clean.save(target, format="PNG")
    return target


def add_white_background(
    source: str | os.PathLike, output_dir=None, output_path=None
) -> Path:
    """Composite a (possibly transparent) image onto white.

    Images without transparency are simply copied under a new name,
    so the original is still never overwritten.
    """
    original = Path(source)
    image = _open_image(original)
    target = _resolve_target(original, "_whitebg", "png", output_dir, output_path)
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


def md_to_html(
    source: str | os.PathLike, output_dir=None, output_path=None
) -> Path:
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
    target = _resolve_target(original, "_converted", "html", output_dir, output_path)
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


def md_to_txt(
    source: str | os.PathLike, output_dir=None, output_path=None
) -> Path:
    """Convert a .md file to plain .txt, next to the original."""
    original = Path(source)
    target = _resolve_target(original, "_converted", "txt", output_dir, output_path)
    target.write_text(strip_markdown(_read_text(original)), encoding="utf-8")
    return target


def clean_md(
    source: str | os.PathLike, output_dir=None, output_path=None
) -> Path:
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
    target = _resolve_target(original, "_clean", "md", output_dir, output_path)
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
    """Default folder for pasted-text saves: the Desktop (Plocha).

    User decision (v0.2): text saves default to the Desktop, never to
    the widget/app folder. On Slovak Windows the shell folder is
    ``Desktop`` (display name "Plocha"); both spellings are tried,
    then Documents, then home, so the dialog always opens somewhere
    that exists.
    """
    home = Path.home()
    for candidate in (
        home / "Desktop",
        home / "Plocha",
        home / "Documents",
        home,
    ):
        if candidate.is_dir():
            return candidate
    return home


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


# ---------------------------------------------------------------------------
# Document conversions (v0.2, main features — user correction).
# All local, all with the same never-overwrite rule.
# Limitations, stated honestly: PDF/DOCX -> PDF keeps text, headings
# and simple lists; images, complex tables and exact Word/PDF layout
# are NOT preserved. Scanned/image-only PDFs have no extractable
# text, so PDF -> MD on those yields (nearly) empty output.
# ---------------------------------------------------------------------------


def _md_lines_to_pdf(lines: list[str], target: Path) -> Path:
    """Render simple Markdown lines to a PDF with reportlab.

    Own small renderer: headings (#, ##, ###), bullet/numbered lists,
    fenced code blocks (monospace), blank lines, and plain paragraphs.
    Inline **bold** / *italic* markers are stripped for readability.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Preformatted, SimpleDocTemplate, Spacer

    styles = getSampleStyleSheet()
    story = []
    in_fence = False
    code_lines: list[str] = []

    def flush_code() -> None:
        if code_lines:
            story.append(Preformatted("\n".join(code_lines), styles["Code"]))
            code_lines.clear()

    def plain(text: str) -> str:
        text = html_lib.escape(text)
        text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
        text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", text)
        return text

    for raw in lines:
        line = raw.rstrip()
        if line.strip().startswith("```"):
            if in_fence:
                flush_code()
            in_fence = not in_fence
            continue
        if in_fence:
            code_lines.append(line)
            continue
        if not line.strip():
            story.append(Spacer(1, 4 * mm))
            continue
        match = re.match(r"^(#{1,3})\s+(.*)", line)
        if match:
            level = len(match.group(1))
            style = styles[f"Heading{level}"]
            story.append(Paragraph(plain(match.group(2)), style))
            continue
        if re.match(r"^\s*[-*+]\s+", line):
            story.append(Paragraph("• " + plain(re.sub(r"^\s*[-*+]\s+", "", line)), styles["Normal"]))
            continue
        if re.match(r"^\s*\d+[.)]\s+", line):
            story.append(Paragraph(plain(line.strip()), styles["Normal"]))
            continue
        story.append(Paragraph(plain(line), styles["Normal"]))
    flush_code()
    if not story:
        story.append(Paragraph("(empty document)", styles["Normal"]))
    SimpleDocTemplate(str(target), pagesize=A4).build(story)
    return target


def pdf_to_md(
    source: str | os.PathLike, output_dir=None, output_path=None
) -> Path:
    """Extract a PDF's text into a Markdown file, next to it."""
    try:
        import pymupdf
    except ImportError:
        import fitz as pymupdf  # type: ignore[no-redef]
    original = Path(source)
    try:
        doc = pymupdf.open(original)
    except Exception as exc:
        raise ValueError(f"Not a readable PDF file: {original.name}") from exc
    parts = [f"# {original.stem}\n"]
    with doc:
        for index, page in enumerate(doc, start=1):
            text = page.get_text().strip()
            parts.append(f"\n## Page {index}\n\n{text}\n" if text else f"\n## Page {index}\n\n")
    target = _resolve_target(original, "_converted", "md", output_dir, output_path)
    target.write_text("\n".join(parts), encoding="utf-8")
    return target


def _docx_paragraphs(source: Path) -> list[tuple[str, str]]:
    """Return (style, text) for each non-empty Word paragraph."""
    from docx import Document

    try:
        document = Document(source)
    except Exception as exc:
        raise ValueError(f"Not a readable Word file: {source.name}") from exc
    out = []
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if text:
            out.append((paragraph.style.name if paragraph.style else "Normal", text))
    return out


def _docx_tables_to_md(source: Path) -> list[str]:
    """Best-effort Markdown tables for a Word file (rows of cell text)."""
    from docx import Document

    document = Document(source)
    blocks = []
    for table in document.tables:
        rows = [[cell.text.strip() for cell in row.cells] for row in table.rows]
        if not rows:
            continue
        blocks.append("| " + " | ".join(rows[0]) + " |")
        blocks.append("| " + " | ".join("---" for _ in rows[0]) + " |")
        for row in rows[1:]:
            blocks.append("| " + " | ".join(row) + " |")
        blocks.append("")
    return blocks


def docx_to_md(
    source: str | os.PathLike, output_dir=None, output_path=None
) -> Path:
    """Convert a Word (.docx) file to Markdown, next to it."""
    original = Path(source)
    lines = [f"# {original.stem}\n"]
    for style, text in _docx_paragraphs(original):
        if style.startswith("Heading 1"):
            lines.append(f"# {text}\n")
        elif style.startswith("Heading 2"):
            lines.append(f"## {text}\n")
        elif style.startswith("Heading 3"):
            lines.append(f"### {text}\n")
        elif style in ("List Bullet", "List Paragraph"):
            lines.append(f"- {text}")
        else:
            lines.append(text)
    lines.extend(_docx_tables_to_md(original))
    target = _resolve_target(original, "_converted", "md", output_dir, output_path)
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def _docx_to_md_lines(source: Path) -> list[str]:
    lines = [f"# {source.stem}\n"]
    for style, text in _docx_paragraphs(source):
        if style.startswith("Heading 1"):
            lines.append(f"# {text}")
        elif style.startswith("Heading 2"):
            lines.append(f"## {text}")
        elif style.startswith("Heading 3"):
            lines.append(f"### {text}")
        elif style in ("List Bullet", "List Paragraph"):
            lines.append(f"- {text}")
        else:
            lines.append(text)
    lines.extend(_docx_tables_to_md(source))
    return lines


def md_to_pdf(
    source: str | os.PathLike, output_dir=None, output_path=None
) -> Path:
    """Convert a .md file to PDF (simple text/headings/lists layout)."""
    original = Path(source)
    target = _resolve_target(original, "_converted", "pdf", output_dir, output_path)
    return _md_lines_to_pdf(_read_text(original).splitlines(), target)


def docx_to_pdf(
    source: str | os.PathLike, output_dir=None, output_path=None
) -> Path:
    """Convert a Word (.docx) file to PDF (text/headings/lists only)."""
    original = Path(source)
    target = _resolve_target(original, "_converted", "pdf", output_dir, output_path)
    return _md_lines_to_pdf(_docx_to_md_lines(original), target)


def text_to_pdf_path(text: str, chosen: str | os.PathLike) -> Path:
    """Convert pasted text to PDF at a user-chosen path (no overwrite)."""
    target = unique_for_chosen(Path(chosen))
    target.parent.mkdir(parents=True, exist_ok=True)
    return _md_lines_to_pdf(text.splitlines(), target)


def text_to_pdf(text: str, directory: str | os.PathLike) -> Path:
    """Convert pasted (Markdown) text to a PDF in ``directory``."""
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    target = _unique_named(folder, f"text-{date.today().isoformat()}", "", "pdf")
    return _md_lines_to_pdf(text.splitlines(), target)


# ---------------------------------------------------------------------------
# OpenDocument / LibreOffice conversions (v0.3).
# ONLY Python stdlib: zipfile + xml.etree. Deliberately NO odfpy (and
# nothing added to requirements.txt) — the user is wary of crashes
# after library updates, so this part has zero new dependencies.
# An ODF file is a ZIP whose content.xml holds the document.
# Honest limitations, same as DOCX: text, headings, simple lists
# and simple tables only. Images, styles, exact layout, tracked
# changes, formulas (values are read where present as text) and
# embedded objects are NOT preserved.
# ---------------------------------------------------------------------------


def _local(tag: str) -> str:
    """Local name of an XML tag, ignoring its namespace."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _odf_text(element) -> str:
    """Plain text of an ODF element, honouring spaces/tabs/line breaks."""
    parts: list[str] = []
    if element.text:
        parts.append(element.text)
    for child in element:
        name = _local(child.tag)
        if name == "s":
            try:
                count = int(child.attrib.get("c", "1"))
            except ValueError:
                count = 1
            parts.append(" " * max(1, min(count, 100)))
        elif name == "tab":
            parts.append("\t")
        elif name == "line-break":
            parts.append("\n")
        else:
            parts.append(_odf_text(child))
        if child.tail:
            parts.append(child.tail)
    return "".join(parts)


def _odf_root(source: Path):
    """Parse content.xml from an ODF zip, or raise ValueError."""
    import zipfile
    import xml.etree.ElementTree as ET

    try:
        with zipfile.ZipFile(source) as archive:
            try:
                data = archive.read("content.xml")
            except KeyError as exc:
                raise ValueError(
                    f"Not a readable OpenDocument file (no content.xml): {source.name}"
                ) from exc
    except zipfile.BadZipFile as exc:
        raise ValueError(f"Not a readable OpenDocument file: {source.name}") from exc
    try:
        return ET.fromstring(data)
    except ET.ParseError as exc:
        raise ValueError(f"Not a readable OpenDocument file: {source.name}") from exc


def _odf_body(root):
    """The office:text / office:spreadsheet / office:presentation node."""
    for element in root.iter():
        if _local(element.tag) in ("text", "spreadsheet", "presentation"):
            return element
    return root


def _repeat(attrib: dict, key: str, default: int = 1) -> int:
    try:
        return max(1, min(int(attrib.get(key, default)), 100))
    except (TypeError, ValueError):
        return default


def _collect_blocks(element, lines: list[str], list_depth: int = 0) -> None:
    """Append Markdown lines for ODF block elements, in document order.

    Handles paragraphs, headings, lists and tables; anything else
    (frames, sections, shapes) is walked into, so text inside them
    is not lost. Nested lists are indented by depth.
    """
    name = _local(element.tag)
    if name == "p":
        text = _odf_text(element).strip()
        if text:
            # list_depth is 1 for top-level list items, 2 for nested,
            # 0 for plain paragraphs: top-level items get "- ", nested
            # ones get an extra 2-space indent per level.
            prefix = ("  " * (list_depth - 1) + "- ") if list_depth else ""
            lines.append(prefix + text)
        return
    if name == "h":
        text = _odf_text(element).strip()
        if text:
            try:
                level = max(1, min(int(element.attrib.get("outline-level", "1")), 6))
            except ValueError:
                level = 1
            lines.append("#" * level + " " + text)
        return
    if name == "list":
        for item in element:
            if _local(item.tag) != "list-item":
                continue
            for child in item:
                _collect_blocks(child, lines, list_depth + 1)
        return
    if name == "table":
        rows = []
        for row in element:
            if _local(row.tag) != "table-row":
                continue
            cells: list[str] = []
            for cell in row:
                if _local(cell.tag) != "table-cell":
                    continue
                text = " ".join(
                    _odf_text(p).strip()
                    for p in cell.iter()
                    if _local(p.tag) in ("p", "h")
                )
                cells.extend([text] * _repeat(cell.attrib, "number-columns-repeated"))
            if any(cells):
                rows.append(cells)
        if rows:
            width = max(len(r) for r in rows)
            rows = [r + [""] * (width - len(r)) for r in rows]
            lines.append("| " + " | ".join(rows[0]) + " |")
            lines.append("| " + " | ".join("---" for _ in rows[0]) + " |")
            for row in rows[1:]:
                lines.append("| " + " | ".join(row) + " |")
            lines.append("")
        return
    for child in element:
        _collect_blocks(child, lines, list_depth)


def _odt_to_md_lines(source: Path) -> list[str]:
    root = _odf_root(source)
    lines = [f"# {source.stem}\n"]
    _collect_blocks(_odf_body(root), lines)
    return lines


def _odp_to_md_lines(source: Path) -> list[str]:
    root = _odf_root(source)
    body = _odf_body(root)
    lines = [f"# {source.stem}\n"]
    pages = [e for e in body.iter() if _local(e.tag) == "page"]
    if not pages:
        _collect_blocks(body, lines)
        return lines
    for index, page in enumerate(pages, start=1):
        name = page.attrib.get("name", "")
        lines.append(f"\n## Slide {index}" + (f" — {name}" if name else "") + "\n")
        _collect_blocks(page, lines)
    return lines


def _ods_sheets(source: Path) -> list[tuple[str, list[list[str]]]]:
    """(sheet name, rows) for every spreadsheet table in an ODS file."""
    root = _odf_root(source)
    body = _odf_body(root)
    sheets = []
    for table in body.iter():
        if _local(table.tag) != "table":
            continue
        name = table.attrib.get("name", "Sheet")
        rows: list[list[str]] = []
        for row in table:
            if _local(row.tag) != "table-row":
                continue
            cells: list[str] = []
            for cell in row:
                if _local(cell.tag) != "table-cell":
                    continue
                text = " ".join(
                    _odf_text(p).strip()
                    for p in cell.iter()
                    if _local(p.tag) in ("p", "h")
                )
                cells.extend([text] * _repeat(cell.attrib, "number-columns-repeated"))
            repeat = _repeat(row.attrib, "number-rows-repeated")
            for _ in range(repeat):
                rows.append(list(cells))
        # Drop fully-empty trailing rows, keep the sheet if it has data.
        while rows and not any(rows[-1]):
            rows.pop()
        sheets.append((name, rows))
    return sheets


def _ods_to_md_lines(source: Path) -> list[str]:
    lines = [f"# {source.stem}\n"]
    for name, rows in _ods_sheets(source):
        lines.append(f"\n## {name}\n")
        if not rows:
            continue
        width = max(len(r) for r in rows)
        rows = [r + [""] * (width - len(r)) for r in rows]
        lines.append("| " + " | ".join(rows[0]) + " |")
        lines.append("| " + " | ".join("---" for _ in rows[0]) + " |")
        for row in rows[1:]:
            lines.append("| " + " | ".join(row) + " |")
    return lines


def odt_to_md(
    source: str | os.PathLike, output_dir=None, output_path=None
) -> Path:
    """Convert a LibreOffice Writer (.odt) file to Markdown."""
    original = Path(source)
    target = _resolve_target(original, "_converted", "md", output_dir, output_path)
    target.write_text("\n".join(_odt_to_md_lines(original)), encoding="utf-8")
    return target


def odt_to_pdf(
    source: str | os.PathLike, output_dir=None, output_path=None
) -> Path:
    """Convert a LibreOffice Writer (.odt) file to PDF (text only)."""
    original = Path(source)
    target = _resolve_target(original, "_converted", "pdf", output_dir, output_path)
    return _md_lines_to_pdf(_odt_to_md_lines(original), target)


def ods_to_md(
    source: str | os.PathLike, output_dir=None, output_path=None
) -> Path:
    """Convert a LibreOffice Calc (.ods) file to Markdown tables."""
    original = Path(source)
    target = _resolve_target(original, "_converted", "md", output_dir, output_path)
    target.write_text("\n".join(_ods_to_md_lines(original)), encoding="utf-8")
    return target


def ods_to_csv(
    source: str | os.PathLike, output_dir=None, output_path=None
) -> Path:
    """Convert a LibreOffice Calc (.ods) file to CSV (first sheet only)."""
    import csv
    import io

    original = Path(source)
    sheets = _ods_sheets(original)
    target = _resolve_target(original, "_converted", "csv", output_dir, output_path)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    if sheets:
        for row in sheets[0][1]:
            writer.writerow(row)
    target.write_text(buffer.getvalue(), encoding="utf-8", newline="")
    return target


def odp_to_md(
    source: str | os.PathLike, output_dir=None, output_path=None
) -> Path:
    """Convert a LibreOffice Impress (.odp) file to Markdown, per slide."""
    original = Path(source)
    target = _resolve_target(original, "_converted", "md", output_dir, output_path)
    target.write_text("\n".join(_odp_to_md_lines(original)), encoding="utf-8")
    return target


def odp_to_pdf(
    source: str | os.PathLike, output_dir=None, output_path=None
) -> Path:
    """Convert a LibreOffice Impress (.odp) file to PDF (text only)."""
    original = Path(source)
    target = _resolve_target(original, "_converted", "pdf", output_dir, output_path)
    return _md_lines_to_pdf(_odp_to_md_lines(original), target)


# ---------------------------------------------------------------------------
# More formats (v0.5, stdlib only for the Office formats — same
# approach as ODF: the .xlsx/.pptx files are ZIPs with XML inside).
# Honest limitations: values only, formulas are read as their
# stored (cached) value and are NOT recalculated; text only for
# slides; images, styles, exact layout, charts and embedded
# objects are NOT preserved. Bad files raise a clean ValueError.
# ---------------------------------------------------------------------------


def _ooxml_root(source: Path, member: str):
    """Parse one XML member from an Office ZIP, or raise ValueError."""
    import zipfile
    import xml.etree.ElementTree as ET

    try:
        with zipfile.ZipFile(source) as archive:
            try:
                data = archive.read(member)
            except KeyError as exc:
                raise ValueError(
                    f"Not a readable Office file (no {member}): {source.name}"
                ) from exc
    except zipfile.BadZipFile as exc:
        raise ValueError(f"Not a readable Office file: {source.name}") from exc
    try:
        return ET.fromstring(data)
    except ET.ParseError as exc:
        raise ValueError(f"Not a readable Office file: {source.name}") from exc


def _ooxml_members(source: Path) -> list[str]:
    import zipfile

    try:
        with zipfile.ZipFile(source) as archive:
            return archive.namelist()
    except zipfile.BadZipFile as exc:
        raise ValueError(f"Not a readable Office file: {source.name}") from exc


def _col_letters(ref: str) -> str:
    return "".join(ch for ch in ref if ch.isalpha())


def _xlsx_sheets(source: Path) -> list[tuple[str, list[list[str]]]]:
    """(sheet name, rows) for an .xlsx file, in workbook order."""
    import zipfile
    import xml.etree.ElementTree as ET

    try:
        with zipfile.ZipFile(source) as archive:
            shared: list[str] = []
            if "xl/sharedStrings.xml" in archive.namelist():
                sroot = ET.fromstring(archive.read("xl/sharedStrings.xml"))
                for si in sroot:
                    if _local(si.tag) != "si":
                        continue
                    shared.append("".join(
                        t.text or "" for t in si.iter() if _local(t.tag) == "t"
                    ))
            workbook = ET.fromstring(archive.read("xl/workbook.xml"))
            names = [
                s.attrib.get("name", f"Sheet {i + 1}")
                for i, s in enumerate(workbook.iter())
                if _local(s.tag) == "sheet"
            ]
            sheets: list[tuple[str, list[list[str]]]] = []
            sheet_files = sorted(
                (n for n in archive.namelist()
                 if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")),
                key=lambda n: int("".join(ch for ch in n.split("/")[-1] if ch.isdigit()) or 0),
            )
            for index, member in enumerate(sheet_files):
                sroot = ET.fromstring(archive.read(member))
                rows_by_num: dict[int, dict[str, str]] = {}
                for row in sroot.iter():
                    if _local(row.tag) != "row":
                        continue
                    try:
                        rnum = int(row.attrib.get("r", "0"))
                    except ValueError:
                        rnum = 0
                    cells: dict[str, str] = {}
                    for cell in row:
                        if _local(cell.tag) != "c":
                            continue
                        ref = cell.attrib.get("r", "")
                        ctype = cell.attrib.get("t")
                        value = ""
                        if ctype == "s":
                            v = next((e.text for e in cell if _local(e.tag) == "v"), None)
                            try:
                                value = shared[int(v)] if v is not None else ""
                            except (ValueError, IndexError):
                                value = ""
                        elif ctype == "inlineStr":
                            value = "".join(
                                t.text or "" for t in cell.iter() if _local(t.tag) == "t"
                            )
                        else:
                            # Plain value, or a formula's cached value in <v>.
                            value = next(
                                (e.text or "" for e in cell if _local(e.tag) == "v"), ""
                            )
                        cells[_col_letters(ref)] = value
                    if cells:
                        rows_by_num[rnum] = cells
                rows: list[list[str]] = []
                if rows_by_num:
                    all_cols = sorted(
                        {c for cells in rows_by_num.values() for c in cells},
                        key=lambda c: (len(c), c),
                    )
                    for rnum in sorted(rows_by_num):
                        rows.append([rows_by_num[rnum].get(c, "") for c in all_cols])
                while rows and not any(rows[-1]):
                    rows.pop()
                name = names[index] if index < len(names) else f"Sheet {index + 1}"
                sheets.append((name, rows))
            return sheets
    except (zipfile.BadZipFile, ET.ParseError, KeyError) as exc:
        raise ValueError(f"Not a readable Excel file: {source.name}") from exc


def _rows_to_md_lines(rows: list[list[str]]) -> list[str]:
    """Markdown table lines for rows (first row = header)."""
    if not rows:
        return []
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    clean = [[c.replace("|", "\\|") for c in r] for r in rows]
    lines = ["| " + " | ".join(clean[0]) + " |",
             "| " + " | ".join("---" for _ in clean[0]) + " |"]
    lines.extend("| " + " | ".join(r) + " |" for r in clean[1:])
    return lines


def _xlsx_to_md_lines(source: Path) -> list[str]:
    lines = [f"# {source.stem}\n"]
    for name, rows in _xlsx_sheets(source):
        lines.append(f"\n## {name}\n")
        lines.extend(_rows_to_md_lines(rows))
    return lines


def xlsx_to_md(source: str | os.PathLike, output_dir=None, output_path=None) -> Path:
    """Convert an Excel (.xlsx) file to Markdown tables (values only)."""
    original = Path(source)
    target = _resolve_target(original, "_converted", "md", output_dir, output_path)
    target.write_text("\n".join(_xlsx_to_md_lines(original)), encoding="utf-8")
    return target


def xlsx_to_csv(source: str | os.PathLike, output_dir=None, output_path=None) -> Path:
    """Convert an Excel (.xlsx) file to CSV (first sheet only)."""
    import csv
    import io

    original = Path(source)
    sheets = _xlsx_sheets(original)
    target = _resolve_target(original, "_converted", "csv", output_dir, output_path)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    if sheets:
        for row in sheets[0][1]:
            writer.writerow(row)
    target.write_text(buffer.getvalue(), encoding="utf-8", newline="")
    return target


def xlsx_to_pdf(source: str | os.PathLike, output_dir=None, output_path=None) -> Path:
    """Convert an Excel (.xlsx) file to PDF (tables as text only)."""
    original = Path(source)
    target = _resolve_target(original, "_converted", "pdf", output_dir, output_path)
    return _md_lines_to_pdf(_xlsx_to_md_lines(original), target)


def _pptx_to_md_lines(source: Path) -> list[str]:
    lines = [f"# {source.stem}\n"]
    members = [m for m in _ooxml_members(source)
               if m.startswith("ppt/slides/slide") and m.endswith(".xml")]
    members.sort(key=lambda m: int("".join(ch for ch in m.split("/")[-1] if ch.isdigit()) or 0))
    if not members:
        raise ValueError(f"Not a readable PowerPoint file: {source.name}")
    for index, member in enumerate(members, start=1):
        root = _ooxml_root(source, member)
        lines.append(f"\n## Slide {index}\n")
        for para in root.iter():
            if _local(para.tag) != "p":
                continue
            text = "".join(t.text or "" for t in para.iter() if _local(t.tag) == "t").strip()
            if text:
                lines.append(text)
    return lines


def pptx_to_md(source: str | os.PathLike, output_dir=None, output_path=None) -> Path:
    """Convert a PowerPoint (.pptx) file to Markdown (slide text only)."""
    original = Path(source)
    target = _resolve_target(original, "_converted", "md", output_dir, output_path)
    target.write_text("\n".join(_pptx_to_md_lines(original)), encoding="utf-8")
    return target


def pptx_to_pdf(source: str | os.PathLike, output_dir=None, output_path=None) -> Path:
    """Convert a PowerPoint (.pptx) file to PDF (slide text only)."""
    original = Path(source)
    target = _resolve_target(original, "_converted", "pdf", output_dir, output_path)
    return _md_lines_to_pdf(_pptx_to_md_lines(original), target)


def txt_to_md(source: str | os.PathLike, output_dir=None, output_path=None) -> Path:
    """Convert a plain-text (.txt) file to Markdown (text unchanged)."""
    original = Path(source)
    text = _read_text(original)
    target = _resolve_target(original, "_converted", "md", output_dir, output_path)
    target.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    return target


def txt_to_pdf(source: str | os.PathLike, output_dir=None, output_path=None) -> Path:
    """Convert a plain-text (.txt) file to PDF."""
    original = Path(source)
    target = _resolve_target(original, "_converted", "pdf", output_dir, output_path)
    return _md_lines_to_pdf(_read_text(original).splitlines(), target)


def _csv_rows(source: Path) -> list[list[str]]:
    import csv
    import io

    try:
        raw = source.read_bytes()
    except OSError as exc:
        raise ValueError(f"Not a readable CSV file: {source.name}") from exc
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("latin-1")
    try:
        return [row for row in csv.reader(io.StringIO(text)) if row]
    except csv.Error as exc:
        raise ValueError(f"Not a readable CSV file: {source.name}") from exc


def csv_to_md(source: str | os.PathLike, output_dir=None, output_path=None) -> Path:
    """Convert a CSV file to a Markdown table (first row = header)."""
    original = Path(source)
    lines = [f"# {original.stem}\n"]
    lines.extend(_rows_to_md_lines(_csv_rows(original)))
    target = _resolve_target(original, "_converted", "md", output_dir, output_path)
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def csv_to_pdf(source: str | os.PathLike, output_dir=None, output_path=None) -> Path:
    """Convert a CSV file to PDF (table as text only)."""
    original = Path(source)
    lines = [f"# {original.stem}\n"]
    lines.extend(_rows_to_md_lines(_csv_rows(original)))
    target = _resolve_target(original, "_converted", "pdf", output_dir, output_path)
    return _md_lines_to_pdf(lines, target)


def _html_to_md_lines(text: str) -> list[str]:
    """Readable Markdown lines from HTML: headings, paragraphs, lists.

    Tags, scripts, styles and CSS/layout are dropped; only the
    readable text survives, in document order.
    """
    from html.parser import HTMLParser

    class _Parser(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.lines: list[str] = []
            self._buf: list[str] = []
            self._skip = 0
            self._heading = 0

        def _flush(self, prefix=""):
            chunk = "".join(self._buf).strip()
            self._buf = []
            if chunk:
                self.lines.append((prefix + chunk) if prefix else chunk)

        def handle_starttag(self, tag, attrs):
            if tag in ("script", "style"):
                self._skip += 1
            elif tag.startswith("h") and len(tag) == 2 and tag[1].isdigit():
                self._flush()
                self._heading = int(tag[1])
            elif tag in ("p", "div", "tr", "section", "article"):
                self._flush()
            elif tag == "li":
                self._flush()
                self._buf.append("")  # marker replaced below
                self._buf = ["- "]
            elif tag == "br":
                self._flush()

        def handle_endtag(self, tag):
            if tag in ("script", "style"):
                self._skip = max(0, self._skip - 1)
            elif tag.startswith("h") and len(tag) == 2 and tag[1].isdigit():
                prefix = "#" * max(1, min(self._heading, 6)) + " "
                self._flush(prefix)
                self._heading = 0
            elif tag in ("p", "div", "li", "tr"):
                self._flush()

        def handle_data(self, data):
            if self._skip:
                return
            self._buf.append(data)

    parser = _Parser()
    parser.feed(text)
    parser._flush()
    return parser.lines


def html_to_md(source: str | os.PathLike, output_dir=None, output_path=None) -> Path:
    """Convert an HTML (.html/.htm) file to Markdown (readable text only)."""
    original = Path(source)
    lines = [f"# {original.stem}\n"]
    lines.extend(_html_to_md_lines(_read_text(original)))
    target = _resolve_target(original, "_converted", "md", output_dir, output_path)
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def html_to_pdf(source: str | os.PathLike, output_dir=None, output_path=None) -> Path:
    """Convert an HTML (.html/.htm) file to PDF (readable text only)."""
    original = Path(source)
    lines = [f"# {original.stem}\n"]
    lines.extend(_html_to_md_lines(_read_text(original)))
    target = _resolve_target(original, "_converted", "pdf", output_dir, output_path)
    return _md_lines_to_pdf(lines, target)


# Action id -> (button label, function), used by the ring menu.
ACTIONS = [
    ("PNG", convert_to_png),
    ("JPG", convert_to_jpg),
    ("WEBP", convert_to_webp),
    ("Compress", compress_image),
    ("Strip metadata", strip_metadata),
    ("White background", add_white_background),
    ("Image → PDF", image_to_pdf),
]

# .md files: MD -> PDF is the v0.2 headline; MD -> HTML and MD -> TXT
# are kept only as minor extras from the earlier (corrected) draft.
MD_ACTIONS = [
    ("MD → PDF", md_to_pdf),
    ("Clean MD", clean_md),
    ("MD → TXT", md_to_txt),
    ("MD → HTML", md_to_html),
]

# PDF files: one headline action.
PDF_ACTIONS = [
    ("PDF → MD", pdf_to_md),
]

# Word files: the two headline actions.
DOCX_ACTIONS = [
    ("DOCX → MD", docx_to_md),
    ("DOCX → PDF", docx_to_pdf),
]

# LibreOffice / OpenDocument files (v0.3, stdlib only).
ODT_ACTIONS = [
    ("ODT → MD", odt_to_md),
    ("ODT → PDF", odt_to_pdf),
]

ODS_ACTIONS = [
    ("ODS → MD", ods_to_md),
    ("ODS → CSV", ods_to_csv),
]

ODP_ACTIONS = [
    ("ODP → MD", odp_to_md),
    ("ODP → PDF", odp_to_pdf),
]

# Office / text formats (v0.5, stdlib parsing where possible).
XLSX_ACTIONS = [
    ("XLSX → MD", xlsx_to_md),
    ("XLSX → CSV", xlsx_to_csv),
    ("XLSX → PDF", xlsx_to_pdf),
]

PPTX_ACTIONS = [
    ("PPTX → MD", pptx_to_md),
    ("PPTX → PDF", pptx_to_pdf),
]

TXT_ACTIONS = [
    ("TXT → MD", txt_to_md),
    ("TXT → PDF", txt_to_pdf),
]

CSV_ACTIONS = [
    ("CSV → MD", csv_to_md),
    ("CSV → PDF", csv_to_pdf),
]

HTML_ACTIONS = [
    ("HTML → MD", html_to_md),
    ("HTML → PDF", html_to_pdf),
]

# One-line descriptions for the v0.5 conversion cards in the GUI.
# Keys are the action functions; unknown functions fall back to
# their button label in the GUI.
ACTION_DESCRIPTIONS = {
    convert_to_png: "Prevedie obrázok do PNG",
    convert_to_jpg: "Prevedie obrázok do JPG",
    convert_to_webp: "Prevedie obrázok do WEBP",
    compress_image: "Zmenší obrázok (nižšia kvalita / optimalizácia)",
    strip_metadata: "Odstráni EXIF a GPS metadáta",
    add_white_background: "Priehľadné pozadie nahradí bielym",
    image_to_pdf: "Vloží obrázok do PDF dokumentu",
    md_to_pdf: "Prevedie Markdown do PDF",
    clean_md: "Vyčistí Markdown (medzery navyše)",
    md_to_txt: "Prevedie Markdown na čistý text",
    md_to_html: "Prevedie Markdown do HTML stránky",
    pdf_to_md: "Vytiahne text z PDF do Markdownu",
    docx_to_md: "Vytiahne text z Wordu do Markdownu",
    docx_to_pdf: "Prevedie Word do PDF (len text)",
    odt_to_md: "Vytiahne text z LibreOffice Writer do Markdownu",
    odt_to_pdf: "Prevedie LibreOffice Writer do PDF (len text)",
    ods_to_md: "Prevedie tabuľky z Calcu do Markdownu",
    ods_to_csv: "Prevedie prvý hárok z Calcu do CSV",
    odp_to_md: "Vytiahne text zo slajdov do Markdownu",
    odp_to_pdf: "Prevedie prezentáciu do PDF (len text)",
    xlsx_to_md: "Prevedie hárky z Excelu do Markdownu",
    xlsx_to_csv: "Prevedie prvý hárok z Excelu do CSV",
    xlsx_to_pdf: "Prevedie Excel do PDF (len text)",
    pptx_to_md: "Vytiahne text zo slajdov do Markdownu",
    pptx_to_pdf: "Prevedie prezentáciu do PDF (len text)",
    txt_to_md: "Prevedie textový súbor do Markdownu",
    txt_to_pdf: "Prevedie textový súbor do PDF",
    csv_to_md: "Prevedie CSV tabuľku do Markdownu",
    csv_to_pdf: "Prevedie CSV tabuľku do PDF",
    html_to_md: "Vytiahne čitateľný text z HTML do Markdownu",
    html_to_pdf: "Prevedie HTML do PDF (len text)",
}

_IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff",
}


def actions_for_file(path: str | os.PathLike) -> list:
    """Only the actions that fit this file type (used by Drop window).

    Unknown extensions return [] instead of the image ring, so the
    Drop window never offers an action that cannot work on the file.
    Single-argument calls still work for every returned function.
    """
    suffix = Path(path).suffix.lower()
    if suffix in (".md", ".markdown"):
        return list(MD_ACTIONS)
    if suffix == ".pdf":
        return list(PDF_ACTIONS)
    if suffix == ".docx":
        return list(DOCX_ACTIONS)
    if suffix == ".odt":
        return list(ODT_ACTIONS)
    if suffix == ".ods":
        return list(ODS_ACTIONS)
    if suffix == ".odp":
        return list(ODP_ACTIONS)
    if suffix == ".xlsx":
        return list(XLSX_ACTIONS)
    if suffix == ".pptx":
        return list(PPTX_ACTIONS)
    if suffix == ".txt":
        return list(TXT_ACTIONS)
    if suffix == ".csv":
        return list(CSV_ACTIONS)
    if suffix in (".html", ".htm"):
        return list(HTML_ACTIONS)
    if suffix in _IMAGE_EXTENSIONS:
        return list(ACTIONS)
    return []


# (suffix, extension) per file action, for the "ask for output file"
# Save dialog prefill. Compress / strip keep the source extension.
_ACTION_OUTPUT = {
    convert_to_png: ("_converted", "png"),
    convert_to_jpg: ("_converted", "jpg"),
    convert_to_webp: ("_converted", "webp"),
    image_to_pdf: ("_converted", "pdf"),
    add_white_background: ("_whitebg", "png"),
    md_to_pdf: ("_converted", "pdf"),
    clean_md: ("_clean", "md"),
    md_to_txt: ("_converted", "txt"),
    md_to_html: ("_converted", "html"),
    pdf_to_md: ("_converted", "md"),
    docx_to_md: ("_converted", "md"),
    docx_to_pdf: ("_converted", "pdf"),
    odt_to_md: ("_converted", "md"),
    odt_to_pdf: ("_converted", "pdf"),
    ods_to_md: ("_converted", "md"),
    ods_to_csv: ("_converted", "csv"),
    odp_to_md: ("_converted", "md"),
    odp_to_pdf: ("_converted", "pdf"),
    xlsx_to_md: ("_converted", "md"),
    xlsx_to_csv: ("_converted", "csv"),
    xlsx_to_pdf: ("_converted", "pdf"),
    pptx_to_md: ("_converted", "md"),
    pptx_to_pdf: ("_converted", "pdf"),
    txt_to_md: ("_converted", "md"),
    txt_to_pdf: ("_converted", "pdf"),
    csv_to_md: ("_converted", "md"),
    csv_to_pdf: ("_converted", "pdf"),
    html_to_md: ("_converted", "md"),
    html_to_pdf: ("_converted", "pdf"),
}


def default_output_for(source, func, output_dir=None) -> Path:
    """Proposed (non-existing) output path for ``func`` on ``source``.

    Used to prefill the Save dialog when "ask for output file" is on.
    Respects the chosen output folder; the _2/_3 rule applies here
    too, so the prefilled name is one that does not exist yet.
    """
    original = Path(source)
    if func in (compress_image, strip_metadata):
        suffix = "_compressed" if func is compress_image else "_clean"
        return _unique_output(
            original, suffix, _image_extension(original), output_dir=output_dir
        )
    try:
        suffix, extension = _ACTION_OUTPUT[func]
    except KeyError as exc:
        raise ValueError(f"No default output known for this action: {func}") from exc
    return _unique_output(original, suffix, extension, output_dir=output_dir)
