"""Main local GUI window for CONVERTOR-APP (v0.8.0).

One clear flow for ordinary users (v0.6.1): the "Konvertor" tab is
just three steps — 1. pick a file, 2. pick what to make of it,
3. one big "Konvertovať" button — plus a plain result line.
Advanced stuff (text paste, drop window, batch, widget toggle)
lives on the "Ďalšie" tab. In v0.8 the log and history moved
out of the main window entirely — they live in Settings
("Nastavenia → Log a história"), because the first real user
called them unnecessary on the main screen. The look stays
the default dark + teal design, but Settings → Vzhľad lets
the user pick another theme and always offers "Obnoviť
predvolený vzhľad" to get the default back.
All GUI strings are Slovak, no jargon; errors are explained in
plain words.

Layout:
  Header — app name + subtitle "Lokálny konvertor — bez cloudu,
  bez účtu", version badge, update notice, gear "⚙ Nastavenia".
  Tab "Konvertor": step 1 (big drop zone + file info), step 2
  (radio choice of only the conversions that fit the file),
  step 3 (one big Konvertovať button + result line), and one
  line saying where the new file will be saved.
  Tab "Ďalšie": text paste, drop window, batch, widget toggle.
  Settings: Output, Text, Widget, Images, Updates, Vzhľad
  (theme), Log a história (read-only log + session history).

Behaviour is unchanged from v0.6 apart from the layout: smart
Conversions (only the actions that fit the picked file), Output
settings in the Settings dialog, Drop window (auto-ask dialog),
Batch conversion, Text paste, Floating widget toggle, automatic
startup update check + manual check in Settings, auto-restart
after a successful update.

Everything runs locally. No upload, no account, no keys, no network.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .actions import (
    ACTION_DESCRIPTIONS,
    actions_for_file,
    compress_image,
    convert_to_jpg,
    default_output_for,
    default_text_dir,
    default_text_filename,
    save_text_to_path,
    text_to_pdf_path,
)
from .settings import default_settings, load_settings, save_settings
from .themes import (
    DEFAULT_THEME,
    result_style,
    stylesheet_for,
    theme_label,
    theme_names,
)
from .update_check import check_update, local_version, run_update, spawn_restart
from .widget import FloatingWidget, TextDialog


def _stamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


# Human-readable Slovak labels for the recognition line in the
# Conversions section (v0.4). Image types share one wording with
# the real extension shown, so ".jpg" reads as an image too.
_FILE_TYPE_LABELS = {
    ".md": "Markdown dokument (.md)",
    ".markdown": "Markdown dokument (.md)",
    ".pdf": "PDF dokument (.pdf)",
    ".docx": "Word dokument (.docx)",
    ".odt": "LibreOffice Writer dokument (.odt)",
    ".ods": "LibreOffice Calc tabuľka (.ods)",
    ".odp": "LibreOffice Impress prezentácia (.odp)",
    ".xlsx": "Excel tabuľka (.xlsx)",
    ".pptx": "PowerPoint prezentácia (.pptx)",
    ".txt": "Textový súbor (.txt)",
    ".csv": "CSV tabuľka (.csv)",
    ".html": "HTML stránka (.html)",
    ".htm": "HTML stránka (.htm)",
    ".png": "Obrázok (.png)",
    ".jpg": "Obrázok (.jpg)",
    ".jpeg": "Obrázok (.jpeg)",
    ".bmp": "Obrázok (.bmp)",
    ".gif": "Obrázok (.gif)",
    ".webp": "Obrázok (.webp)",
    ".tif": "Obrázok (.tif)",
    ".tiff": "Obrázok (.tiff)",
}


def _file_type_label(path: Path) -> str:
    """Plain-words label for a file type, or "" if unknown."""
    return _FILE_TYPE_LABELS.get(path.suffix.lower(), "")


def _format_size(size: int) -> str:
    """Human-readable file size: B, KB or MB (1 decimal)."""
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def _friendly_error(exc: Exception) -> str:
    """Plain-Slovak explanation of a failed conversion (no jargon).

    The technical detail (exception text) stays in the log only —
    the user sees this. Actions raise ValueError("Not a readable
    ...") for unreadable or corrupt files.
    """
    text = str(exc)
    if isinstance(exc, ValueError) and "readable" in text:
        return (
            "Súbor sa nepodarilo prečítať. Skús iný súbor, "
            "alebo skontroluj, či nie je poškodený."
        )
    if isinstance(exc, FileNotFoundError):
        return "Súbor sa nenašiel. Možno bol medzitým presunutý alebo zmazaný."
    if isinstance(exc, PermissionError):
        return (
            "Nemám povolenie zapisovať do tohto priečinka. "
            "Skús iný priečinok pre výstup."
        )
    return "Niečo sa nepodarilo. Skús to znova, alebo vyber iný súbor."


# Default theme stylesheet (v0.8): the v0.6 dark + teal design,
# built from beaver/themes.py. The app applies the SAVED theme
# at startup (see main() below); this constant is only the
# fallback when no settings exist yet.
STYLESHEET = stylesheet_for(DEFAULT_THEME)


class _DropZone(QFrame):
    """Large drop area at the top of the Konvertor tab (v0.6).

    Clicking it opens the file picker; dropping a file on it
    sets the picked file (it never converts by itself — the
    smart Conversion cards below do that).
    """

    def __init__(self, main_window):
        super().__init__()
        self._main = main_window
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(110)
        layout = QVBoxLayout(self)
        title = QLabel("Pretiahni sem súbor")
        title.setObjectName("dropZoneTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub = QLabel("alebo klikni a vyber súbor")
        sub.setObjectName("dropZoneSub")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(sub)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._main._pick_file()
        super().mousePressEvent(event)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        urls = event.mimeData().urls()
        if not urls:
            return
        path = Path(urls[0].toLocalFile())
        if path.is_file():
            self._main._set_file(path)
        else:
            self._main.log("Pretiahni jeden súbor, nie priečinok.")


class ActionChoiceDialog(QDialog):
    """Ask what to do with a dropped file (Drop window only).

    Lists ONLY the actions that fit the file type. ``chosen`` is the
    selected action function, or None if the dialog was cancelled.
    """

    def __init__(self, parent, path: Path, actions):
        super().__init__(parent)
        self.setWindowTitle("Čo urobiť s týmto súborom?")
        self.setMinimumWidth(320)
        self.chosen = None
        layout = QVBoxLayout(self)
        label = QLabel(f"Čo urobiť s:\n{path.name}")
        label.setWordWrap(True)
        layout.addWidget(label)
        for label_text, func in actions:
            button = QPushButton(label_text)
            button.clicked.connect(
                lambda _=False, f=func: self._pick(f)
            )
            layout.addWidget(button)
        cancel = QPushButton("Zrušiť")
        cancel.clicked.connect(self.reject)
        layout.addWidget(cancel)

    def _pick(self, func) -> None:
        self.chosen = func
        self.accept()


class DropWindow(QWidget):
    """Small always-on-top window with a big drop area.

    Dropping a single file here automatically opens the action
    choice dialog for that file type. The window itself never
    converts anything — the main window runs the chosen action,
    so Output settings, logging and the Done message stay in one
    place. The window stays open after an action, ready for the
    next drop.
    """

    def __init__(self, main_window):
        super().__init__(
            None,
            Qt.WindowType.WindowStaysOnTopHint,
        )
        self._main = main_window
        self.setWindowTitle("CONVERTOR-APP — Pretiahni sem")
        self.setMinimumSize(320, 240)
        self.setAcceptDrops(True)
        layout = QVBoxLayout(self)
        label = QLabel("Pretiahni sem súbor\n\nAppka sa ťa opýta, čo s ním má urobiť.")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setWordWrap(True)
        label.setStyleSheet("font-size: 18px;")
        layout.addWidget(label)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        urls = event.mimeData().urls()
        if not urls:
            return
        path = Path(urls[0].toLocalFile())
        if not path.is_file():
            self._main.log("Okno na pretiahnutie: pretiahni jeden súbor, nie priečinok.")
            QMessageBox.warning(self, "Okno na pretiahnutie", "Pretiahni jeden súbor, nie priečinok.")
            return
        actions = actions_for_file(path)
        if not actions:
            self._main.log(f"Okno na pretiahnutie: žiadne akcie pre {path.name} ({path.suffix}).")
            QMessageBox.warning(
                self,
                "Žiadne akcie",
                f"Pre tento typ súboru nie je žiadna konverzia:\n{path.name}",
            )
            return
        dialog = ActionChoiceDialog(self, path, actions)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.chosen is None:
            self._main.log(f"Okno na pretiahnutie: zrušené pre {path.name}.")
            return
        self._main._run_file_action(dialog.chosen, file_path=path)


class SettingsDialog(QDialog):
    """Settings dialog, opened from the gear button in the top row.

    Sections: Output (mode, folder, ask-for-output-file), Text
    (default folder for pasted-text saves), Widget (show the
    floating widget at startup), Images (JPG / compress quality),
    Vzhľad (theme: default dark + teal, or another one, with
    "Obnoviť predvolený vzhľad" to get the default back),
    Log a história (read-only log + session history — moved
    here from the main window in v0.8) and Aktualizácie
    (manual update check + update button).
    ``settings`` holds the chosen
    values after Accept; Cancel leaves everything unchanged;
    "Reset to defaults" restores the default values in the
    dialog (they are only saved when Save is clicked).
    ``log_lines`` / ``history_entries`` are the current log
    and session history from the main window (shown read-only).
    """

    def __init__(self, parent, settings: dict,
                 log_lines=None, history_entries=None):
        super().__init__(parent)
        self.setWindowTitle("Nastavenia")
        self.setMinimumWidth(480)
        self.settings = dict(settings)
        self._log_lines = list(log_lines or [])
        self._history_entries = list(history_entries or [])
        layout = QVBoxLayout(self)

        # --- Output ------------------------------------------------
        output_box = QGroupBox("Output")
        output_layout = QVBoxLayout(output_box)
        self._next_radio = QRadioButton("Vedľa originálu (predvolené)")
        output_layout.addWidget(self._next_radio)
        folder_row = QHBoxLayout()
        self._folder_radio = QRadioButton("Priečinok:")
        self._folder_edit = QLineEdit()
        self._folder_edit.setReadOnly(True)
        self._folder_edit.setPlaceholderText("Zatiaľ nevybratý priečinok")
        folder_pick = QPushButton("Prehľadávať…")
        folder_pick.clicked.connect(self._pick_folder)
        self._folder_button = folder_pick
        folder_row.addWidget(self._folder_radio)
        folder_row.addWidget(self._folder_edit, stretch=1)
        folder_row.addWidget(folder_pick)
        output_layout.addLayout(folder_row)
        self._ask_checkbox = QCheckBox(
            "Opýtať sa na výstupný súbor pred každou konverziou"
        )
        output_layout.addWidget(self._ask_checkbox)
        self._folder_radio.toggled.connect(self._on_folder_toggled)
        layout.addWidget(output_box)

        # --- Text --------------------------------------------------
        text_box = QGroupBox("Text")
        text_layout = QHBoxLayout(text_box)
        text_layout.addWidget(QLabel("Predvolený priečinok pre vložený text:"))
        self._text_edit = QLineEdit()
        self._text_edit.setReadOnly(True)
        text_pick = QPushButton("Browse…")
        text_pick.clicked.connect(self._pick_text_folder)
        text_layout.addWidget(self._text_edit, stretch=1)
        text_layout.addWidget(text_pick)
        layout.addWidget(text_box)

        # --- Widget ------------------------------------------------
        widget_box = QGroupBox("Widget")
        widget_layout = QVBoxLayout(widget_box)
        self._widget_checkbox = QCheckBox(
            "Zobraziť plávajúci widget pri spustení"
        )
        widget_layout.addWidget(self._widget_checkbox)
        layout.addWidget(widget_box)

        # --- Images (v0.5) -----------------------------------------
        images_box = QGroupBox("Obrázky")
        images_layout = QVBoxLayout(images_box)
        jpg_row = QHBoxLayout()
        jpg_row.addWidget(QLabel("JPG kvalita (10–100):"))
        self._jpg_spin = QSpinBox()
        self._jpg_spin.setRange(10, 100)
        jpg_row.addWidget(self._jpg_spin)
        jpg_row.addStretch(1)
        images_layout.addLayout(jpg_row)
        comp_row = QHBoxLayout()
        comp_row.addWidget(QLabel("Kvalita kompresie JPG (10–100):"))
        self._compress_spin = QSpinBox()
        self._compress_spin.setRange(10, 100)
        comp_row.addWidget(self._compress_spin)
        comp_row.addStretch(1)
        images_layout.addLayout(comp_row)
        layout.addWidget(images_box)

        # --- Vzhľad (v0.8) ------------------------------------------
        # Predvolený vzhľad je tmavý + tyrkysový z v0.6; kto chce,
        # vyberie iný — a tlačidlo ho kedykoľvek vráti na predvolený.
        looks_box = QGroupBox("Vzhľad")
        looks_layout = QVBoxLayout(looks_box)
        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel("Téma:"))
        self._theme_combo = QComboBox()
        for name in theme_names():
            self._theme_combo.addItem(theme_label(name), name)
        theme_row.addWidget(self._theme_combo, stretch=1)
        theme_reset = QPushButton("Obnoviť predvolený vzhľad")
        theme_reset.clicked.connect(self._reset_theme)
        theme_row.addWidget(theme_reset)
        looks_layout.addLayout(theme_row)
        layout.addWidget(looks_box)

        # --- Log a história (v0.8) -----------------------------------
        # V hlavnom okne už nie sú — prvý reálny používateľ ich
        # označil za zbytočné na hlavnej obrazovke. Kto ich chce,
        # nájde ich tu, len na čítanie.
        log_box = QGroupBox("Log a história")
        log_layout = QVBoxLayout(log_box)
        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setPlainText("\n".join(self._log_lines))
        self._log_view.setMaximumHeight(160)
        log_layout.addWidget(self._log_view)
        self._history_view = QListWidget()
        for entry in self._history_entries:
            self._history_view.addItem(entry)
        self._history_view.setMaximumHeight(110)
        log_layout.addWidget(self._history_view)
        open_folder = QPushButton("Otvoriť priečinok")
        open_folder.clicked.connect(self._open_output_folder)
        log_layout.addWidget(open_folder)
        layout.addWidget(log_box)

        # --- Updates (v0.5) ----------------------------------------
        update_box = QGroupBox("Aktualizácie")
        update_layout = QVBoxLayout(update_box)
        self._update_status = QLabel("Zatiaľ neskontrolované.")
        self._update_status.setWordWrap(True)
        update_layout.addWidget(self._update_status)
        update_row = QHBoxLayout()
        check_button = QPushButton("Skontrolovať aktualizácie")
        check_button.clicked.connect(self._check_updates)
        self._update_button = QPushButton("Aktualizovať")
        self._update_button.setEnabled(False)
        self._update_button.clicked.connect(self._run_update)
        update_row.addWidget(check_button)
        update_row.addWidget(self._update_button)
        update_row.addStretch(1)
        update_layout.addLayout(update_row)
        layout.addWidget(update_box)

        # --- Buttons -----------------------------------------------
        button_row = QHBoxLayout()
        reset = QPushButton("Obnoviť predvolené")
        reset.clicked.connect(self._reset_to_defaults)
        save = QPushButton("Uložiť")
        save.clicked.connect(self.accept)
        cancel = QPushButton("Zrušiť")
        cancel.clicked.connect(self.reject)
        button_row.addWidget(reset)
        button_row.addStretch(1)
        button_row.addWidget(save)
        button_row.addWidget(cancel)
        layout.addLayout(button_row)

        self._load_into_controls(settings)

    def _load_into_controls(self, settings: dict) -> None:
        folder_mode = settings.get("output_mode") == "folder"
        self._folder_radio.setChecked(folder_mode)
        self._next_radio.setChecked(not folder_mode)
        self._folder_edit.setText(str(settings.get("output_folder") or ""))
        self._ask_checkbox.setChecked(bool(settings.get("ask_output_file")))
        self._text_edit.setText(str(settings.get("text_folder") or ""))
        self._widget_checkbox.setChecked(
            bool(settings.get("show_widget_on_start"))
        )
        try:
            self._jpg_spin.setValue(int(settings.get("jpg_quality", 92)))
        except (TypeError, ValueError):
            self._jpg_spin.setValue(92)
        try:
            self._compress_spin.setValue(int(settings.get("compress_quality", 70)))
        except (TypeError, ValueError):
            self._compress_spin.setValue(70)
        theme = str(settings.get("theme") or DEFAULT_THEME)
        index = self._theme_combo.findData(theme)
        self._theme_combo.setCurrentIndex(index if index >= 0 else 0)
        self._on_folder_toggled()

    def _reset_theme(self) -> None:
        """Back to the default look (v0.8): dark + teal."""
        index = self._theme_combo.findData(DEFAULT_THEME)
        self._theme_combo.setCurrentIndex(index if index >= 0 else 0)

    def _open_output_folder(self) -> None:
        """Open the folder of the last conversion (via main window)."""
        parent = self.parent()
        if parent is not None and hasattr(parent, "_open_output_folder"):
            parent._open_output_folder()

    def _check_updates(self) -> None:
        """Manual update check: status text + enable Update if available.

        Version numbers only, never commit SHAs (v0.5.1): the SHAs
        in the check result are for the internal comparison only.
        """
        result = check_update()
        shown_local = result.get("local_version") or local_version() or "?"
        if result["status"] == "up_to_date":
            self._update_status.setText(
                f"Aktuálna verzia: {shown_local} — Máš najnovšiu verziu."
            )
        elif result["status"] == "available":
            shown_remote = result.get("remote_version")
            if shown_remote:
                self._update_status.setText(
                    f"Je k dispozícii nová verzia: {shown_remote}."
                )
            else:
                self._update_status.setText("Je k dispozícii novšia verzia.")
        else:
            self._update_status.setText(result.get("message", "Kontrola sa nepodarila."))
        self._update_button.setEnabled(result["status"] == "available")

    def _run_update(self) -> None:
        """Pull from origin/main, then auto-restart on success (v0.5.2).

        Success: show "Aktualizácia stiahnutá, reštartujem…",
        spawn the new process and quit the old one via the main
        window's schedule_restart_after_update() — the ~500 ms
        delay keeps the status visible. Failure: no restart, no
        quit, the app keeps running on the old version. If the
        main.py path cannot be resolved, fall back to the old
        manual-restart message instead of quitting.
        """
        result = run_update()
        if not result.get("success"):
            QMessageBox.warning(
                self, "Aktualizácia zlyhala",
                result.get("message", "Aktualizácia zlyhala."),
            )
            return
        self._update_status.setText("Aktualizácia stiahnutá, reštartujem…")
        self._update_button.setEnabled(False)
        parent = self.parent()
        if parent is not None and hasattr(
            parent, "schedule_restart_after_update"
        ):
            if parent.schedule_restart_after_update():
                return
        # Fallback: main.py could not be resolved, so do NOT quit.
        self._update_status.setText(
            "Aktualizované. Reštartuj appku, aby sa nová verzia načítala."
        )
        QMessageBox.information(
            self, "Aktualizované",
            "Aktualizované. Reštartuj appku, aby sa nová verzia načítala.",
        )

    def _on_folder_toggled(self) -> None:
        enabled = self._folder_radio.isChecked()
        self._folder_edit.setEnabled(enabled)
        self._folder_button.setEnabled(enabled)

    def _pick_folder(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, "Vybrať priečinok pre výstup")
        if chosen:
            self._folder_edit.setText(chosen)
            self._folder_radio.setChecked(True)

    def _pick_text_folder(self) -> None:
        chosen = QFileDialog.getExistingDirectory(
            self, "Vybrať predvolený priečinok pre vložený text"
        )
        if chosen:
            self._text_edit.setText(chosen)

    def _reset_to_defaults(self) -> None:
        self._load_into_controls(default_settings())

    def accept(self) -> None:
        self.settings = {
            "output_mode": (
                "folder" if self._folder_radio.isChecked()
                else "next_to_original"
            ),
            "output_folder": self._folder_edit.text().strip(),
            "ask_output_file": self._ask_checkbox.isChecked(),
            "text_folder": self._text_edit.text().strip(),
            "show_widget_on_start": self._widget_checkbox.isChecked(),
            "jpg_quality": self._jpg_spin.value(),
            "compress_quality": self._compress_spin.value(),
            "theme": self._theme_combo.currentData() or DEFAULT_THEME,
        }
        super().accept()


class BatchDialog(QDialog):
    """Batch conversion (v0.5): many files, one conversion per type.

    Files are grouped by suffix. Each group with fitting actions
    gets a combo box to pick one conversion; that conversion then
    runs for every file in the group. Groups with no fitting
    action are listed as unsupported and skipped. Output
    settings are respected, but the per-file "ask for output
    file" dialog is deliberately NOT shown per file in batch
    mode (it would prompt for every file); the chosen output
    folder / next-to-original rule applies instead.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self._main = parent
        self.setWindowTitle("Hromadná konverzia")
        self.setMinimumSize(520, 420)
        layout = QVBoxLayout(self)
        pick = QPushButton("Vybrať súbory…")
        pick.clicked.connect(self._pick_files)
        layout.addWidget(pick)
        self._groups_area = QVBoxLayout()
        layout.addLayout(self._groups_area)
        layout.addStretch(1)
        self._groups: list[tuple[list[Path], object]] = []
        self._combos: list[QComboBox] = []
        run = QPushButton("Spustiť hromadnú konverziu")
        run.clicked.connect(self._run_batch)
        self._run_button = run
        run.setEnabled(False)
        cancel = QPushButton("Zavrieť")
        cancel.clicked.connect(self.reject)
        layout.addWidget(run)
        layout.addWidget(cancel)

    def _pick_files(self) -> None:
        chosen, _ = QFileDialog.getOpenFileNames(self, "Vybrať súbory")
        if not chosen:
            return
        # Clear previous group widgets.
        while self._groups_area.count():
            item = self._groups_area.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self._groups = []
        self._combos = []
        grouped: dict[str, list[Path]] = {}
        for item in chosen:
            path = Path(item)
            if path.is_file():
                grouped.setdefault(path.suffix.lower(), []).append(path)
        for suffix, files in sorted(grouped.items()):
            actions = actions_for_file(files[0]) if files else []
            box = QGroupBox(
                f"{suffix or '(bez prípony)'} — {len(files)} súbor(ov)"
            )
            box_layout = QVBoxLayout(box)
            names = QLabel(", ".join(p.name for p in files))
            names.setWordWrap(True)
            box_layout.addWidget(names)
            if actions:
                combo = QComboBox()
                for label_text, _func in actions:
                    combo.addItem(label_text)
                box_layout.addWidget(combo)
                self._combos.append(combo)
                self._groups.append((files, combo))
            else:
                box_layout.addWidget(QLabel("Nepodporovaný typ — preskočí sa."))
            self._groups_area.addWidget(box)
        self._run_button.setEnabled(bool(self._groups))

    def _run_batch(self) -> None:
        total_ok = 0
        total_fail = 0
        for files, combo in self._groups:
            actions = actions_for_file(files[0])
            if combo.currentIndex() < 0 or combo.currentIndex() >= len(actions):
                continue
            _label, func = actions[combo.currentIndex()]
            for path in files:
                try:
                    output = self._main._execute_file_action(func, path)
                except Exception as exc:
                    self._main.log(f"Hromadne zlyhalo {path.name}: {exc}")
                    total_fail += 1
                else:
                    self._main.log(f"Hromadne uložené: {output}")
                    self._main._record_history(path.name, output)
                    total_ok += 1
        QMessageBox.information(
            self, "Hromadná konverzia hotová",
            f"Hotovo: {total_ok} úspešných, {total_fail} zlyhaných.",
        )
        self.accept()


class MainWindow(QMainWindow):
    """Local control panel: file conversions + text + log."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CONVERTOR-APP v0.8.0")
        self.setMinimumSize(720, 700)
        self.setAcceptDrops(True)
        self._file: Path | None = None
        self._widget: FloatingWidget | None = None
        self._drop_window: DropWindow | None = None
        self._output_dir: Path | None = None
        # Log and history are plain lists now (v0.8): the tab is
        # gone from the main window, and Settings shows them
        # read-only from these lists.
        self._log_lines: list[str] = []
        self._history_entries: list[str] = []
        self._last_output: Path | None = None
        # Loaded before any control is built, so the Output section
        # below can be initialised from the saved settings.
        self._settings: dict = load_settings()

        root = QWidget(self)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(10)

        # --- Hlavička: názov + podtitul vľavo, verzia, upozornenie, ozubené koleso vpravo
        top_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("CONVERTOR-APP")
        title.setObjectName("appTitle")
        subtitle = QLabel("Lokálny konvertor — bez cloudu, bez účtu")
        subtitle.setObjectName("subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        version_badge = QLabel("v0.8.0")
        version_badge.setObjectName("versionBadge")
        self._update_notice = QPushButton("Aktualizácia k dispozícii")
        self._update_notice.setVisible(False)
        self._update_notice.clicked.connect(self._run_update_from_notice)
        gear = QPushButton("⚙ Nastavenia")
        gear.setObjectName("gearButton")
        gear.clicked.connect(self._open_settings)
        top_row.addLayout(title_box)
        top_row.addWidget(version_badge)
        top_row.addStretch(1)
        top_row.addWidget(self._update_notice)
        top_row.addWidget(gear)
        layout.addLayout(top_row)

        tabs = QTabWidget()
        tabs.setObjectName("mainTabs")
        layout.addWidget(tabs)

        # --- Karta 1: Konvertor ----------------------------------------
        convertor_tab = QWidget()
        tab_layout = QVBoxLayout(convertor_tab)
        tab_layout.setContentsMargins(4, 8, 4, 4)
        tab_layout.setSpacing(10)

        # --- Krok 1: Vyber súbor ---------------------------------------
        # Jedna veľká zóna na pretiahnutie (klik = vybrať súbor) +
        # info o vybratom súbore. Nič iné tu nie je — bežný človek
        # má vidieť len to, čo práve potrebuje.
        step1_box = QGroupBox("1. Vyber súbor")
        step1_layout = QVBoxLayout(step1_box)
        self._drop_zone = _DropZone(self)
        step1_layout.addWidget(self._drop_zone)
        self._file_info_label = QLabel("Zatiaľ žiadny súbor.")
        self._file_info_label.setObjectName("fileInfo")
        self._file_info_label.setWordWrap(True)
        step1_layout.addWidget(self._file_info_label)
        pick = QPushButton("Vybrať súbor…")
        pick.setObjectName("primaryButton")
        pick.clicked.connect(self._pick_file)
        step1_layout.addWidget(pick)
        tab_layout.addWidget(step1_box)
        # Odznaky podporovaných formátov — len popisy, nie tlačidlá
        chips_row = QHBoxLayout()
        chips_row.setSpacing(4)
        for fmt in ("PDF", "DOCX", "XLSX", "PPTX", "ODT", "ODS",
                    "TXT", "CSV", "HTML", "PNG", "JPG", "WEBP"):
            chip = QLabel(fmt)
            chip.setObjectName("formatChip")
            chips_row.addWidget(chip)
        chips_row.addStretch(1)
        tab_layout.addLayout(chips_row)

        # (Výstup tu už nie je: v0.6.1 je na hlavnej obrazovke len
        # jeden riadok o tom, kam sa nový súbor uloží — nastavenie
        # samotné žije v Nastaveniach. Pozri krok 3 nižšie.)

        # --- Krok 2: Vyber, čo z neho spraviť --------------------------
        # Bez statického zoznamu všetkých tlačidiel: sekciu prestavuje
        # _rebuild_conversions() pri zmene vybratého súboru — len
        # nápoveda bez súboru, len vhodné možnosti pre rozpoznaný
        # súbor (prepínač, nie tlačidlo na každú akciu), hláška
        # "zatiaľ nepodporujem" pre neznámy typ. Smerovanie je
        # actions_for_file(), to isté ako v Okne na pretiahnutie.
        step2_box = QGroupBox("2. Vyber, čo z neho spraviť")
        self._conv_layout = QVBoxLayout(step2_box)
        self._recognition_label = QLabel("Najprv vyber súbor v kroku 1.")
        self._recognition_label.setWordWrap(True)
        self._conv_layout.addWidget(self._recognition_label)
        self._conv_radios: list[QRadioButton] = []
        self._conv_actions: list = []
        tab_layout.addWidget(step2_box)

        # --- Krok 3: jedno veľké tlačidlo ------------------------------
        self._convert_button = QPushButton("Konvertovať")
        self._convert_button.setObjectName("convertButton")
        self._convert_button.setMinimumHeight(52)
        self._convert_button.setEnabled(False)
        self._convert_button.clicked.connect(self._on_convert_clicked)
        tab_layout.addWidget(self._convert_button)
        # Výsledok — jeden jasný riadok, nie vyskakovacie okno
        self._result_label = QLabel("")
        self._result_label.setWordWrap(True)
        self._result_label.setVisible(False)
        tab_layout.addWidget(self._result_label)
        result_row = QHBoxLayout()
        self._open_folder_button = QPushButton("Otvoriť priečinok s výsledkom")
        self._open_folder_button.clicked.connect(self._open_output_folder)
        self._open_folder_button.setVisible(False)
        self._next_file_button = QPushButton("Konvertovať ďalší súbor")
        self._next_file_button.clicked.connect(self._reset_flow)
        self._next_file_button.setVisible(False)
        result_row.addWidget(self._open_folder_button)
        result_row.addWidget(self._next_file_button)
        result_row.addStretch(1)
        tab_layout.addLayout(result_row)
        # Kam sa nový súbor uloží — jeden riadok ľudskou rečou.
        # Nastavenie samotné žije v Nastaveniach (ozubené koleso).
        save_row = QHBoxLayout()
        self._save_info_label = QLabel("")
        self._save_info_label.setObjectName("fileInfo")
        self._save_info_label.setWordWrap(True)
        save_row.addWidget(self._save_info_label, stretch=1)
        change_save = QPushButton("Zmeniť…")
        change_save.clicked.connect(self._open_settings)
        save_row.addWidget(change_save)
        tab_layout.addLayout(save_row)
        tab_layout.addStretch(1)
        tabs.addTab(convertor_tab, "Konvertor")

        # --- Karta 2: Ďalšie -------------------------------------------
        # Pokročilé veci mimo hlavnej obrazovky: text bez súboru,
        # okno na pretiahnutie, hromadná konverzia, widget.
        more_tab = QWidget()
        more_layout = QVBoxLayout(more_tab)
        more_layout.setContentsMargins(4, 8, 4, 4)
        more_layout.setSpacing(10)
        text_box = QGroupBox("Text bez súboru")
        text_layout = QHBoxLayout(text_box)
        text_layout.addWidget(QLabel("Napíš alebo vlož text a ulož ho ako súbor."))
        paste = QPushButton("Vložiť text…")
        paste.clicked.connect(self._paste_text)
        text_layout.addWidget(paste)
        more_layout.addWidget(text_box)
        tools_box = QGroupBox("Ďalšie nástroje")
        tools_layout = QVBoxLayout(tools_box)
        drop_button = QPushButton("Okno na pretiahnutie…")
        drop_button.clicked.connect(self._open_drop_window)
        batch_button = QPushButton("Hromadná konverzia…")
        batch_button.clicked.connect(self._open_batch)
        widget_button = QPushButton("Plávajúci widget: zobraziť / skryť")
        widget_button.clicked.connect(self._toggle_widget)
        tools_layout.addWidget(drop_button)
        tools_layout.addWidget(batch_button)
        tools_layout.addWidget(widget_button)
        more_layout.addWidget(tools_box)
        more_layout.addStretch(1)
        tabs.addTab(more_tab, "Ďalšie")

        # (v0.8: karta "Log a história" je preč z hlavného okna —
        # log a história žijú v Nastaveniach, len na čítanie.)

        self.setCentralWidget(root)
        self._apply_settings_to_controls()
        self.log("CONVERTOR-APP v0.8.0 pripravená. Pretiahni súbor a klikni na Konvertovať.")
        if self._settings.get("show_widget_on_start"):
            self._toggle_widget()
        # Automatic update check (v0.5): after the window shows,
        # so startup is not blocked. Silent unless an update is
        # actually available — then the top-row notice appears.
        QTimer.singleShot(1000, self._auto_update_check)

    # -- log ------------------------------------------------------------
    def log(self, message: str) -> None:
        """Append a timestamped line to the in-memory log (v0.8).

        The log is a plain list now — the Settings dialog shows
        it read-only when opened. Capped so a long session
        cannot grow it without bound.
        """
        self._log_lines.append(f"[{_stamp()}] {message}")
        while len(self._log_lines) > 500:
            self._log_lines.pop(0)

    def _record_history(self, source_name: str, output: Path) -> None:
        """Add a file → output entry to the session history list."""
        self._last_output = Path(output)
        self._history_entries.append(f"{source_name} → {output.name}")
        while len(self._history_entries) > 50:
            self._history_entries.pop(0)

    def _open_output_folder(self) -> None:
        """Open the folder of the last successful conversion."""
        if self._last_output is None:
            QMessageBox.information(
                self, "Otvoriť priečinok", "Zatiaľ žiadna konverzia v tejto relácii."
            )
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._last_output.parent)))

    def _open_batch(self) -> None:
        """Open the batch conversion dialog (v0.5)."""
        dialog = BatchDialog(self)
        dialog.exec()

    def _auto_update_check(self) -> None:
        """Silent startup update check: notice only if available."""
        try:
            result = check_update()
        except Exception:
            return
        if result.get("status") == "available":
            shown_remote = result.get("remote_version")
            if shown_remote:
                self.log(
                    f"Aktualizácia k dispozícii: nová verzia {shown_remote}. "
                    "Pozri Nastavenia → Aktualizácie."
                )
            else:
                self.log(
                    "Aktualizácia k dispozícii: novšia verzia. "
                    "Pozri Nastavenia → Aktualizácie."
                )
            self._update_notice.setVisible(True)

    def schedule_restart_after_update(self) -> bool:
        """Spawn the new app process and quit this one after ~500 ms.

        Returns True only if a new process was actually spawned.
        Returns False — and quits nothing — when main.py cannot
        be resolved or the spawn fails. The caller must only call
        this after a successful pull. The delay keeps the
        "reštartujem…" status visible before the old window closes.
        """
        if not spawn_restart():
            self.log(
                "Reštart sa nepodaril — reštartuj appku ručne, "
                "aby sa nová verzia načítala."
            )
            return False
        self.log("Aktualizácia stiahnutá, reštartujem…")
        app = QApplication.instance()
        if app is not None:
            QTimer.singleShot(500, app.quit)
        return True

    def _run_update_from_notice(self) -> None:
        """Update from the top-row notice, then auto-restart (v0.5.2)."""
        result = run_update()
        if not result.get("success"):
            QMessageBox.warning(
                self, "Aktualizácia zlyhala",
                result.get("message", "Aktualizácia zlyhala."),
            )
            return
        self._update_notice.setVisible(False)
        if self.schedule_restart_after_update():
            return
        # Fallback: spawn failed, so do NOT quit.
        QMessageBox.information(
            self, "Aktualizované",
            "Aktualizované. Reštartuj appku, aby sa nová verzia načítala.",
        )

    # -- file picking / dropping -----------------------------------------
    # NOTE (v0.4): dropping onto the MAIN window still does NOT
    # convert anything by itself — it sets the picked file, and
    # _rebuild_conversions() then suggests only the conversions
    # that fit it. The auto-ask dialog behaviour lives only in
    # the Drop window.
    def _pick_file(self) -> None:
        chosen, _ = QFileDialog.getOpenFileName(self, "Vybrať súbor")
        if chosen:
            self._set_file(Path(chosen))

    def _set_file(self, path: Path) -> None:
        self._file = path
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        label = _file_type_label(path)
        self._file_info_label.setText(
            f"{path.name} — {label or 'neznámy typ'} — {_format_size(size)}"
        )
        self.log(f"Vybrané: {path.name}")
        self._hide_result()
        self._rebuild_conversions()

    def _rebuild_conversions(self) -> None:
        """Rebuild step 2 for the currently picked file (v0.4/0.6.1).

        No file: hint only, no options. Recognised file: a
        recognition label plus ONLY the actions that
        actions_for_file() returns for it, each as one radio
        option in plain words (the first one is pre-selected, so
        the user can just press Konvertovať). Unknown type: a
        clear "not supported yet" message, no options, and a log
        line — never an empty list and never the full list.
        """
        for radio in self._conv_radios:
            self._conv_layout.removeWidget(radio)
            radio.deleteLater()
        self._conv_radios = []
        self._conv_actions = []
        self._convert_button.setEnabled(False)
        if self._file is None:
            self._recognition_label.setText("Najprv vyber súbor v kroku 1.")
            return
        actions = actions_for_file(self._file)
        if not actions:
            suffix = self._file.suffix.lower() or "(bez prípony)"
            self._recognition_label.setText(
                f"Tento typ súboru zatiaľ nepodporujem ({suffix}) — "
                "skús iný súbor."
            )
            self.log(
                f"Pre {self._file.name} nie sú žiadne konverzie "
                f"({suffix}) — typ zatiaľ nie je podporovaný."
            )
            return
        label = _file_type_label(self._file)
        self._recognition_label.setText(
            f"Rozpoznal som: {label} — vyber, čo z neho spraviť:"
            if label
            else f"Rozpoznal som: {self._file.name} — vyber, čo z neho spraviť:"
        )
        for label_text, func in actions:
            radio = QRadioButton(ACTION_DESCRIPTIONS.get(func, label_text))
            self._conv_layout.addWidget(radio)
            self._conv_radios.append(radio)
            self._conv_actions.append(func)
        if self._conv_radios:
            self._conv_radios[0].setChecked(True)
            self._convert_button.setEnabled(True)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        urls = event.mimeData().urls()
        if urls:
            path = Path(urls[0].toLocalFile())
            if path.is_file():
                self._set_file(path)
            else:
                self.log("Pretiahni jeden súbor, nie priečinok.")

    # -- settings / output settings -------------------------------------
    def _text_dir(self) -> Path:
        """Text-folder setting, or the Desktop default as fallback."""
        stored = str(self._settings.get("text_folder") or "")
        if stored and Path(stored).is_dir():
            return Path(stored)
        return default_text_dir()

    def _apply_settings_to_controls(self) -> None:
        """Push the loaded/saved settings into the app state.

        In v0.6 the Output controls lived on the main tab; in
        v0.6.1 the main tab only shows one plain line saying where
        the new file will be saved, and the Output settings
        themselves live in the Settings dialog (which already
        wrote the file). The floating widget, if already open,
        gets the new text folder too, so its paste dialog matches.
        """
        folder_mode = self._settings.get("output_mode") == "folder"
        folder = str(self._settings.get("output_folder") or "")
        self._output_dir = Path(folder) if folder_mode and folder else None
        if folder_mode and folder:
            self._save_info_label.setText(f"Uloží sa do priečinka: {folder}")
        else:
            self._save_info_label.setText(
                "Nový súbor sa uloží vedľa pôvodného súboru."
            )
        self._apply_theme()
        if self._widget is not None:
            self._widget.set_text_dir(self._text_dir())

    def _theme_name(self) -> str:
        """Saved theme key, default if missing or unknown."""
        theme = str(self._settings.get("theme") or DEFAULT_THEME)
        return theme if theme in theme_names() else DEFAULT_THEME

    def _apply_theme(self) -> None:
        """Apply the saved theme to the whole app (v0.8)."""
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(stylesheet_for(self._theme_name()))

    def _open_settings(self) -> None:
        """Open the Settings dialog from the gear button."""
        dialog = SettingsDialog(
            self, self._settings,
            log_lines=self._log_lines,
            history_entries=self._history_entries,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._settings = dialog.settings
        save_settings(self._settings)
        self._apply_settings_to_controls()
        self.log(
            "Nastavenia uložené "
            f"(výstup: {self._settings['output_mode']}, "
            f"priečinok pre text: {self._text_dir()}, "
            "widget pri spustení: "
            f"{'zapnutý' if self._settings.get('show_widget_on_start') else 'vypnutý'}, "
            f"téma: {theme_label(self._theme_name())})."
        )

    def _output_dir_value(self):
        """Chosen output folder, or None for 'next to original'."""
        return self._output_dir

    # -- drop window -------------------------------------------------------
    def _open_drop_window(self) -> None:
        if self._drop_window is None:
            self._drop_window = DropWindow(self)
        self._drop_window.show()
        self._drop_window.raise_()
        self.log("Okno na pretiahnutie otvorené (pretiahni tam súbor — appka sa opýta, čo s ním).")

    # -- actions -----------------------------------------------------------
    def _action_kwargs(self, func) -> dict:
        """Quality settings for image actions (v0.5); {} otherwise."""
        if func is convert_to_jpg:
            try:
                return {"jpg_quality": int(self._settings.get("jpg_quality", 92))}
            except (TypeError, ValueError):
                return {"jpg_quality": 92}
        if func is compress_image:
            try:
                return {"compress_quality": int(self._settings.get("compress_quality", 70))}
            except (TypeError, ValueError):
                return {"compress_quality": 70}
        return {}

    def _execute_file_action(self, func, target_file: Path) -> Path:
        """Run one file action, no dialogs, no message boxes.

        Used by the batch flow (and by the single-file flow when
        "ask for output file" is off). Respects the Output
        folder setting and the image quality settings; the
        per-file Save dialog is deliberately not shown here.
        """
        output_dir = self._output_dir_value()
        return func(target_file, output_dir=output_dir, **self._action_kwargs(func))

    def _execute_with_output(self, func, target_file) -> Path | None:
        """Run one action, honouring the 'ask for output file' setting.

        Returns the output path, or None if the user cancelled the
        Save dialog. Raises on failure — the caller shows a
        friendly message, the technical detail stays in the log.
        """
        if self._settings.get("ask_output_file"):
            proposed = default_output_for(
                target_file, func, output_dir=self._output_dir_value()
            )
            ext = proposed.suffix.lstrip(".").upper()
            chosen, _ = QFileDialog.getSaveFileName(
                self,
                "Uložiť výstup ako",
                str(proposed),
                f"{ext} (*{proposed.suffix});;All files (*.*)",
            )
            if not chosen:
                self.log("Ukladanie výstupu zrušené.")
                return None
            return func(
                target_file, output_path=Path(chosen),
                **self._action_kwargs(func),
            )
        return self._execute_file_action(func, target_file)

    def _run_file_action(self, func, file_path=None) -> None:
        """Run a file action, respecting the Output settings.

        Used by the Drop window. ``file_path`` is set by the Drop
        window; otherwise the picked file is used. Failures are
        explained in plain words; the technical detail stays in
        the log. Pasted-text saving is untouched by this (it keeps
        its own save dialog in _paste_text).
        """
        target_file = file_path if file_path is not None else self._file
        if target_file is None:
            self.log("Žiadny súbor vybratý — najprv vyber súbor.")
            QMessageBox.warning(self, "Žiadny súbor", "Najprv vyber súbor.")
            return
        try:
            output = self._execute_with_output(func, target_file)
        except Exception as exc:
            self.log(f"ZLYHALO {target_file.name}: {exc}")
            QMessageBox.warning(self, "Nepodarilo sa", _friendly_error(exc))
            return
        if output is None:
            return
        self.log(f"Uložené: {output}")
        self._record_history(target_file.name, output)
        QMessageBox.information(
            self, "Hotovo", f"Nový súbor je uložený:\n{output.name}"
        )

    def _selected_action(self):
        """The action chosen by the step-2 radio button, or None."""
        for radio, func in zip(self._conv_radios, self._conv_actions):
            if radio.isChecked():
                return func
        return None

    def _on_convert_clicked(self) -> None:
        """Step 3: run the chosen conversion, show the result inline.

        Success and failure both land in the result line under
        the button — no pop-up the user has to close first.
        """
        func = self._selected_action()
        if self._file is None or func is None:
            return
        self._convert_button.setEnabled(False)
        try:
            output = self._execute_with_output(func, self._file)
        except Exception as exc:
            self.log(f"ZLYHALO {self._file.name}: {exc}")
            self._show_result(False, _friendly_error(exc))
        else:
            if output is not None:
                self.log(f"Uložené: {output}")
                self._record_history(self._file.name, output)
                self._show_result(True, f"Hotovo! Nový súbor: {output.name}")
        finally:
            self._convert_button.setEnabled(True)

    def _show_result(self, ok: bool, text: str) -> None:
        """Show the inline result line (themed ok/fail colors)."""
        self._result_label.setText(("✓ " if ok else "✗ ") + text)
        self._result_label.setStyleSheet(result_style(ok, self._theme_name()))
        self._result_label.setVisible(True)
        self._open_folder_button.setVisible(ok)
        self._next_file_button.setVisible(True)

    def _hide_result(self) -> None:
        """Hide the result line and its buttons (new file picked)."""
        self._result_label.setVisible(False)
        self._open_folder_button.setVisible(False)
        self._next_file_button.setVisible(False)

    def _reset_flow(self) -> None:
        """Start over: clear the picked file and the result line."""
        self._file = None
        self._file_info_label.setText("Zatiaľ žiadny súbor.")
        self._hide_result()
        self._rebuild_conversions()

    def _paste_text(self) -> None:
        dialog = TextDialog(self)
        if dialog.exec() != TextDialog.DialogCode.Accepted:
            return
        text = dialog.text()
        if not text.strip():
            self.log("Vložený text bol prázdny — nič sa neuložilo.")
            return
        # Ask what to do with the text: save dialog per kind, via a
        # small choice — Save .md is the default action here; the
        # floating ring offers the full set (md/txt/pdf/copy).
        # The dialog defaults to the text_folder setting (or the
        # Desktop default if that folder is missing).
        default = str(self._text_dir() / default_text_filename("md"))
        chosen, _ = QFileDialog.getSaveFileName(
            self, "Uložiť vložený text", default,
            "Markdown (*.md);;Text (*.txt);;PDF (*.pdf)",
        )
        if not chosen:
            self.log("Ukladanie textu zrušené.")
            return
        suffix = Path(chosen).suffix.lower()
        try:
            if suffix == ".pdf":
                output = text_to_pdf_path(text, chosen)
            elif suffix == ".txt":
                output = save_text_to_path(text, chosen, "txt")
            else:
                output = save_text_to_path(text, chosen, "md")
        except Exception as exc:
            self.log(f"ZLYHALO ukladanie textu: {exc}")
            QMessageBox.warning(self, "Nepodarilo sa", _friendly_error(exc))
        else:
            self.log(f"Uložený vložený text: {output}")

    def _toggle_widget(self) -> None:
        if self._widget is None:
            self._widget = FloatingWidget(text_dir=self._text_dir())
        if self._widget.isVisible():
            self._widget.hide()
            self.log("Plávajúci widget skrytý.")
        else:
            self._widget.show()
            self.log("Plávajúci widget zobrazený (rýchla cesta: pretiahni naň súbor).")


def main() -> int:
    app = QApplication(sys.argv)
    # Saved theme (v0.8): the default dark + teal when nothing
    # is saved yet. The main window re-applies it from its own
    # settings after it loads them.
    app.setStyleSheet(stylesheet_for(str(load_settings().get("theme") or DEFAULT_THEME)))
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
