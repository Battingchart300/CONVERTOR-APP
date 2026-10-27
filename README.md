# File utility widget — prototype v0.1

A small floating desktop widget, vibecoded from scratch as an
original implementation. It is **inspired by** the idea of a desktop
pet that opens a ring of file actions — no code, artwork, or text
was copied from any existing app of that kind.

## What it does (v0.1)

- A small, always-on-top, draggable widget sits on the desktop.
- Drag a file onto it and a ring menu opens around it with:
  1. **PNG** — convert image to PNG
  2. **JPG** — convert image to JPG
  3. **Compress** — smaller re-save (JPEG quality 70, others optimized)
  4. **Strip metadata** — copy with no EXIF / GPS / text metadata
  5. **White background** — composite a transparent image onto white
- Every action writes a **new file next to the original**
  (`name_converted.png`, `name_compressed.jpg`, `name_clean.jpg`,
  `name_whitebg.png`, …). The original is **never overwritten**.
  If the target name already exists, `_2`, `_3`, … is appended.
- A small success / failure message is shown after each action.
- Everything runs locally. No upload, no account, no keys,
  no network calls, no telemetry.

## Run on Windows

```powershell
pip install -r requirements.txt
python main.py
```

Then drag an image file onto the widget and click an action
in the ring.

## TODO (not in v0.1 — not faked as working)

- **Shift-mode:** hold a file and press Shift to open the same
  ring under the cursor, anywhere on screen. This needs a
  system-wide file-drag hook on Windows, which PySide6 alone
  does not provide — it is the next step, not implemented here.
- PDF conversion, crop, annotate, redact, and brightness /
  contrast editing are not in v0.1 yet.
- Non-image files currently show a failure message instead of
  an action (the ring actions are image actions in v0.1).

## Status / testing

- Code compiles with `python3 -m py_compile` on all `.py` files.
- The action functions were run against a test image on Linux
  (Pillow only) — see the verification note in the project report.
- **Real Windows GUI run/test has NOT been done yet** (this
  prototype was built on a Linux VM without PySide6 or Windows).
  The user must run `python main.py` on his Windows PC and
  check: widget drags, drop opens the ring, each of the 5
  actions saves a new file next to the original.

## Layout

```
main.py                 entry point
requirements.txt        PySide6 + Pillow
beaver/
  __init__.py
  actions.py            pure Pillow actions (no Qt, testable alone)
  widget.py             floating widget + ring menu (PySide6)
```
