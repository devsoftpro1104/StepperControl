"""Загрузка иконок из qrc-ресурсов."""
from __future__ import annotations

from PyQt6.QtGui import QIcon


def play() -> QIcon: return QIcon(":/icons/icons/play.svg")
def stop() -> QIcon: return QIcon(":/icons/icons/stop.svg")