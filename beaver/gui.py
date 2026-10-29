"""Main local GUI window for CONVERTOR-APP (v0.5).

Written from scratch for this app, in PySide6. It is in the same
spirit as a local launcher window — sections, buttons, and a
timestamped log/console — but no code is copied from any other
launcher. The floating widget + ring menu stays as the quick path;
this window is the full local control panel for the same actions.

Sections:
  1. File — pick a file, or drag one onto the window (this still
     only SETS the picked file; it does not convert it)
  2. Output — where converted files go: next to the original
     (default) or a chosen folder, plus "ask for output file
     before each conversion" (a Save dialog prefilled with the
     proposed name, so it can be renamed / relocated)
  3. Conversions — SMART (v0.4): no static list of all buttons.
     With no file picked, only a hint is shown. Once a file is
     picked (or dropped onto the main window), the app recognises
     its type and shows ONLY the conversions that fit it, plus a
     recognition label. An unsupported type shows a clear
     "not supported yet" message and no buttons at all.
  4. Text — paste text, save it to the Desktop (default) as
     .md / .txt / .pdf, or copy it (unchanged from v0.2: pasted
     text keeps its own save dialog)
  5. Log — timestamped console of what was converted and where
     it was saved

Plus a "Drop window" button: a small always-on-top window with a
big drop area. Dropping a single file there AUTOMATICALLY asks
what to do with it, listing only the actions that fit that file
type; the chosen action respects the Output settings above, logs
in the main window, and shows a Done message.

Plus Settings, reached from the top row: the app title on the
left and a "⚙ Nastavenia" gear button on the right. The gear
opens a Settings dialog (Output / Text / Widget / Images /
Aktualizácie) whose values are saved to
~/.convertor-app/settings.json — outside the repo, so a git
pull never overwrites them — and applied immediately.

v0.5 adds: more file types (XLSX, PPTX, TXT, CSV, HTML,
image → PDF / WEBP), conversion cards with descriptions,
a file-info line, batch conversion, JPG/compress quality
settings, a session history list, an "Otvoriť priečinok"
button, and update checking — automatic (silent) at startup
plus manual in Settings → Aktualizácie.

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
from .update_check import check_update, run_update
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


class ActionChoiceDialog(QDialog):
    """Ask what to do with a dropped file (Drop window only).

    Lists ONLY the actions that fit the file type. ``chosen`` is the
    selected action function, or None if the dialog was cancelled.
    """

    def __init__(self, parent, path: Path, actions):
        super().__init__(parent)
        self.setWindowTitle("What to do with this file?")
        self.setMinimumWidth(320)
        self.chosen = None
        layout = QVBoxLayout(self)
        label = QLabel(f"What to do with:\n{path.name}")
        label.setWordWrap(True)
        layout.addWidget(label)
        for label_text, func in actions:
            button = QPushButton(label_text)
            button.clicked.connect(
                lambda _=False, f=func: self._pick(f)
            )
            layout.addWidget(button)
        cancel = QPushButton("Cancel")
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
        self.setWindowTitle("CONVERTOR-APP — Drop here")
        self.setMinimumSize(320, 240)
        self.setAcceptDrops(True)
        layout = QVBoxLayout(self)
        label = QLabel("Drop a file here\n\nIt will ask what to do with it.")
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
            self._main.log("Drop window: drop a single file, not a folder.")
            QMessageBox.warning(self, "Drop window", "Drop a single file, not a folder.")
            return
        actions = actions_for_file(path)
        if not actions:
            self._main.log(f"Drop window: no actions for {path.name} ({path.suffix}).")
            QMessageBox.warning(
                self,
                "No actions",
                f"No conversion fits this file type:\n{path.name}",
            )
            return
        dialog = ActionChoiceDialog(self, path, actions)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.chosen is None:
            self._main.log(f"Drop window: cancelled for {path.name}.")
            return
        self._main._run_file_action(dialog.chosen, file_path=path)


class SettingsDialog(QDialog):
    """Settings dialog, opened from the gear button in the top row.

    Sections: Output (mode, folder, ask-for-output-file), Text
    (default folder for pasted-text saves), Widget (show the
    floating widget at startup), Images (JPG / compress quality)
    and Aktualizácie (manual update check + update button).
    ``settings`` holds the chosen
    values after Accept; Cancel leaves everything unchanged;
    "Reset to defaults" restores the default values in the
    dialog (they are only saved when Save is clicked).
    """

    def __init__(self, parent, settings: dict):
        super().__init__(parent)
        self.setWindowTitle("Nastavenia")
        self.setMinimumWidth(480)
        self.settings = dict(settings)
        layout = QVBoxLayout(self)

        # --- Output ------------------------------------------------
        output_box = QGroupBox("Output")
        output_layout = QVBoxLayout(output_box)
        self._next_radio = QRadioButton("Next to original (default)")
        output_layout.addWidget(self._next_radio)
        folder_row = QHBoxLayout()
        self._folder_radio = QRadioButton("Folder:")
        self._folder_edit = QLineEdit()
        self._folder_edit.setReadOnly(True)
        self._folder_edit.setPlaceholderText("No folder picked yet")
        folder_pick = QPushButton("Browse…")
        folder_pick.clicked.connect(self._pick_folder)
        self._folder_button = folder_pick
        folder_row.addWidget(self._folder_radio)
        folder_row.addWidget(self._folder_edit, stretch=1)
        folder_row.addWidget(folder_pick)
        output_layout.addLayout(folder_row)
        self._ask_checkbox = QCheckBox(
            "Ask for output file before each conversion"
        )
        output_layout.addWidget(self._ask_checkbox)
        self._folder_radio.toggled.connect(self._on_folder_toggled)
        layout.addWidget(output_box)

        # --- Text --------------------------------------------------
        text_box = QGroupBox("Text")
        text_layout = QHBoxLayout(text_box)
        text_layout.addWidget(QLabel("Default folder for pasted text:"))
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
            "Show floating widget at startup"
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
        reset = QPushButton("Reset to defaults")
        reset.clicked.connect(self._reset_to_defaults)
        save = QPushButton("Save")
        save.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
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
        self._on_folder_toggled()

    def _check_updates(self) -> None:
        """Manual update check: status text + enable Update if available."""
        result = check_update()
        local = result.get("local", "")
        remote = result.get("remote", "")
        short_local = local[:7] if local else "?"
        short_remote = remote[:7] if remote else "?"
        if result["status"] == "up_to_date":
            self._update_status.setText(
                f"Aktuálna verzia: {short_local} — Máš najnovšiu verziu."
            )
        elif result["status"] == "available":
            self._update_status.setText(
                f"Aktuálna: {short_local}, na GitHube: {short_remote} — "
                "K dispozícii je aktualizácia."
            )
        else:
            self._update_status.setText(result.get("message", "Kontrola sa nepodarila."))
        self._update_button.setEnabled(result["status"] == "available")

    def _run_update(self) -> None:
        """Pull from origin/main, then tell the user to restart."""
        result = run_update()
        if result.get("success"):
            self._update_status.setText(
                "Aktualizované. Reštartuj appku, aby sa nová verzia načítala."
            )
            self._update_button.setEnabled(False)
            QMessageBox.information(
                self, "Aktualizované",
                "Aktualizované. Reštartuj appku, aby sa nová verzia načítala.",
            )
        else:
            QMessageBox.warning(
                self, "Aktualizácia zlyhala",
                result.get("message", "Aktualizácia zlyhala."),
            )

    def _on_folder_toggled(self) -> None:
        enabled = self._folder_radio.isChecked()
        self._folder_edit.setEnabled(enabled)
        self._folder_button.setEnabled(enabled)

    def _pick_folder(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, "Pick output folder")
        if chosen:
            self._folder_edit.setText(chosen)
            self._folder_radio.setChecked(True)

    def _pick_text_folder(self) -> None:
        chosen = QFileDialog.getExistingDirectory(
            self, "Pick default folder for pasted text"
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
                    self._main.log(f"BATCH FAILED {path.name}: {exc}")
                    total_fail += 1
                else:
                    self._main.log(f"BATCH Saved: {output}")
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
        self.setWindowTitle("CONVERTOR-APP v0.5")
        self.setMinimumSize(640, 700)
        self.setAcceptDrops(True)
        self._file: Path | None = None
        self._widget: FloatingWidget | None = None
        self._drop_window: DropWindow | None = None
        self._output_dir: Path | None = None
        # Loaded before any control is built, so the Output section
        # below can be initialised from the saved settings.
        self._settings: dict = load_settings()

        root = QWidget(self)
        layout = QVBoxLayout(root)

        # --- Top row: title left, gear button right ------------------
        # This is THE way into Settings: "⚙ Nastavenia" at the top
        # right of the main window, not a plain button in a section.
        top_row = QHBoxLayout()
        title = QLabel("CONVERTOR-APP")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        self._update_notice = QPushButton("Aktualizácia k dispozícii")
        self._update_notice.setVisible(False)
        self._update_notice.clicked.connect(self._run_update_from_notice)
        gear = QPushButton("⚙ Nastavenia")
        gear.clicked.connect(self._open_settings)
        top_row.addWidget(title)
        top_row.addStretch(1)
        top_row.addWidget(self._update_notice)
        top_row.addWidget(gear)
        layout.addLayout(top_row)

        # --- 1. File ---------------------------------------------------
        file_box = QGroupBox("1. File (pick one, or drag it onto this window)")
        file_vbox = QVBoxLayout(file_box)
        file_layout = QHBoxLayout()
        self._file_label = QLabel("No file picked yet.")
        self._file_label.setWordWrap(True)
        pick = QPushButton("Pick file…")
        pick.clicked.connect(self._pick_file)
        drop_button = QPushButton("Drop window…")
        drop_button.clicked.connect(self._open_drop_window)
        batch_button = QPushButton("Hromadná konverzia…")
        batch_button.clicked.connect(self._open_batch)
        file_layout.addWidget(self._file_label, stretch=1)
        file_layout.addWidget(pick)
        file_layout.addWidget(drop_button)
        file_layout.addWidget(batch_button)
        file_vbox.addLayout(file_layout)
        self._file_info_label = QLabel("Žiadny súbor vybratý.")
        self._file_info_label.setWordWrap(True)
        file_vbox.addWidget(self._file_info_label)
        layout.addWidget(file_box)

        # --- 2. Output -------------------------------------------------
        output_box = QGroupBox("2. Output (where converted files go)")
        output_layout = QVBoxLayout(output_box)
        self._next_radio = QRadioButton("Next to original (default)")
        self._next_radio.setChecked(True)
        output_layout.addWidget(self._next_radio)
        folder_row = QHBoxLayout()
        self._folder_radio = QRadioButton("Folder:")
        self._folder_edit = QLineEdit()
        self._folder_edit.setReadOnly(True)
        self._folder_edit.setPlaceholderText("No folder picked yet")
        self._folder_edit.setEnabled(False)
        folder_pick = QPushButton("Browse…")
        folder_pick.setEnabled(False)
        folder_pick.clicked.connect(self._pick_output_folder)
        self._folder_radio.toggled.connect(self._on_output_mode_changed)
        self._folder_edit_ref = self._folder_edit
        self._folder_button_ref = folder_pick
        folder_row.addWidget(self._folder_radio)
        folder_row.addWidget(self._folder_edit, stretch=1)
        folder_row.addWidget(folder_pick)
        output_layout.addLayout(folder_row)
        self._ask_checkbox = QCheckBox(
            "Ask for output file before each conversion"
        )
        self._ask_checkbox.toggled.connect(self._save_output_settings)
        output_layout.addWidget(self._ask_checkbox)
        layout.addWidget(output_box)
        self._apply_settings_to_controls()

        # --- 3. Conversions (SMART, v0.4) ------------------------------
        # No static list of all 18 buttons any more. The section is
        # rebuilt by _rebuild_conversions() whenever the picked
        # file changes: hint only with no file, only the fitting
        # actions for a recognised file, and a "not supported yet"
        # message (no buttons) for an unknown type. The routing is
        # actions_for_file(), the same one the Drop window uses —
        # there is no second routing table to drift out of sync.
        conv_box = QGroupBox("3. Conversions (only for the picked file)")
        self._conv_layout = QVBoxLayout(conv_box)
        self._recognition_label = QLabel(
            "Vyber súbor a ukážem len konverzie preň."
        )
        self._recognition_label.setWordWrap(True)
        self._conv_layout.addWidget(self._recognition_label)
        self._conv_buttons: list[QPushButton] = []
        layout.addWidget(conv_box)

        # --- 4. Text ----------------------------------------------------
        text_box = QGroupBox("4. Text (no file needed — saves default to Desktop)")
        text_layout = QHBoxLayout(text_box)
        paste = QPushButton("Paste text…")
        paste.clicked.connect(self._paste_text)
        widget_button = QPushButton("Floating widget: show / hide")
        widget_button.clicked.connect(self._toggle_widget)
        text_layout.addWidget(paste)
        text_layout.addWidget(widget_button)
        layout.addWidget(text_box)

        # --- 5. Log ------------------------------------------------------
        log_box = QGroupBox("5. Log (timestamped)")
        log_layout = QVBoxLayout(log_box)
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        log_layout.addWidget(self._log)
        layout.addWidget(log_box)

        # --- 6. History (session only, v0.5) ----------------------------
        history_box = QGroupBox("Posledné konverzie (táto relácia)")
        history_layout = QVBoxLayout(history_box)
        self._history_list = QListWidget()
        history_layout.addWidget(self._history_list)
        self._last_output: Path | None = None
        open_folder = QPushButton("Otvoriť priečinok")
        open_folder.clicked.connect(self._open_output_folder)
        history_layout.addWidget(open_folder)
        layout.addWidget(history_box)

        self.setCentralWidget(root)
        self.log("CONVERTOR-APP v0.5 ready. Pick a file, or paste text.")
        if self._settings.get("show_widget_on_start"):
            self._toggle_widget()
        # Automatic update check (v0.5): after the window shows,
        # so startup is not blocked. Silent unless an update is
        # actually available — then the top-row notice appears.
        QTimer.singleShot(1000, self._auto_update_check)

    # -- log ------------------------------------------------------------
    def log(self, message: str) -> None:
        self._log.appendPlainText(f"[{_stamp()}] {message}")

    def _record_history(self, source_name: str, output: Path) -> None:
        """Add a file → output entry to the session history list."""
        self._last_output = Path(output)
        self._history_list.addItem(f"{source_name} → {output.name}")
        while self._history_list.count() > 50:
            self._history_list.takeItem(0)

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
            self.log(
                "Aktualizácia k dispozícii "
                f"(aktuálna: {result.get('local', '')[:7]}, "
                f"na GitHube: {result.get('remote', '')[:7]}). "
                "Pozri Nastavenia → Aktualizácie."
            )
            self._update_notice.setVisible(True)

    def _run_update_from_notice(self) -> None:
        """Update from the top-row notice, then ask for a restart."""
        result = run_update()
        if result.get("success"):
            self.log("Aktualizované — reštartuj appku.")
            self._update_notice.setVisible(False)
            QMessageBox.information(
                self, "Aktualizované",
                "Aktualizované. Reštartuj appku, aby sa nová verzia načítala.",
            )
        else:
            QMessageBox.warning(
                self, "Aktualizácia zlyhala",
                result.get("message", "Aktualizácia zlyhala."),
            )

    # -- file picking / dropping -----------------------------------------
    # NOTE (v0.4): dropping onto the MAIN window still does NOT
    # convert anything by itself — it sets the picked file, and
    # _rebuild_conversions() then suggests only the conversions
    # that fit it. The auto-ask dialog behaviour lives only in
    # the Drop window.
    def _pick_file(self) -> None:
        chosen, _ = QFileDialog.getOpenFileName(self, "Pick a file")
        if chosen:
            self._set_file(Path(chosen))

    def _set_file(self, path: Path) -> None:
        self._file = path
        self._file_label.setText(str(path))
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        label = _file_type_label(path)
        self._file_info_label.setText(
            f"{path.name} — {label or 'neznámy typ'} — {_format_size(size)}"
        )
        self.log(f"Picked: {path.name}")
        self._rebuild_conversions()

    def _rebuild_conversions(self) -> None:
        """Rebuild section 3 for the currently picked file (v0.4/0.5).

        No file: hint only, no buttons. Recognised file: a
        recognition label plus ONLY the actions that
        actions_for_file() returns for it, each as a card: a
        button plus a one-line description. Unknown type: a clear
        "not supported yet" message, no buttons, and a log line —
        never an empty list and never the full list.
        """
        for widget in self._conv_buttons:
            self._conv_layout.removeWidget(widget)
            widget.deleteLater()
        self._conv_buttons = []
        if self._file is None:
            self._recognition_label.setText(
                "Vyber súbor a ukážem len konverzie preň."
            )
            return
        actions = actions_for_file(self._file)
        if not actions:
            suffix = self._file.suffix.lower() or "(bez prípony)"
            self._recognition_label.setText(
                f"Tento typ súboru zatiaľ nepodporujem ({suffix}) — "
                "žiadne konverzie preň nemám."
            )
            self.log(
                f"No conversions for {self._file.name} "
                f"({suffix}) — type not supported yet."
            )
            return
        label = _file_type_label(self._file)
        self._recognition_label.setText(
            f"Rozpoznal som: {label} — môžeš z neho spraviť:"
            if label
            else f"Rozpoznal som: {self._file.name} — môžeš z neho spraviť:"
        )
        for label_text, func in actions:
            card = QWidget()
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(0, 0, 0, 0)
            button = QPushButton(label_text)
            button.clicked.connect(
                lambda _=False, f=func: self._run_file_action(f)
            )
            description = QLabel(
                ACTION_DESCRIPTIONS.get(func, label_text)
            )
            description.setWordWrap(True)
            card_layout.addWidget(button)
            card_layout.addWidget(description, stretch=1)
            self._conv_layout.addWidget(card)
            self._conv_buttons.append(card)

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
                self.log("Drop a single file, not a folder.")

    # -- settings / output settings -------------------------------------
    def _text_dir(self) -> Path:
        """Text-folder setting, or the Desktop default as fallback."""
        stored = str(self._settings.get("text_folder") or "")
        if stored and Path(stored).is_dir():
            return Path(stored)
        return default_text_dir()

    def _apply_settings_to_controls(self) -> None:
        """Push the loaded/saved settings into the Output section.

        Does not save again: this is called after loading, and
        after the Settings dialog is saved (which already wrote
        the file). The floating widget, if already open, gets the
        new text folder too, so its paste dialog matches.
        """
        folder_mode = self._settings.get("output_mode") == "folder"
        folder = str(self._settings.get("output_folder") or "")
        self._output_dir = Path(folder) if folder_mode and folder else None
        self._folder_edit.setText(folder)
        self._folder_radio.setChecked(folder_mode)
        self._next_radio.setChecked(not folder_mode)
        self._ask_checkbox.setChecked(
            bool(self._settings.get("ask_output_file"))
        )
        self._on_output_mode_changed()
        if self._widget is not None:
            self._widget.set_text_dir(self._text_dir())

    def _save_output_settings(self) -> None:
        """Save the current Output section back to the settings file."""
        if not hasattr(self, "_settings"):
            return
        self._settings["output_mode"] = (
            "folder" if self._folder_radio.isChecked()
            else "next_to_original"
        )
        self._settings["output_folder"] = self._folder_edit.text().strip()
        self._settings["ask_output_file"] = self._ask_checkbox.isChecked()
        save_settings(self._settings)

    def _open_settings(self) -> None:
        """Open the Settings dialog from the gear button."""
        dialog = SettingsDialog(self, self._settings)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._settings = dialog.settings
        save_settings(self._settings)
        self._apply_settings_to_controls()
        self.log(
            "Settings saved "
            f"(output: {self._settings['output_mode']}, "
            f"text folder: {self._text_dir()}, "
            "widget at startup: "
            f"{'on' if self._settings.get('show_widget_on_start') else 'off'})."
        )

    def _on_output_mode_changed(self) -> None:
        enabled = self._folder_radio.isChecked()
        self._folder_edit_ref.setEnabled(enabled)
        self._folder_button_ref.setEnabled(enabled)
        # Changing the mode is a settings change too, so it is
        # remembered — but only once the controls exist.
        if hasattr(self, "_ask_checkbox"):
            self._save_output_settings()

    def _pick_output_folder(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, "Pick output folder")
        if chosen:
            self._output_dir = Path(chosen)
            self._folder_edit.setText(chosen)
            self._folder_radio.setChecked(True)
            self._save_output_settings()
            self.log(f"Output folder: {chosen}")

    def _output_dir_value(self):
        """Chosen output folder, or None for 'next to original'."""
        if self._folder_radio.isChecked() and self._output_dir is not None:
            return self._output_dir
        return None

    # -- drop window -------------------------------------------------------
    def _open_drop_window(self) -> None:
        if self._drop_window is None:
            self._drop_window = DropWindow(self)
        self._drop_window.show()
        self._drop_window.raise_()
        self.log("Drop window opened (drop a file there — it will ask what to do).")

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

    def _run_file_action(self, func, file_path=None) -> None:
        """Run a file action, respecting the Output settings.

        ``file_path`` is set by the Drop window; otherwise the picked
        file is used. When "ask for output file" is on, a Save dialog
        prefilled with the proposed name is shown first — the user
        can rename / relocate it, and the never-overwrite rule still
        applies to the chosen path. Pasted-text saving is untouched
        by this (it keeps its own save dialog in _paste_text).
        """
        target_file = file_path if file_path is not None else self._file
        if target_file is None:
            self.log("No file picked — pick a file first.")
            QMessageBox.warning(self, "No file", "Pick a file first.")
            return
        output_dir = self._output_dir_value()
        try:
            if self._ask_checkbox.isChecked():
                proposed = default_output_for(target_file, func, output_dir=output_dir)
                ext = proposed.suffix.lstrip(".").upper()
                chosen, _ = QFileDialog.getSaveFileName(
                    self,
                    "Save output as",
                    str(proposed),
                    f"{ext} (*{proposed.suffix});;All files (*.*)",
                )
                if not chosen:
                    self.log("Output save cancelled.")
                    return
                output = func(
                    target_file, output_path=Path(chosen),
                    **self._action_kwargs(func),
                )
            else:
                output = self._execute_file_action(func, target_file)
        except Exception as exc:
            self.log(f"FAILED {target_file.name}: {exc}")
            QMessageBox.warning(self, "Failed", f"{exc}")
        else:
            self.log(f"Saved: {output}")
            self._record_history(target_file.name, output)
            QMessageBox.information(self, "Done", f"Saved:\n{output.name}")

    def _paste_text(self) -> None:
        dialog = TextDialog(self)
        if dialog.exec() != TextDialog.DialogCode.Accepted:
            return
        text = dialog.text()
        if not text.strip():
            self.log("Pasted text was empty — nothing saved.")
            return
        # Ask what to do with the text: save dialog per kind, via a
        # small choice — Save .md is the default action here; the
        # floating ring offers the full set (md/txt/pdf/copy).
        # The dialog defaults to the text_folder setting (or the
        # Desktop default if that folder is missing).
        default = str(self._text_dir() / default_text_filename("md"))
        chosen, _ = QFileDialog.getSaveFileName(
            self, "Save pasted text", default,
            "Markdown (*.md);;Text (*.txt);;PDF (*.pdf)",
        )
        if not chosen:
            self.log("Text save cancelled.")
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
            self.log(f"FAILED text save: {exc}")
            QMessageBox.warning(self, "Failed", f"{exc}")
        else:
            self.log(f"Saved pasted text: {output}")

    def _toggle_widget(self) -> None:
        if self._widget is None:
            self._widget = FloatingWidget(text_dir=self._text_dir())
        if self._widget.isVisible():
            self._widget.hide()
            self.log("Floating widget hidden.")
        else:
            self._widget.show()
            self.log("Floating widget shown (quick path: drag a file onto it).")


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
