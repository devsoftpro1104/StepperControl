"""Вкладка СОЕДИНЕНИЕ: подключение по COM + панель CLI-команд.

  - PORT       — combo COM + Refresh + Connect/Disconnect
  - CLI panel  — все команды прошивки, разложенные по подсистемам
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from ..cli_control_panel import CliControlPanel
from ..connection_panel import ConnectionPanel
from ..panel import Panel


class ConnectTab(QWidget):
    connect_requested    = Signal(str)
    disconnect_requested = Signal()
    command_requested    = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")

        self.connection = ConnectionPanel()
        self.cli        = CliControlPanel()
        self.cli.setEnabled(False)         # активна только при подключении

        port_panel = Panel("CONNECTION")
        port_panel.add(self.connection)

        cli_panel = Panel("CLI COMMANDS")
        cli_panel.add(self.cli)

        # ScrollArea на случай маленького окна — сетка команд высокая.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: 0; }")
        scroll_inner = QWidget()
        scroll_inner.setStyleSheet("background: transparent;")
        inner = QVBoxLayout(scroll_inner)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setSpacing(10)
        inner.addWidget(port_panel)
        inner.addWidget(cli_panel)
        inner.addStretch(1)
        scroll.setWidget(scroll_inner)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(scroll, 1)

        # Forward внутренние сигналы наружу
        self.connection.connect_requested.connect(self.connect_requested)
        self.connection.disconnect_requested.connect(self.disconnect_requested)
        self.cli.command_requested.connect(self.command_requested)

    # ---- слоты модели -------------------------------------------------

    def set_connected(self, connected: bool) -> None:
        self.connection.set_connected(connected)
        self.cli.setEnabled(connected)
