"""Панель графика: pyqtgraph-плот для PROBE DUMP-снимка."""

from __future__ import annotations

from typing import Optional

import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QVBoxLayout, QWidget


class PlotPanel(QWidget):
    VREF_V    = 3.3
    ADC_FULL  = 4095.0

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        pg.setConfigOption("background", "#1e1e1e")
        pg.setConfigOption("foreground", "#cccccc")

        self.plot = pg.PlotWidget(title="PROBE DUMP waveform")
        self.plot.setLabel("bottom", "time", units="µs")
        self.plot.setLabel("left",   "voltage", units="V")
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.curve = self.plot.plot(pen=pg.mkPen("#ffd054", width=1))

        layout.addWidget(self.plot)

    def show_dump(self, samples: np.ndarray, sample_hz: int) -> None:
        n = int(samples.shape[0]) if samples is not None else 0
        if n == 0 or sample_hz <= 0:
            self.curve.clear()
            return
        t = np.arange(n, dtype=np.float64) * (1_000_000.0 / sample_hz)
        v = samples.astype(np.float64) * (self.VREF_V / self.ADC_FULL)
        self.curve.setData(t, v)
        self.plot.enableAutoRange(axis="xy", enable=True)
        self.plot.autoRange()

    def clear(self) -> None:
        self.curve.clear()
