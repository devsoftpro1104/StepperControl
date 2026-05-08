"""QObject-воркер, держащий соединение в отдельном потоке."""
from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal


class ConnectionWorker(QObject):
    connected    = pyqtSignal()
    disconnected = pyqtSignal()
    error        = pyqtSignal(str)