"""Main local GUI window for CONVERTOR-APP (v0.2).

Written from scratch for this app, in PySide6. It is in the same
spirit as a local launcher window — sections, buttons, and a
timestamped log/console — but no code is copied from any other
launcher. The floating widget + ring menu stays as the quick path;
this window is the full local control panel for the same actions.

Sections:
  1. File — pick a file, or drag one onto the window
  2. Conversions — buttons for the document/image actions that fit
     the picked file (other buttons log a friendly "wrong file type"
     instead of crashing)
  3. Text — paste text, save it to the Desktop (default) as
     .md / .txt / .pdf, or copy it
  4. Log — timestamped console of what was converted and where
     it was saved

Everything runs locally. No upload, no account, no keys, no network.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .actions import (
    ACTIONS,
    DOCX_ACTIONS,
    MD_ACTIONS,
    PDF_ACTIONS,
    default_text_dir,
    default_text_filename,
    save_text_to_path,
    text_to_pdf_path,
)
from .widget import FloatingWidget, TextDialog


def _stamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


class MainWindow(QMainWindow):
    """Local control panel: file conversions + text + log."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CONVERTOR-APP v0.2")
        self.setMinimumSize(640, 560)
        self.setAcceptDrops(True)
        self._file: Path | None = None
        self._widget: FloatingWidget | None = None

        root = QWidget(self)
        layout = QVBoxLayout(root)

        # --- 1. File ---------------------------------------------------
        file_box = QGroupBox("1. File (pick one, or drag it onto this window)")
        file_layout = QHBoxLayout(file_box)
        self._file_label = QLabel("No file picked yet.")
        self._file_label.setWordWrap(True)
        pick = QPushButton("Pick file…")
        pick.clicked.connect(self._pick_file)
        file_layout.addWidget(self._file_label, stretch=1)
        file_layout.addWidget(pick)
        layout.addWidget(file_box)

        # --- 2. Conversions --------------------------------------------
        conv_box = QGroupBox("2. Conversions (run on the picked file)")
        conv_layout = QVBoxLayout(conv_box)
        self._buttons: list[tuple[str, object]] = []
        for label, func in (
            [("PDF → MD", PDF_ACTIONS[0][1])]
            + DOCX_ACTIONS
            + MD_ACTIONS
            + ACTIONS
        ):
            button = QPushButton(label)
            button.clicked.connect(lambda _=False, f=func: self._run_file_action(f))
            conv_layout.addWidget(button)
            self._buttons.append((label, func))
        layout.addWidget(conv_box)

        # --- 3. Text ----------------------------------------------------
        text_box = QGroupBox("3. Text (no file needed — saves default to Desktop)")
        text_layout = QHBoxLayout(text_box)
        paste = QPushButton("Paste text…")
        paste.clicked.connect(self._paste_text)
        widget_button = QPushButton("Floating widget: show / hide")
        widget_button.clicked.connect(self._toggle_widget)
        text_layout.addWidget(paste)
        text_layout.addWidget(widget_button)
        layout.addWidget(text_box)

        # --- 4. Log ------------------------------------------------------
        log_box = QGroupBox("4. Log (timestamped)")
        log_layout = QVBoxLayout(log_box)
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        log_layout.addWidget(self._log)
        layout.addWidget(log_box)

        self.setCentralWidget(root)
        self.log("CONVERTOR-APP v0.2 ready. Pick a file, or paste text.")

    # -- log ------------------------------------------------------------
    def log(self, message: str) -> None:
        self._log.appendPlainText(f"[{_stamp()}] {message}")

    # -- file picking / dropping -----------------------------------------
    def _pick_file(self) -> None:
        chosen, _ = QFileDialog.getOpenFileName(self, "Pick a file")
        if chosen:
            self._set_file(Path(chosen))

    def _set_file(self, path: Path) -> None:
        self._file = path
        self._file_label.setText(str(path))
        self.log(f"Picked: {path.name}")

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

    # -- actions -----------------------------------------------------------
    def _run_file_action(self, func) -> None:
        if self._file is None:
            self.log("No file picked — pick a file first.")
            QMessageBox.warning(self, "No file", "Pick a file first.")
            return
        try:
            output = func(self._file)
        except Exception as exc:
            self.log(f"FAILED {self._file.name}: {exc}")
            QMessageBox.warning(self, "Failed", f"{exc}")
        else:
            self.log(f"Saved: {output}")
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
        default = str(default_text_dir() / default_text_filename("md"))
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
            self._widget = FloatingWidget()
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
