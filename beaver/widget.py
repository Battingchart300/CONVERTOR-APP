"""Floating widget + ring menu. Own implementation, PySide6.

The widget is a small, always-on-top, draggable circle. Dropping a
file onto it opens a ring of action buttons around it. Clicking one
runs that action on the dropped file (see ``actions.py``) and shows
a short success / failure message. Nothing leaves the local PC.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QLabel,
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
    ODP_ACTIONS,
    ODS_ACTIONS,
    ODT_ACTIONS,
    PDF_ACTIONS,
    default_text_dir,
    default_text_filename,
    save_text_to_path,
    text_to_pdf_path,
)


class RingMenu(QWidget):
    """A frameless popup with action buttons arranged in a circle.

    ``items`` is a list of (label, callable) pairs; each callable takes
    no arguments and returns a Path (saved file), a str (message to
    show, e.g. "Copied"), or None (user cancelled — close silently).
    """

    def __init__(self, items, center: QPoint):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        radius = 110
        size = radius * 2 + 90
        self.setGeometry(center.x() - size // 2, center.y() - size // 2, size, size)
        for index, (label, func) in enumerate(items):
            angle = 2 * math.pi * index / len(items) - math.pi / 2
            x = size // 2 + int(radius * math.cos(angle)) - 45
            y = size // 2 + int(radius * math.sin(angle)) - 18
            button = QPushButton(label, self)
            button.setGeometry(x, y, 90, 36)
            button.setStyleSheet(
                "QPushButton { background: #2b2b2b; color: white; "
                "border: 2px solid #888; border-radius: 10px; }"
                "QPushButton:hover { background: #3d5a80; }"
            )
            button.clicked.connect(lambda _=False, f=func: self._run(f))
        close = QPushButton("✕", self)
        close.setGeometry(size // 2 - 18, size // 2 - 18, 36, 36)
        close.setStyleSheet(
            "QPushButton { background: #555; color: white; "
            "border: 2px solid #888; border-radius: 18px; }"
        )
        close.clicked.connect(self.close)

    def _run(self, func) -> None:
        try:
            output = func()
        except Exception as exc:  # show it, do not crash the widget
            QMessageBox.warning(self, "Failed", f"{exc}")
        else:
            if output is None:
                pass  # user cancelled a save dialog — nothing to report
            elif isinstance(output, Path):
                QMessageBox.information(self, "Done", f"Saved:\n{output.name}")
            else:
                QMessageBox.information(self, "Done", str(output))
        self.close()


class TextDialog(QDialog):
    """Paste dialog for text-only input (no file needed)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Paste text")
        self.setMinimumSize(420, 320)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Paste or type text, then OK:"))
        self.editor = QPlainTextEdit(self)
        self.editor.setPlaceholderText("Paste text here…")
        layout.addWidget(self.editor)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def text(self) -> str:
        return self.editor.toPlainText()


class FloatingWidget(QWidget):
    """Small draggable desktop widget that accepts dropped files.

    v0.2: a "Text" button under the circle opens a paste dialog, so
    text can be used with no file at all.
    """

    def __init__(self, text_dir=None):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAcceptDrops(True)
        self.setGeometry(100, 100, 72, 106)
        self._drag_offset = QPoint()
        self._ring: RingMenu | None = None
        # Default folder for the widget's own paste dialogs. The
        # main window passes its text_folder setting; standalone
        # use (widget main) keeps the Desktop default.
        self._text_dir: Path = (
            Path(text_dir) if text_dir is not None else default_text_dir()
        )

    def set_text_dir(self, text_dir) -> None:
        """Update the paste-dialog default folder (Settings change)."""
        if text_dir is not None:
            self._text_dir = Path(text_dir)

        # Original icon drawn in code: a plain circle with an emoji
        # label. No third-party artwork is embedded anywhere.
        label = QLabel("🦫", self)
        label.setGeometry(0, 0, 72, 72)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(
            "QLabel { font-size: 40px; background: #8a5a2b; "
            "border: 3px solid #4a2f14; border-radius: 36px; }"
        )
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        text_button = QPushButton("Text", self)
        text_button.setGeometry(6, 76, 60, 26)
        text_button.setStyleSheet(
            "QPushButton { background: #2b2b2b; color: white; "
            "border: 2px solid #888; border-radius: 8px; }"
            "QPushButton:hover { background: #3d5a80; }"
        )
        text_button.clicked.connect(self._open_text)

    def _open_text(self) -> None:
        dialog = TextDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        text = dialog.text()
        if not text.strip():
            QMessageBox.warning(self, "Empty", "No text pasted — nothing to do.")
            return
        items = [
            ("Save .md", lambda: self._save_text(text, "md")),
            ("Save .txt", lambda: self._save_text(text, "txt")),
            ("To PDF", lambda: self._save_pasted_pdf(text)),
            ("To HTML", lambda: self._save_text(text, "html")),
            ("Copy", lambda: self._copy_text(text)),
        ]
        center = self.geometry().center()
        self._ring = RingMenu(items, center)
        self._ring.show()

    def _save_text(self, text: str, kind: str):
        """Save pasted text via a dialog with a sensible default name.

        The dialog defaults to the widget's text folder (the main
        window's text_folder setting, else the Desktop default)
        and a ``text-<date>.<ext>`` name. If the chosen file already
        exists, save_text_to_path applies the _2/_3 rule instead of
        overwriting.
        """
        default = str(self._text_dir / default_text_filename(kind))
        filters = {
            "md": "Markdown (*.md)",
            "txt": "Text (*.txt)",
            "html": "HTML (*.html)",
        }[kind]
        chosen, _ = QFileDialog.getSaveFileName(self, "Save text", default, filters)
        if not chosen:
            return None
        return save_text_to_path(text, chosen, kind)

    def _save_pasted_pdf(self, text: str):
        """Save pasted text as PDF, dialog defaults to the text folder."""
        default = str(self._text_dir / default_text_filename("pdf"))
        chosen, _ = QFileDialog.getSaveFileName(
            self, "Save text as PDF", default, "PDF (*.pdf)"
        )
        if not chosen:
            return None
        return text_to_pdf_path(text, chosen)

    def _copy_text(self, text: str) -> str:
        QApplication.clipboard().setText(text)
        return "Copied to clipboard."

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
        super().mouseMoveEvent(event)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        urls = event.mimeData().urls()
        if not urls:
            return
        file_path = Path(urls[0].toLocalFile())
        if not file_path.is_file():
            QMessageBox.warning(self, "Failed", "Drop a single file, not a folder.")
            return
        # Route by extension (v0.3 adds .odt/.ods/.odp): .md -> MD
        # ring, .pdf -> PDF ring, .docx -> Word ring, .odt/.ods/.odp
        # -> LibreOffice rings, everything else keeps the v0.1 image
        # ring, which fails gracefully on non-images. Single-argument
        # calls still work: the new output_dir / output_path
        # parameters in actions.py are optional.
        suffix = file_path.suffix.lower()
        if suffix in (".md", ".markdown"):
            actions = MD_ACTIONS
        elif suffix == ".pdf":
            actions = PDF_ACTIONS
        elif suffix == ".docx":
            actions = DOCX_ACTIONS
        elif suffix == ".odt":
            actions = ODT_ACTIONS
        elif suffix == ".ods":
            actions = ODS_ACTIONS
        elif suffix == ".odp":
            actions = ODP_ACTIONS
        else:
            actions = ACTIONS
        items = [
            (label, (lambda f=func, p=file_path: f(p)))
            for label, func in actions
        ]
        center = self.geometry().center()
        self._ring = RingMenu(items, center)
        self._ring.show()


def main() -> int:
    app = QApplication(sys.argv)
    widget = FloatingWidget()
    widget.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
