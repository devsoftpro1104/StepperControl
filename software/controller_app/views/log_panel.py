"""Панель лога: цветной read-only текст по severity-строке.

Цвета живут здесь — model держит severity как строку и не зависит от Qt.GUI.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QTextEdit


_COLORS = {
    "ok":     QColor("#7ec77e"),
    "err":    QColor("#e26464"),
    "event":  QColor("#e2c264"),
    "stream": QColor("#7ec0e2"),
    "cmt":    QColor("#999999"),
    "raw":    QColor("#cccccc"),
    "tx":     QColor("#ffffff"),
}
_DEFAULT = QColor("#cccccc")


class LogPanel(QTextEdit):
    def __init__(self, parent: Optional[QTextEdit] = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setStyleSheet(
            "background:#1e1e1e; color:#eaeaea; "
            "font-family:Consolas,monospace; font-size:11pt;"
        )

    def append_line(self, text: str, severity: str = "raw") -> None:
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        fmt = QTextCharFormat()
        fmt.setForeground(_COLORS.get(severity, _DEFAULT))
        cursor.insertText(text + "\n", fmt)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
