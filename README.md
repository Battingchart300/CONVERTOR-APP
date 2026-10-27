# File utility widget — prototype v0.2

A small floating desktop widget, vibecoded from scratch as an
original implementation. It is **inspired by** the idea of a desktop
pet that opens a ring of file actions — no code, artwork, or text
was copied from any existing app of that kind.

## What it does (v0.2)

- A small, always-on-top, draggable widget sits on the desktop.
- Drag an **image** onto it and a ring menu opens around it with:
  1. **PNG** — convert image to PNG
  2. **JPG** — convert image to JPG
  3. **Compress** — smaller re-save (JPEG quality 70, others optimized)
  4. **Strip metadata** — copy with no EXIF / GPS / text metadata
  5. **White background** — composite a transparent image onto white
- Drag a **.md file** onto it and the ring instead offers:
  1. **MD → HTML** — standalone `.html` file next to the original
     (rendered with the `markdown` package, fenced code + tables)
  2. **MD → TXT** — plain text with Markdown syntax stripped
     (hand-written stripping code, no copied library)
  3. **Clean MD** — cleaned copy: trailing whitespace removed,
     runs of 3+ blank lines collapsed to 2, no content lines lost
- **Text without a file:** click the **Text** button under the
  widget, paste/type text, and its own ring offers:
  1. **Save .md** — save dialog, defaults to
     `Documents/text-<date>.md`
  2. **Save .txt** — same, `.txt`
  3. **To HTML** — same, standalone `.html` rendered from Markdown
  4. **Copy** — copy the pasted text to the clipboard
- Every action writes a **new file** and the original is
  **never overwritten**. File drops save next to the original
  (`name_converted.html`, `name_clean.md`, …); pasted-text saves
  use the dialog's chosen path. If the target name already
  exists, `_2`, `_3`, … is appended.
- A small success / failure message is shown after each action.
- Everything runs locally. No upload, no account, no keys,
  no network calls, no telemetry.

## Run on Windows

```powershell
pip install -r requirements.txt
python main.py
```

Then drag an image or .md file onto the widget, or click
**Text** under it and paste text, and click an action in the ring.

## TODO (not in v0.2 — not faked as working)

- **Shift-mode:** hold a file and press Shift to open the same
  ring under the cursor, anywhere on screen. This needs a
  system-wide file-drag hook on Windows, which PySide6 alone
  does not provide — it is the next step, not implemented here.
- PDF conversion, crop, annotate, redact, and brightness /
  contrast editing are not in v0.2 yet.
- Non-image, non-Markdown files dropped on the widget still
  show the image ring, which fails gracefully on them.

## Status / testing

- Code compiles with `python3 -m py_compile` on all `.py` files.
- The action functions were run against test .md and test text
  on Linux (Pillow + markdown only) — see the verification note
  in the project report.
- **Real Windows GUI run/test has NOT been done yet** (this
  prototype was built on a Linux VM without PySide6 or Windows).
  The user must run `python main.py` on his Windows PC and
  check: widget drags, image drop opens the image ring, .md
  drop opens the MD ring, Text button opens the paste dialog
  and its ring, and every action saves a new file without
  overwriting.

## Layout

```
main.py                 entry point
requirements.txt        PySide6 + Pillow + Markdown
beaver/
  __init__.py
  actions.py            pure actions (no Qt, testable alone):
                        images (Pillow), Markdown + text
  widget.py             floating widget + ring menu (PySide6),
                        paste dialog for text-only input
```
