"""Вкладка ДАТЧИКИ: три rolling-графика по каналам прошивки.

  - TEMP   — DS18B20, °C    (диапазон −10…+60)
  - HALL   — AH49E, raw ADC (диапазон 0…4095)
  - PROBE  — self-probe ADC (диапазон 0…4095)

Подписаны на model.{temp,hall,probe}_sample_received.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QVBoxLayout, QWidget

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
        self.hall = ScopeChart(
            y_min=-2048, y_max=2047,
            y_step_major=500, y_step_minor=100,
            axis_label="ADC", unit_label="ctr",
            value_fmt="{:+7.0f}", tick_fmt="{:+.0f}",
            zero_line=True,
        )
        self.probe = ScopeChart(
            y_min=0, y_max=4095,
            y_step_major=500, y_step_minor=100,
            axis_label="ADC", unit_label="raw",
            value_fmt="{:7.0f}", tick_fmt="{:.0f}",
            zero_line=False,
        )

        temp_panel  = Panel("TEMPERATURE  ·  DS18B20  ·  $T18")
        temp_panel.add(self.temp, 1)

        hall_panel  = Panel("HALL SENSOR  ·  AH49E  ·  $H")
        hall_panel.add(self.hall, 1)

        probe_panel = Panel("PROBE  ·  ADC2/PA0  ·  $P")
        probe_panel.add(self.probe, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(temp_panel,  1)
        layout.addWidget(hall_panel,  1)
        layout.addWidget(probe_panel, 1)

    # ---- слоты модели --------------------------------------------------

    def on_temp_sample(self, s) -> None:
        self.temp.push_value(s.temp_c)

    def on_hall_sample(self, s) -> None:
        self.hall.push_value(s.centered)

    def on_probe_sample(self, s) -> None:
        self.probe.push_value(s.adc)

    def reset(self) -> None:
        self.temp.reset()
        self.hall.reset()
        self.probe.reset()
