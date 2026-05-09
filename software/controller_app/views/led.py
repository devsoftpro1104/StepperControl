"""Светодиодный индикатор: маленький круглый огонёк с радиальным градиентом.

Используется в шапке окна: LINK (есть подключение к COM) и DUMP (идёт сборка
PROBE DUMP). Отдельный виджет, чтобы расширять — добавить FAULT, RUN и т.п.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QRectF
from PySide6.QtGui import QBrush, QColor, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget

from .theme import COL_GRN, COL_LED_OFF, COL_PANEL_EDGE


class Led(QWidget):
    def __init__(self, color_on: str = COL_GRN,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(18, 18)
        self._on    = False
        self._color = QColor(color_on)

    def set_on(self, on: bool) -> None:
        if on != self._on:
            self._on = on
            self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(2, 2, 14, 14)
        if self._on:
            grad = QRadialGradient(
                rect.center().x() - 2, rect.center().y() - 2, 10
            )
            grad.setColorAt(0.0, self._color.lighter(160))
            grad.setColorAt(1.0, self._color.darker(180))
            p.setBrush(QBrush(grad))
            glow = QColor(self._color); glow.setAlpha(80)
            p.setPen(QPen(glow, 2))
        else:
            p.setBrush(QBrush(QColor(COL_LED_OFF)))
            p.setPen(QPen(QColor(COL_PANEL_EDGE), 1.2))
        p.drawEllipse(rect)
