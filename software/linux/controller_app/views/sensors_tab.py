"""Вкладка ДАТЧИКИ: три графика стопкой.

  - TEMP   — DS18B20, °C    (диапазон −10…+60)
  - HALL   — AH49E, centered ADC counts (диапазон ±2048)
  - PROBE  — waveform-снимок после команды PROBE DUMP

Подписана на model.{temp,hall}_sample_received и model.dump_completed
через wiring в app.py.
"""

from __future__ import annotations

from kivy.uix.boxlayout import BoxLayout

from .dump_chart import DumpChart
from .scope_chart import ScopeChart


class SensorsTab(BoxLayout):
    def __init__(self, **kwargs) -> None:
        super().__init__(orientation="vertical", padding=6, spacing=4, **kwargs)

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
        self.probe = DumpChart(
            y_min=0, y_max=3.3,
            y_step_major=0.5, y_step_minor=0.1,
            axis_label="V", tick_fmt="{:.1f}",
            zero_line=False,
        )

        self.add_widget(self.temp)
        self.add_widget(self.hall)
        self.add_widget(self.probe)

    # ---- слоты модели --------------------------------------------------

    def on_temp_sample(self, s) -> None:
        self.temp.push_value(s.temp_c)

    def on_hall_sample(self, s) -> None:
        self.hall.push_value(s.centered)

    def show_dump(self, snap) -> None:
        self.probe.show_dump(snap.samples, snap.sample_hz)

    def reset(self) -> None:
        self.temp.reset()
        self.hall.reset()
        self.probe.reset()
