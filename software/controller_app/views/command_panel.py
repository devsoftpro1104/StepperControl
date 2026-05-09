"""Панель ввода команды: однострочный QLineEdit + Send."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QWidget


class CommandPanel(QWidget):
    command_submitted = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)

        self.le_cmd = QLineEdit()
        self.le_cmd.setPlaceholderText("введи команду и нажми Enter (например: PING)")
        self.le_cmd.returnPressed.connect(self._submit)

        self.btn_send = QPushButton("Send")
        self.btn_send.clicked.connect(self._submit)

        row.addWidget(self.le_cmd)
        row.addWidget(self.btn_send)

        self.setEnabled(False)

    def _submit(self) -> None:
        cmd = self.le_cmd.text().strip()
        if not cmd:
            return
        self.command_submitted.emit(cmd)
        self.le_cmd.clear()
