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
    QLabel,
    QMessageBox,
    QPushButton,
    QWidget,
)

from .actions import ACTIONS


class RingMenu(QWidget):
    """A frameless popup with action buttons arranged in a circle."""

    def __init__(self, file_path: Path, center: QPoint):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._file_path = file_path
        radius = 110
        size = radius * 2 + 90
        self.setGeometry(center.x() - size // 2, center.y() - size // 2, size, size)
        for index, (label, func) in enumerate(ACTIONS):
            angle = 2 * math.pi * index / len(ACTIONS) - math.pi / 2
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
            output = func(self._file_path)
        except Exception as exc:  # show it, do not crash the widget
            QMessageBox.warning(self, "Failed", f"{exc}")
        else:
            QMessageBox.information(
                self, "Done", f"Saved:\n{output.name}"
            )
        self.close()


class FloatingWidget(QWidget):
    """Small draggable desktop widget that accepts dropped files."""

    def __init__(self):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAcceptDrops(True)
        self.setGeometry(100, 100, 72, 72)
        self._drag_offset = QPoint()
        self._ring: RingMenu | None = None

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
        center = self.geometry().center()
        self._ring = RingMenu(file_path, center)
        self._ring.show()


def main() -> int:
    app = QApplication(sys.argv)
    widget = FloatingWidget()
    widget.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
