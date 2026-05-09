"""Панель соединения: COM-порт + Refresh + Connect/Disconnect + PROBE DUMP + Clear."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QPushButton, QWidget
from serial.tools import list_ports


class ConnectionPanel(QWidget):
    connect_requested    = Signal(str)        # выбранный порт
    disconnect_requested = Signal()
    dump_requested       = Signal()
    clear_log_requested  = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._connected = False

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)

        self.cb_port = QComboBox()
        self.cb_port.setMinimumWidth(160)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.refresh_ports)

        self.btn_connect = QPushButton("Connect")
        self.btn_connect.clicked.connect(self._on_connect_clicked)

        self.btn_dump = QPushButton("PROBE DUMP")
        self.btn_dump.setEnabled(False)
        self.btn_dump.clicked.connect(self.dump_requested)

        self.btn_clear = QPushButton("Clear log")
        self.btn_clear.clicked.connect(self.clear_log_requested)

        row.addWidget(self.cb_port)
        row.addWidget(self.btn_refresh)
        row.addWidget(self.btn_connect)
        row.addStretch(1)
        row.addWidget(self.btn_dump)
        row.addWidget(self.btn_clear)

        self.refresh_ports()

    def refresh_ports(self) -> None:
        self.cb_port.clear()
        for p in list_ports.comports():
            label = f"{p.device}  ({p.description})" if p.description else p.device
            self.cb_port.addItem(label, userData=p.device)
        if self.cb_port.count() == 0:
            self.cb_port.addItem("(нет портов)", userData=None)

    def set_connected(self, connected: bool) -> None:
        self._connected = connected
        self.btn_connect.setText("Disconnect" if connected else "Connect")
        self.btn_dump.setEnabled(connected)

    def _on_connect_clicked(self) -> None:
        if self._connected:
            self.disconnect_requested.emit()
            return
        port = self.cb_port.currentData()
        if port:
            self.connect_requested.emit(port)
