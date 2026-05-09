"""Панель лога: цветной read-only текст по severity-строке.

Цвета severity живут здесь — model держит severity как строку и не зависит
от Qt.GUI. Палитру окружения берём из theme.py.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QTextEdit

from .theme import (
    COL_AMBER, COL_DIGITAL, COL_GRN, COL_RED, COL_TEXT, COL_TEXT_DIM,
    textedit_qss,
)


_COLORS = {
    "ok":     QColor(COL_GRN),
    "err":    QColor(COL_RED),
    "event":  QColor(COL_AMBER),
    "stream": QColor(COL_DIGITAL),
    "cmt":    QColor(COL_TEXT_DIM),
    "raw":    QColor(COL_TEXT),
    "tx":     QColor("#ffffff"),
}
_DEFAULT = QColor(COL_TEXT)


class LogPanel(QTextEdit):
    def __init__(self, parent: Optional[QTextEdit] = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setStyleSheet(textedit_qss())

    def append_line(self, text: str, severity: str = "raw") -> None:
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        fmt = QTextCharFormat()
        fmt.setForeground(_COLORS.get(severity, _DEFAULT))
        cursor.insertText(text + "\n", fmt)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
