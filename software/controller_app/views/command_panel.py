"""Панель ввода команды: однострочный QLineEdit + Send."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QWidget

from .theme import industrial_button_qss, lineedit_qss


class CommandPanel(QWidget):
    command_submitted = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.setStyleSheet("background: transparent;")

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self.le_cmd = QLineEdit()
        self.le_cmd.setPlaceholderText("введи команду и нажми Enter (например: PING)")
        self.le_cmd.setMinimumHeight(36)
        self.le_cmd.setStyleSheet(lineedit_qss())
        self.le_cmd.returnPressed.connect(self._submit)

        self.btn_send = QPushButton("SEND")
        self.btn_send.setMinimumHeight(36)
        self.btn_send.setMinimumWidth(110)
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.setStyleSheet(industrial_button_qss())
        self.btn_send.clicked.connect(self._submit)

        row.addWidget(self.le_cmd, 1)
        row.addWidget(self.btn_send)

        self.setEnabled(False)

    def _submit(self) -> None:
        cmd = self.le_cmd.text().strip()
        if not cmd:
            return
        self.command_submitted.emit(cmd)
        self.le_cmd.clear()
