"""Настройки приложения (QSettings обёртка)."""
from __future__ import annotations

from PyQt6.QtCore import QSettings


class AppSettings:
    def __init__(self) -> None:
        self._s = QSettings("StepperControl", "controller_app")

    def get(self, key: str, default: object = None) -> object:
        return self._s.value(key, default)

    def set(self, key: str, value: object) -> None:
        self._s.setValue(key, value)