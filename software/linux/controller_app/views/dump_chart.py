"""One-shot осциллограф для PROBE DUMP.

Та же тёмная коробка, что у ScopeChart, но вместо rolling-окна —
жёстко-длинный снимок: ось X = время от 0 до n/sample_hz. Сигнал —
напряжение по 12-битному ADC × VREF.

Большой readout — измеренная частота STEP-импульсов по средней линии
(амплитуда / 2). Если signal плоский, freq = 0.

Эквивалент `views/dump_chart.py` PySide6-версии.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np

from kivy.graphics import Color, Line
from kivy.uix.label import Label

from .chart_base import _BaseChart
from .theme import (
    COL_DIGITAL, COL_DIGITAL_DIM, COL_LABEL, RGBA_DIGITAL,
    hex_to_rgba,
)


class DumpChart(_BaseChart):
    VREF_V   = 3.3
    ADC_FULL = 4095.0

    def __init__(
        self,
        *,
        y_min: float = 0.0, y_max: float = 3.3,
        y_step_major: float = 0.5, y_step_minor: float = 0.1,
        axis_label: str = "V",
        tick_fmt: str = "{:.1f}",
        zero_line: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(
            y_min=y_min, y_max=y_max,
            y_step_major=y_step_major, y_step_minor=y_step_minor,
            axis_label=axis_label, tick_fmt=tick_fmt,
            zero_line=zero_line, time_label="TIME",
            **kwargs,
        )

        self._t_us: Optional[np.ndarray] = None
        self._v:    Optional[np.ndarray] = None
        self._t_max_us:  float = 0.0
        self._freq_hz:   float = 0.0
        self._period_us: float = 0.0
        self._has_data:  bool  = False

        # 3-слойная фосфорная трасса (как в ScopeChart).
        self._trace_lines: list[tuple[Color, Line]] = []
        with self.canvas:
            for width, alpha in ((7.0, 0.22), (3.4, 0.55), (1.6, 1.0)):
                col = Color(*RGBA_DIGITAL[:3], alpha)
                ln  = Line(points=[], width=width, cap="round", joint="round")
                self._trace_lines.append((col, ln))

        # X-сетка / X-метки. Пул — макс. ~12 делений (1-2-5 шаг).
        self._x_grid_lines: list[tuple[Color, Line]] = []
        self._x_lbls: list[Label] = []
        self._build_x_pool()

        # Большой readout с измеренной частотой.
        self._big_readout = Label(
            text="— — —",
            color=hex_to_rgba(COL_DIGITAL_DIM),
            font_name="RobotoMono-Regular",
            font_size="22sp", bold=True,
            halign="right", valign="middle",
            size_hint=(None, None), size=(260, 36),
        )
        self._big_readout.bind(
            size=lambda *_: setattr(self._big_readout, "text_size",
                                    self._big_readout.size),
        )
        self._unit_lbl = Label(
            text="STEP FREQ",
            color=hex_to_rgba(COL_LABEL),
            bold=True, font_size="9sp",
            halign="right", valign="middle",
            size_hint=(None, None), size=(260, 14),
        )
        self._unit_lbl.bind(
            size=lambda *_: setattr(self._unit_lbl, "text_size",
                                    self._unit_lbl.size),
        )
        self.add_widget(self._big_readout)
        self.add_widget(self._unit_lbl)

        self.bind(pos=lambda *_: self._refresh(),
                  size=lambda *_: self._refresh())

    # ---- API ---------------------------------------------------------

    def show_dump(self, samples: np.ndarray, sample_hz: int) -> None:
        n = int(samples.shape[0]) if samples is not None else 0
        if n == 0 or sample_hz <= 0:
            self.clear()
            return
        t_us = np.arange(n, dtype=np.float64) * (1_000_000.0 / sample_hz)
        v    = samples.astype(np.float64) * (self.VREF_V / self.ADC_FULL)
        self._t_us     = t_us
        self._v        = v
        self._t_max_us = float(t_us[-1]) if n > 1 else 1.0
        self._freq_hz, self._period_us = self._measure_freq(samples, sample_hz)
        self._has_data = True
        self._refresh()

    def clear(self) -> None:
        self._t_us     = None
        self._v        = None
        self._t_max_us = 0.0
        self._freq_hz  = 0.0
        self._period_us = 0.0
        self._has_data = False
        self._refresh()

    def reset(self) -> None:
        self.clear()

    @staticmethod
    def _measure_freq(samples: np.ndarray, sample_hz: int) -> tuple[float, float]:
        """Восходящие фронты по midpoint-порогу → средний период → freq."""
        n = int(samples.shape[0])
        if n < 4 or sample_hz <= 0:
            return 0.0, 0.0
        s_min = float(samples.min())
        s_max = float(samples.max())
        if s_max - s_min < 200:
            return 0.0, 0.0
        mid = (s_min + s_max) * 0.5
        above = samples >= mid
        rising = np.where(np.diff(above.astype(np.int8)) > 0)[0]
        if rising.size < 2:
            return 0.0, 0.0
        period_samples = (rising[-1] - rising[0]) / (rising.size - 1)
        if period_samples <= 0:
            return 0.0, 0.0
        period_us = period_samples * 1_000_000.0 / sample_hz
        freq_hz   = sample_hz / period_samples
        return freq_hz, period_us

    @staticmethod
    def _nice_time_step(span_us: float) -> tuple[float, str]:
        """Подобрать «красивый» шаг сетки по X и unit ('µs' или 'ms')."""
        if span_us <= 0:
            return 1.0, "µs"
        target = span_us / 8.0
        unit  = "µs"
        scale = 1.0
        if target >= 1000.0:
            unit  = "ms"
            scale = 1000.0
            target = target / scale
        exp = math.floor(math.log10(target)) if target > 0 else 0
        base = 10 ** exp
        for m in (1, 2, 5, 10):
            if m * base >= target:
                step_unit = m * base
                return step_unit * scale, unit
        return 10 * base * scale, unit

    # ---- X-pool (создаётся один раз) ---------------------------------

    def _build_x_pool(self) -> None:
        with self.canvas.before:
            r, g, b, _ = RGBA_DIGITAL
            for _ in range(12):
                col = Color(r, g, b, 0.22)
                ln  = Line(points=[0, 0, 0, 0], width=1.0)
                self._x_grid_lines.append((col, ln))
        for _ in range(12):
            lbl = Label(
                text="", color=hex_to_rgba(COL_LABEL),
                bold=True, font_size="9sp",
                font_name="RobotoMono-Regular",
                halign="center", valign="middle",
                size_hint=(None, None), size=(60, 16),
            )
            lbl.bind(size=lambda i, _s: setattr(i, "text_size", i.size))
            self.add_widget(lbl)
            self._x_lbls.append(lbl)

    # ---- refresh -----------------------------------------------------

    def _refresh(self) -> None:
        if self.width <= 4 or self.height <= 4:
            return

        px, py, pw, ph = self._plot_rect()
        plot_l, plot_b = px, py
        plot_r = px + pw
        plot_t = py + ph

        # ---- Time grid + labels ----
        t_span = self._t_max_us if self._has_data and self._t_max_us > 0 else 1000.0
        t_step_us, t_unit = self._nice_time_step(t_span)
        t_scale = 1000.0 if t_unit == "ms" else 1.0

        def t_to_x(t_us: float) -> float:
            return plot_l + (t_us / t_span) * pw

        t = 0.0
        i_slot = 0
        while t <= t_span + 1e-6 and i_slot < len(self._x_grid_lines):
            x = t_to_x(t)
            if plot_l - 0.5 <= x <= plot_r + 0.5:
                _, ln = self._x_grid_lines[i_slot]
                ln.points = [x, plot_b, x, plot_t]
                lbl = self._x_lbls[i_slot]
                lbl.text = f"{t / t_scale:g}{t_unit}"
                lbl.pos  = (x - lbl.width / 2, plot_b - 22)
                i_slot += 1
            t += t_step_us

        for k in range(i_slot, len(self._x_grid_lines)):
            self._x_grid_lines[k][1].points = [0, 0, 0, 0]
            self._x_lbls[k].text = ""

        # ---- Trace ----
        if (self._has_data and self._t_us is not None and self._v is not None
                and self._t_us.shape[0] >= 2):
            y_min, y_max = self._y_min, self._y_max
            pts: list[float] = []
            for ts, rv in zip(self._t_us, self._v):
                x = t_to_x(float(ts))
                rv_clip = max(y_min, min(y_max, float(rv)))
                y = self.v_to_y(rv_clip)
                pts.append(x); pts.append(y)
            for _c, ln in self._trace_lines:
                ln.points = pts
        else:
            for _c, ln in self._trace_lines:
                ln.points = []

        # ---- Большой readout ----
        has_freq = self._has_data and self._freq_hz > 0
        if has_freq:
            self._big_readout.text  = f"{self._freq_hz:,.0f} Hz"
            self._big_readout.color = hex_to_rgba(COL_DIGITAL)
            if self._period_us < 1000.0:
                self._unit_lbl.text = f"T = {self._period_us:.1f} µs"
            else:
                self._unit_lbl.text = f"T = {self._period_us / 1000.0:.2f} ms"
        else:
            self._big_readout.text  = "— — —"
            self._big_readout.color = hex_to_rgba(COL_DIGITAL_DIM)
            self._unit_lbl.text = "STEP FREQ"

        self._big_readout.pos = (
            plot_r - self._big_readout.width - 14,
            plot_t - self._big_readout.height - 6,
        )
        self._unit_lbl.pos = (
            plot_r - self._unit_lbl.width - 14,
            plot_t - self._big_readout.height - 6 - self._unit_lbl.height,
        )
