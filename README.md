# CONVERTOR-APP — v0.5.2

Local desktop file converter for Windows. Pick a file, get only the conversions that fit it, and save a new file — the original is never overwritten.

No upload, no account, no keys, no telemetry. Everything runs locally.

## What it does

| Input | Output |
|---|---|
| Image (PNG / JPG / WEBP) | PNG, JPG, WEBP, compress, strip metadata (EXIF/GPS), white background, image → PDF |
| PDF | → Markdown (text, one section per page) |
| Word (.docx) | → Markdown, → PDF |
| Excel (.xlsx) | → Markdown, → CSV (first sheet), → PDF |
| PowerPoint (.pptx) | → Markdown, → PDF (slide text only) |
| Text / CSV / HTML | → Markdown, → PDF |
| LibreOffice (.odt / .ods / .odp) | → Markdown, → PDF / CSV |
| Pasted text | Save as .md / .txt / .pdf, or copy to clipboard |

Plus: batch conversion (many files, grouped by type), session history, configurable output folder, and an update check that restarts the app itself after a successful update (v0.5.2).

## Three ways to use it

1. **Main window** — `python main.py`. Full control panel: file, output, smart conversions, text, timestamped log.
2. **Drop window** — drop a file, the app asks what to do with it and shows only fitting actions.
3. **Floating widget** — small always-on-top widget. Drag a file onto it and a ring of actions opens around it.

## Quick start (Windows)

```powershell
pip install -r requirements.txt
python main.py
```

Pick a file (or drag it in), click a conversion, check the Log for where the new file was saved.

Settings live outside the repo in `~/.convertor-app/settings.json`, so `git pull` never overwrites them.

## Tech

Python + PySide6, Pillow, PyMuPDF, python-docx, reportlab, Markdown. OpenDocument support uses stdlib only (`zipfile` + XML) — no extra dependency.

## Project structure

```
main.py               entry point -> main GUI window
requirements.txt      PySide6 + Pillow + Markdown + PyMuPDF + python-docx + reportlab
beaver/
  actions.py          pure actions (no Qt, testable alone)
  gui.py              main window, Drop window, Settings, batch, update
  widget.py           floating widget + ring menu
  settings.py         user settings (stdlib only, safe fallback)
  update_check.py     update check + auto-restart after update
```

## Honest limitations

- Document → PDF keeps text, headings and simple lists. Images, complex tables and exact layout are **not** preserved — this is a text converter, not a layout clone.
- Formulas are read as their stored (cached) value, not recalculated. XLSX / ODS → CSV is the first sheet only.
- Scanned / image-only PDFs have no extractable text, so PDF → Markdown on those yields (nearly) empty output.
- The Windows GUI run of v0.5.2 has not been tested yet — code compiles and the actions were tested on Linux (31/31 checks in v0.5). See [CHANGELOG.md](CHANGELOG.md) for the full version history and test notes.

## License

MIT — see [LICENSE](LICENSE).
