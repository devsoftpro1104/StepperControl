"""Воркер приёма стрима телеметрии."""
from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal


class TelemetryWorker(QObject):
    sample = pyqtSignal(object)  # TelemetrySample