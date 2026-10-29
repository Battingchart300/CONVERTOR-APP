# CONVERTOR-APP — v0.5

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

## What it does (v0.5 — new: more files, refined GUI, better functions, update check)

### 1. More supported files (stdlib parsing where possible)

- **Excel (.xlsx) → MD / CSV / PDF** — sheets as Markdown
  tables, CSV = first sheet only, PDF = tables as text. Values
  only: formulas are read as their stored (cached) value and
  are **not** recalculated.
- **PowerPoint (.pptx) → MD / PDF** — slide text only, one
  `## Slide N` section per slide. Layout, images, charts and
  animations are **not** preserved.
- **Text (.txt) → MD / PDF** and **CSV → MD / PDF** — CSV
  first row = header for the Markdown table.
- **HTML (.html / .htm) → MD / PDF** — readable text only:
  headings, paragraphs and lists survive; tags, scripts,
  styles and CSS/layout are dropped.
- **Image → PDF** (the image rendered into a single-page PDF)
  and **Image → WEBP** (quality 90) — added to the image
  actions, so images now have 7 actions: PNG, JPG, WEBP,
  Compress, Strip metadata, White background, Image → PDF.
- All new types are routed through the same
  `actions_for_file()` as before, so the smart Conversions
  section and the Drop window suggest only fitting actions
  for them, and unknown types still get no actions.

### 2. Refined GUI

- **Conversion cards:** each suggested conversion is now a
  card — a button plus a one-line description, e.g.
  "DOCX → MD — vytiahne text do Markdownu".
- **File info panel:** under section 1, the picked file's
  name, recognised type label and human-readable size
  (B / KB / MB).
- **After a conversion:** the status is logged, the
  conversion is added to the session history (below), and an
  **"Otvoriť priečinok"** button opens the output folder
  (Qt QDesktopServices, cross-platform).

### 3. Better functions

- **Hromadná konverzia (batch):** "Hromadná konverzia…" in
  section 1 opens a dialog: pick many files, they are grouped
  by type, pick one conversion per group, and it runs for
  every file in that group. Each result is logged, successes
  and failures are counted in a summary, Output settings and
  the never-overwrite rule apply. The per-file "ask for
  output file" dialog is deliberately NOT shown per file in
  batch mode (it would prompt for every file).
- **Image quality settings:** Settings (gear button) now has
  an Obrázky section — JPG kvalita (default 92, as before)
  and kvalita kompresie JPG (default 70, as before), both
  10–100, persisted in the existing settings file. The
  floating widget keeps the old defaults (it does not read
  these two settings).
- **History:** "Posledné konverzie (táto relácia)" under the
  Log lists file → output for conversions in this session
  (max 50, oldest dropped). It is session-only, not saved
  to disk.

### 4. Update check — automatic at startup + manual in Settings

- **Automatic:** about 1 second after the main window shows,
  the app runs a short-timeout `git fetch origin` and compares
  local HEAD with origin/main. If up-to-date or offline, it
  stays silent. If an update is actually available, it logs
  it and shows a top-row **"Aktualizácia k dispozícii"**
  button, which runs the update on click.
- **Manual:** Settings → **Aktualizácie** has a
  "Skontrolovať aktualizácie" button, a status line (current
  commit, remote commit, up-to-date / available / offline)
  and an "Aktualizovať" button, enabled only when an update
  is available. Updating runs `git pull origin main` and
  then tells the user to restart the app — the app does
  **not** force-restart itself, because on Windows the
  running files may be locked.
- **Never crashes the app:** no git repo, no internet, a
  timeout (~10 s for fetch) or any git error returns an
  offline/error status, never an exception. The check uses
  stdlib + git subprocess only — no new dependency.

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
- **Obrázky (new in v0.5):** JPG kvalita (default 92) and
  kvalita kompresie JPG (default 70), both 10–100.
- **Aktualizácie (new in v0.5):** "Skontrolovať
  aktualizácie" button, status text, and an "Aktualizovať"
  button (enabled only when an update is available) — see
  the v0.5 update-check section above.
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

- **Images:** PNG, JPG, WEBP, Compress, Strip metadata, White background, Image → PDF
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
- v0.5 specifics: XLSX formulas are read as their cached
  value, not recalculated, and XLSX → CSV is the first sheet
  only; PPTX keeps slide text only (no layout, images or
  charts); HTML keeps readable text only (no CSS/layout);
  image → PDF renders one image per PDF file.
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
  window opens (title v0.5), file pick + drop work, Output
  folder + "ask for output file" work on an image and a
  document, Drop window opens / asks / runs / logs, each ODF
  conversion saves a new file, text saves default to Desktop,
  floating widget toggles, and the Log shows every result.
  Also check the new smart Conversions: with no file picked,
  section 3 shows only the hint and no buttons; picking a
  .docx shows only DOCX → MD and DOCX → PDF with a
  recognition label; picking an image shows only the seven
  image actions; an unsupported file (e.g. .exe) shows the
  "not supported yet" message and no buttons.
  Also check Settings: the gear button "⚙ Nastavenia" is in
  the top row (title left, gear right), the dialog opens,
  Save persists and updates section 2, Cancel changes nothing,
  Reset to defaults works, settings survive a restart (and
  live in ~/.convertor-app/settings.json, not in the repo),
  and "show widget at startup" opens the widget with the
  main window.
  **New in v0.5 to check:** conversion cards show a
  description next to each button; the file-info line shows
  name, type and size; batch conversion groups files by type
  and runs one conversion per group; JPG/compress quality in
  Settings changes JPG output; the history list fills and
  "Otvoriť priečinok" opens the output folder; Settings →
  Aktualizácie checks and (when an update exists) updates,
  and at startup an available update shows the top-row
  notice without blocking startup or popping up when
  up-to-date/offline. v0.5 action tests: 31/31 passed on
  Linux (synthetic XLSX/PPTX/TXT/CSV/HTML, image, MD and
  ODT regression, routing, settings, update-check
  non-repo case).

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
                        gear button + update notice), File (with
                        file info + batch button) / Output /
                        smart Conversions as cards (dynamic, via
                        actions_for_file) / Text / Log / session
                        history, plus Drop window + action choice
                        dialog + Settings dialog + batch dialog
  settings.py           user settings (stdlib only, no Qt):
                        ~/.convertor-app/settings.json, defaults
                        + safe fallback on a missing/corrupt file,
                        now also JPG / compress quality
  update_check.py       update check (stdlib + git subprocess):
                        fetch + HEAD vs origin/main, never raises
```
