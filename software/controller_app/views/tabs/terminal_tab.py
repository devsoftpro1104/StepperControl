"""Вкладка ТЕРМИНАЛ: лог прошивки + raw command-line + clear-кнопка.

Лог тут — единственное окно, куда падают `+OK` / `-ERR` / `!event` /
комментарии и неизвестные строки. Высокочастотные стримы ($M, $T18, $H, $P)
сюда не пишутся (они визуализируются на других вкладках) — иначе при
50–100 Hz терминал перегружается.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from ..command_panel import CommandPanel
from ..log_panel import LogPanel
from ..panel import Panel
from ..theme import industrial_button_qss


class TerminalTab(QWidget):
    command_submitted = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")

        self.log = LogPanel()
        self.cmd = CommandPanel()

        self.btn_clear = QPushButton("CLEAR")
        self.btn_clear.setMinimumHeight(36)
        self.btn_clear.setMinimumWidth(110)
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.setStyleSheet(industrial_button_qss())
        self.btn_clear.clicked.connect(self.log.clear)

        log_panel = Panel("LOG")
        log_panel.add(self.log, 1)

        cmd_row = QHBoxLayout()
        cmd_row.setSpacing(8)
        cmd_row.addWidget(self.cmd, 1)
        cmd_row.addWidget(self.btn_clear)

        cmd_panel = Panel("COMMAND")
        cmd_panel.add_layout(cmd_row)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(log_panel, 1)
        layout.addWidget(cmd_panel)

        # forward
        self.cmd.command_submitted.connect(self.command_submitted)

    def append_log(self, text: str, severity: str = "raw") -> None:
        self.log.append_line(text, severity)
