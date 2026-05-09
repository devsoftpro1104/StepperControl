"""Панель графика: pyqtgraph-плот для PROBE DUMP-снимка.

Стилистика осциллографа ЧПУ-стойки: глубокий чёрный фон, голубой
фосфорно-цианистый трейс с лёгким glow-подсветом. Для подсветки рисуем
кривую двумя слоями: широкий полупрозрачный «свет» под основным трейсом.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pyqtgraph as pg
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QVBoxLayout, QWidget

from .theme import (
    COL_BG_INSET, COL_DIGITAL, COL_DIGITAL_DIM, COL_PANEL_EDGE, COL_TEXT_DIM,
)


class PlotPanel(QWidget):
    VREF_V    = 3.3
    ADC_FULL  = 4095.0

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        pg.setConfigOption("background", COL_BG_INSET)
        pg.setConfigOption("foreground", COL_TEXT_DIM)
        pg.setConfigOption("antialias", True)

        self.plot = pg.PlotWidget()
        self.plot.setLabel("bottom", "time", units="µs")
        self.plot.setLabel("left",   "voltage", units="V")
        self.plot.showGrid(x=True, y=True, alpha=0.25)
        self.plot.getPlotItem().getViewBox().setBackgroundColor(COL_BG_INSET)

        # рамка под цвет панелей
        self.plot.setStyleSheet(
            f"border: 1px solid {COL_PANEL_EDGE}; border-radius: 4px;"
        )

        # Двухслойный тренд: широкий полупрозрачный «glow» снизу + резкая
        # тонкая линия сверху. setData у обеих кривых синхронизируется
        # одной точкой входа `show_dump`.
        glow_color = QColor(COL_DIGITAL); glow_color.setAlpha(60)
        self.glow_curve = self.plot.plot(
            pen=pg.mkPen(glow_color, width=6)
        )
        self.curve = self.plot.plot(
            pen=pg.mkPen(QColor(COL_DIGITAL), width=1.6)
        )

        # сетка чуть холоднее, чтобы не спорила с трейсом
        grid_color = QColor(COL_DIGITAL_DIM)
        for ax in ("left", "bottom"):
            axis = self.plot.getPlotItem().getAxis(ax)
            axis.setPen(pg.mkPen(grid_color))
            axis.setTextPen(pg.mkPen(QColor(COL_TEXT_DIM)))

        layout.addWidget(self.plot)

    def show_dump(self, samples: np.ndarray, sample_hz: int) -> None:
        n = int(samples.shape[0]) if samples is not None else 0
        if n == 0 or sample_hz <= 0:
            self.curve.clear()
            self.glow_curve.clear()
            return
        t = np.arange(n, dtype=np.float64) * (1_000_000.0 / sample_hz)
        v = samples.astype(np.float64) * (self.VREF_V / self.ADC_FULL)
        self.curve.setData(t, v)
        self.glow_curve.setData(t, v)
        self.plot.enableAutoRange(axis="xy", enable=True)
        self.plot.autoRange()

    def clear(self) -> None:
        self.curve.clear()
        self.glow_curve.clear()
