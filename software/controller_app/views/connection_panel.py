"""Панель подключения: COM-порт + Refresh + Connect/Disconnect.

Команды CLI (PROBE DUMP, CLEAR LOG и т.п.) живут отдельно — в
CliControlPanel и TerminalTab. Здесь только всё, что относится к
установлению/разрыву связи.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QPushButton, QWidget
from serial.tools import list_ports

from .theme import combobox_qss, industrial_button_qss


class ConnectionPanel(QWidget):
    connect_requested    = Signal(str)
    disconnect_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._connected = False

        self.setStyleSheet("background: transparent;")

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self.cb_port = QComboBox()
        self.cb_port.setMinimumWidth(260)
        self.cb_port.setMinimumHeight(36)
        self.cb_port.setStyleSheet(combobox_qss())

        self.btn_refresh = QPushButton("⟳")
        self.btn_refresh.setFixedSize(36, 36)
        self.btn_refresh.setToolTip("Обновить список портов")

        self.btn_connect = QPushButton("CONNECT")
        self.btn_connect.setCheckable(True)
        self.btn_connect.setMinimumWidth(160)
        self.btn_connect.setMinimumHeight(36)

        for b in (self.btn_refresh, self.btn_connect):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(industrial_button_qss())

        self.btn_refresh.clicked.connect(self.refresh_ports)
        self.btn_connect.clicked.connect(self._on_connect_clicked)

        row.addWidget(self.cb_port, 1)
        row.addWidget(self.btn_refresh)
        row.addWidget(self.btn_connect)

        self.refresh_ports()

    def refresh_ports(self) -> None:
        prev = self.cb_port.currentData()
        self.cb_port.clear()
        for p in list_ports.comports():
            label = f"{p.device}  —  {p.description}" if p.description else p.device
            self.cb_port.addItem(label, userData=p.device)
        if self.cb_port.count() == 0:
            self.cb_port.addItem("(нет портов)", userData=None)
        if prev:
            idx = self.cb_port.findData(prev)
            if idx >= 0:
                self.cb_port.setCurrentIndex(idx)

    def set_connected(self, connected: bool) -> None:
        self._connected = connected
        self.btn_connect.setText("DISCONNECT" if connected else "CONNECT")
        self.btn_connect.setChecked(connected)

    def _on_connect_clicked(self) -> None:
        if self._connected:
            self.disconnect_requested.emit()
            return
        port = self.cb_port.currentData()
        if port:
            self.connect_requested.emit(port)
