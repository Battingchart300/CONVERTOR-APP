# CONVERTOR-APP — v0.4

A local desktop file converter, vibecoded from scratch as an
original implementation. It is **inspired by** the idea of a desktop
pet that opens a ring of file actions — no code, artwork, or text
was copied from any existing app of that kind.

## Three ways to use it (all local, all GUI)

1. **Main window** (`python main.py`) — the full local control
   panel, in the spirit of a launcher window, written from scratch
   in PySide6: sections for File, Output, Conversions, Text, and
   a timestamped Log console showing what was converted and
   where it was saved.
2. **Drop window** (new in v0.3) — from the main window, "Drop
   window…" opens a small always-on-top window with a big drop
   area. Dropping a single file there AUTOMATICALLY asks what
   to do with it, listing only the actions that fit that file
   type. The chosen action respects the Output settings, logs
   in the main window, and shows a Done message.
3. **Floating widget** — the quick path: a small, always-on-top,
   draggable widget. Drag a file onto it and a ring of actions
   opens around it. Toggle it from the main window
   ("Floating widget: show / hide").

## What it does (v0.4 — new: smart Conversions)

Section **3. Conversions** in the main window no longer shows
all 18 buttons at once, regardless of file type. The flow is
now exactly three steps:

1. **Pick a file** — "Pick file…" in section 1, or drag a file
   onto the main window. Picking / dropping still does NOT
   convert anything by itself.
2. **The app recognises it** — by file type, and shows a
   recognition label in plain words, e.g. "Rozpoznal som:
   Word dokument (.docx)", "PDF dokument (.pdf)", "Obrázok
   (.png)", "LibreOffice Writer dokument (.odt)".
3. **Only the suggested conversions are shown** — for a .docx
   only DOCX → MD and DOCX → PDF, for an image only the five
   image actions, and so on. Nothing that cannot work on the
   picked file is offered.

With **no file picked**, section 3 shows only a hint
("Vyber súbor a ukážem len konverzie preň.") and no buttons.
For an **unknown / unsupported type** (e.g. `.exe`) it shows
a clear "Tento typ súboru zatiaľ nepodporujem" message, no
buttons, and a log line — never an empty list and never the
full list.

The routing is the existing `actions_for_file()` from
`actions.py` — the same routing the Drop window already uses,
so there is no second list to drift out of sync. Everything
else is unchanged: Output section + Settings sync, the gear
"⚙ Nastavenia" button, Drop window behaviour, Text section,
Log, and the never-overwrite rule.

## What it does (v0.3 — new features)

### 1. Configurable output file (new in v0.3)

Section **2. Output** in the main window:

- **"Next to original (default)"** — the v0.1/v0.2 behaviour.
- **"Folder:" + Browse…** — pick any folder; all file actions
  (image, document and the new LibreOffice actions) save there
  instead of next to the original.
- **"Ask for output file before each conversion"** — when on,
  a Save dialog prefilled with the proposed name opens before
  each file action, so the output can be renamed / relocated
  on the spot. The never-overwrite rule still applies to the
  chosen path (an existing name becomes `_2`, `_3`, …), and
  the file extension is forced to the action's real format.
- Pasted-text saving is unchanged: it keeps its own save
  dialog (default Desktop), it is NOT affected by this section.

### 2. Drop window (new in v0.3)

See "Three ways to use it" above. Dropping onto the MAIN
window is unchanged: it only sets the picked file, it does
not convert it. Dropping a folder, or a file type with no
fitting action (e.g. `.exe`), shows a warning instead of an
empty action list.

### Settings — gear button in the top row (new in v0.3)

At the top of the main window: the app title on the left, and
on the right a **"⚙ Nastavenia"** gear button. Clicking the
gear opens the Settings dialog — Settings is NOT buried as a
plain button inside a lower section.

- **Output:** output mode (next to original / folder),
  output folder, and "Ask for output file before each
  conversion". Changing section **2. Output** in the main
  window also saves here, and saving in Settings updates
  section 2 to match — they stay in sync.
- **Text:** default folder for pasted-text saves. The main
  window's "Paste text…" dialog (and the floating widget's
  paste dialogs, when opened from the main window) default
  to this folder; if it is missing, the Desktop default
  is used instead.
- **Widget:** "Show floating widget at startup" — when on,
  the floating widget opens together with the main window.
- **Save** applies immediately (writes the file, updates
  section 2, logs in the main window), **Cancel** changes
  nothing, **Reset to defaults** restores the default
  values in the dialog (saved only when Save is clicked).

Settings are stored **outside the repo**, in the user's
home folder — `~/.convertor-app/settings.json` (on Windows:
`C:\Users\<name>\.convertor-app\settings.json`) — so a later
`git pull` never overwrites them. A missing or corrupt
settings file never crashes the app: it falls back to the
defaults (output next to original, no ask dialog, text to
Desktop, widget off at startup).

### 3. LibreOffice / OpenDocument support (new in v0.3)

Built with **Python stdlib only** (`zipfile` + XML parsing) —
**no new dependency, nothing added to `requirements.txt`**
(deliberately: no `odfpy`, so no new library-update risk):

1. **ODT → MD** and **ODT → PDF** — Writer documents
2. **ODS → MD** (all sheets as Markdown tables) and
   **ODS → CSV** (first sheet only)
3. **ODP → MD** (one `## Slide N` section per slide) and
   **ODP → PDF**

### Older features (kept)

Document conversions (the v0.2 headline — MD → HTML is **not**
a headline feature):

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
  **never overwritten**. By default file actions save next to
  the original (`name_converted.md`, `name_converted.pdf`, …);
  if the target name already exists, `_2`, `_3`, … is appended.
  The same rule applies to a chosen output folder and to a
  path picked in the "ask for output file" Save dialog.
- Pasted-text saves **default to the Desktop (Plocha)** on
  Windows, with a `text-<date>.md/.txt/.pdf` default name and
  the same `_2`/`_3` rule — never to the app/widget folder.
  (Fallbacks if Desktop is missing: Plocha, Documents, home.)
- Everything runs locally. No upload, no account, no keys,
  no network calls, no telemetry.

## Honest limitations (not faked)

- PDF/DOCX/ODT/ODP → PDF keeps **text, headings and simple
  lists**. Images, complex tables and exact Word/PDF/ODF
  layout are **not** preserved — this is a text converter,
  not a layout clone.
- ODF specifics: styles, fonts and colours are not preserved;
  spreadsheet formulas are read as their stored text, not
  recalculated; ODS → CSV converts the first sheet only.
- Scanned / image-only PDFs have no extractable text, so
  PDF → MD on those yields (nearly) empty output.
- Non-image, non-document files dropped on the widget still
  show the image ring, which fails gracefully on them. (The
  Drop window, by contrast, refuses them with a warning.)

## Run on Windows

```powershell
pip install -r requirements.txt
python main.py
```

Then: pick a file (or drag it onto the main window or the
widget), click a conversion, and check the Log for where the
new file was saved. Or click "Drop window…", drop a file
there and pick an action. Or click "Paste text…" / the
widget's **Text** button and save to the Desktop.

## TODO (not in v0.3 — not faked as working)

- **Shift-mode:** hold a file and press Shift to open the same
  ring under the cursor, anywhere on screen. This needs a
  system-wide file-drag hook on Windows, which PySide6 alone
  does not provide.
- PDF conversion of scanned PDFs (OCR), crop, annotate, redact,
  and brightness / contrast editing are not in v0.3 yet.

## Status / testing

- Code compiles with `python3 -m py_compile` on all `.py` files.
- The action functions were run against synthetic ODT / ODS /
  ODP files (built as ZIP + `content.xml` in `/tmp`) and
  regression-tested image / MD / DOCX / PDF actions on Linux
  (Pillow, python-docx, reportlab, PyMuPDF, markdown in a
  throwaway venv) — 26/26 checks passed, see the project report.
- **Real Windows GUI run/test has NOT been done yet** (built
  on a headless Linux VM; a PySide6 live run was not possible
  there, and the GUI was only compile-checked). The user must
  run `python main.py` on his Windows PC and check: main
  window opens (title v0.4), file pick + drop work, Output
  folder + "ask for output file" work on an image and a
  document, Drop window opens / asks / runs / logs, each ODF
  conversion saves a new file, text saves default to Desktop,
  floating widget toggles, and the Log shows every result.
  Also check the new smart Conversions: with no file picked,
  section 3 shows only the hint and no buttons; picking a
  .docx shows only DOCX → MD and DOCX → PDF with a
  recognition label; picking an image shows only the five
  image actions; an unsupported file (e.g. .exe) shows the
  "not supported yet" message and no buttons.
  Also check Settings: the gear button "⚙ Nastavenia" is in
  the top row (title left, gear right), the dialog opens,
  Save persists and updates section 2, Cancel changes nothing,
  Reset to defaults works, settings survive a restart (and
  live in ~/.convertor-app/settings.json, not in the repo),
  and "show widget at startup" opens the widget with the
  main window.

## Layout

```
main.py                 entry point -> main GUI window
requirements.txt        PySide6 + Pillow + Markdown + PyMuPDF
                        + python-docx + reportlab (UNCHANGED in v0.3)
beaver/
  __init__.py
  actions.py            pure actions (no Qt, testable alone):
                        images, Markdown, text, PDF/DOCX docs,
                        OpenDocument (stdlib only), shared
                        output resolution + actions_for_file
  widget.py             floating widget + ring menu + paste dialog
                        (now also routes .odt/.ods/.odp; its paste
                        dialogs use the text_folder setting when
                        opened from the main window)
  gui.py                main window: top row (title + ⚙ Nastavenia
                        gear button), File / Output / smart
                        Conversions (dynamic, via actions_for_file)
                        / Text / Log, plus Drop window + action
                        choice dialog + Settings dialog
  settings.py           user settings (stdlib only, no Qt):
                        ~/.convertor-app/settings.json, defaults
                        + safe fallback on a missing/corrupt file
```
