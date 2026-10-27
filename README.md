# CONVERTOR-APP — v0.2

A local desktop file converter, vibecoded from scratch as an
original implementation. It is **inspired by** the idea of a desktop
pet that opens a ring of file actions — no code, artwork, or text
was copied from any existing app of that kind.

## Two ways to use it (both local, both GUI)

1. **Main window** (`python main.py`) — the full local control
   panel, in the spirit of a launcher window, written from scratch
   in PySide6: sections for File, Conversions, Text, and a
   timestamped Log console showing what was converted and where
   it was saved.
2. **Floating widget** — the quick path: a small, always-on-top,
   draggable widget. Drag a file onto it and a ring of actions
   opens around it. Toggle it from the main window
   ("Floating widget: show / hide").

## What it does (v0.2 — main features)

Document conversions (the v0.2 headline, per the user's correction
— MD → HTML is **not** a headline feature):

1. **PDF → MD** — extract a PDF's text into Markdown, one
   `## Page N` section per page (PyMuPDF)
2. **Word (.docx) → MD** — headings, paragraphs, simple lists
   and tables to Markdown (python-docx)
3. **MD → PDF** — Markdown to PDF, headings / lists / code
   blocks rendered with reportlab
4. **Word (.docx) → PDF** — same PDF rendering from Word text

Plus, kept from v0.1 / the earlier draft:

- **Images:** PNG, JPG, Compress, Strip metadata, White background
- **MD extras (minor, not headline):** MD → TXT (syntax stripped),
  MD → HTML (standalone file), Clean MD (trailing whitespace out)
- **Text without a file:** main window "Paste text…" or the
  widget's **Text** button opens a paste dialog (GUI, not CLI).
  Its ring / save dialog offers: Save .md, Save .txt, To PDF,
  Copy to clipboard — and, in the main window, one save dialog
  with a format choice.

## Never overwrite, Desktop default for text

- Every action writes a **new file** and the original is
  **never overwritten**. File drops save next to the original
  (`name_converted.md`, `name_converted.pdf`, …); if the target
  name already exists, `_2`, `_3`, … is appended.
- Pasted-text saves **default to the Desktop (Plocha)** on
  Windows, with a `text-<date>.md/.txt/.pdf` default name and
  the same `_2`/`_3` rule — never to the app/widget folder.
  (Fallbacks if Desktop is missing: Plocha, Documents, home.)
- Everything runs locally. No upload, no account, no keys,
  no network calls, no telemetry.

## Honest limitations (not faked)

- PDF/DOCX → PDF keeps **text, headings and simple lists**.
  Images, complex tables and exact Word/PDF layout are **not**
  preserved — this is a text converter, not a layout clone.
- Scanned / image-only PDFs have no extractable text, so
  PDF → MD on those yields (nearly) empty output.
- Non-image, non-document files dropped on the widget still
  show the image ring, which fails gracefully on them.

## Run on Windows

```powershell
pip install -r requirements.txt
python main.py
```

Then: pick a file (or drag it onto the main window or the
widget), click a conversion, and check the Log for where the
new file was saved. Or click "Paste text…" / the widget's
**Text** button and save to the Desktop.

## TODO (not in v0.2 — not faked as working)

- **Shift-mode:** hold a file and press Shift to open the same
  ring under the cursor, anywhere on screen. This needs a
  system-wide file-drag hook on Windows, which PySide6 alone
  does not provide.
- PDF conversion of scanned PDFs (OCR), crop, annotate, redact,
  and brightness / contrast editing are not in v0.2 yet.

## Status / testing

- Code compiles with `python3 -m py_compile` on all `.py` files.
- The action functions were run against test PDF / DOCX / MD
  files and pasted text on Linux (PyMuPDF, python-docx,
  reportlab, Pillow, markdown only) — see the verification note
  in the project report.
- **Real Windows GUI run/test has NOT been done yet** (built on
  a Linux VM without PySide6 GUI or Windows). The user must run
  `python main.py` on his Windows PC and check: main window
  opens, file pick + drop work, each of the 4 document
  conversions saves a new file, text saves default to Desktop,
  floating widget toggles, and the Log shows every result.

## Layout

```
main.py                 entry point -> main GUI window
requirements.txt        PySide6 + Pillow + Markdown + PyMuPDF
                        + python-docx + reportlab
beaver/
  __init__.py
  actions.py            pure actions (no Qt, testable alone):
                        images, Markdown, text, PDF/DOCX docs
  widget.py             floating widget + ring menu + paste dialog
  gui.py                main window: sections, buttons, log console
```
