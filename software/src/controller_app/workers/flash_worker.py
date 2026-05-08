"""Воркер обновления прошивки (через UDS или bootloader)."""
from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal


class FlashWorker(QObject):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool)