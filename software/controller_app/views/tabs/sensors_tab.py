"""Вкладка ДАТЧИКИ: TEMP rolling + waveform PROBE DUMP.

  - TEMP   — DS18B20, °C    (диапазон −10…+60)
  - PROBE  — waveform-снимок после команды PROBE DUMP

Подписаны на model.temp_sample_received и model.dump_completed.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QVBoxLayout, QWidget

from ..dump_chart import DumpChart
from ..panel import Panel
from ..scope_chart import ScopeChart


class SensorsTab(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")

        self.temp = ScopeChart(
            y_min=-10, y_max=60,
            y_step_major=10, y_step_minor=5,
            axis_label="°C", unit_label="°C",
            value_fmt="{:+7.2f}", tick_fmt="{:+.0f}",
            zero_line=True,
        )
        self.probe = DumpChart(
            y_min=0, y_max=3.3,
            y_step_major=0.5, y_step_minor=0.1,
            axis_label="V", unit_label="V",
            value_fmt="{:+5.2f}", tick_fmt="{:.1f}",
            zero_line=False,
        )

        temp_panel  = Panel("TEMPERATURE  ·  DS18B20  ·  $T18")
        temp_panel.add(self.temp, 1)

        probe_panel = Panel("PROBE DUMP WAVEFORM")
        probe_panel.add(self.probe, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(temp_panel,  1)
        layout.addWidget(probe_panel, 1)

    # ---- слоты модели --------------------------------------------------

    def on_temp_sample(self, s) -> None:
        self.temp.push_value(s.temp_c)

    def show_dump(self, samples, sample_hz: int) -> None:
        self.probe.show_dump(samples, sample_hz)

    def reset(self) -> None:
        self.temp.reset()
        self.probe.reset()
