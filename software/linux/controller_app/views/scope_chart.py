"""Жильной осциллограф: rolling time-series с цианистым фосфорным трейсом.

Параметризован по диапазону Y, шагам сетки и форматам подписей. Один и
тот же класс рисует TEMP (signed °C) и HALL (centered ADC). Конкретные
настройки задаёт фабрика из `sensors_tab.py`.

Обновление:
  - сетка / подписи Y / axis label / TIME — `_BaseChart._rebuild_static`
    (только при resize).
  - X-сетка / подписи времени — `_rebuild_time_layer` (при tick — раз в
    50 мс — оси «ползут» с временем).
  - 3-слойная фосфорная трасса — три долгоживущих `Line`-инструкции с
    обновлением `.points` каждый tick.
  - Курсор-точка справа и большой readout — Label-ы, обновляются на push.
"""

from __future__ import annotations

import math
import time
from collections import deque
from typing import Optional

from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Line
from kivy.uix.label import Label

from .chart_base import _BaseChart
from .theme import (
    COL_DIGITAL, COL_DIGITAL_DIM, COL_LABEL, RGBA_DIGITAL,
    hex_to_rgba,
)


class ScopeChart(_BaseChart):
    WINDOW_S       = 30.0      # ширина окна, секунд
    SEC_STEP_MAJOR = 5         # шаг вертикальных делений по времени, с
    TICK_HZ        = 20        # частота перерисовки

    def __init__(
        self,
        y_min: float, y_max: float,
        y_step_major: float, y_step_minor: float,
        *,
        axis_label: str = "VALUE",
        unit_label: Optional[str] = None,
        value_fmt: str = "{:+7.1f}",
        tick_fmt: str  = "{:+.0f}",
        zero_line: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(
            y_min=y_min, y_max=y_max,
            y_step_major=y_step_major, y_step_minor=y_step_minor,
            axis_label=axis_label, tick_fmt=tick_fmt,
            zero_line=zero_line, time_label="TIME",
            **kwargs,
        )

        self._unit_label = unit_label if unit_label is not None else axis_label
        self._value_fmt  = value_fmt

        self._samples: deque[tuple[float, float]] = deque()
        self._t0: Optional[float] = None
        self._current: float = (y_min + y_max) / 2.0
        self._idle_value: float = self._current
        self._has_data: bool = False

        # ---- 3-слойная трасса. Долгоживущие Line — обновляем .points. ---
        self._trace_lines: list[tuple[Color, Line]] = []
        with self.canvas:
            for width, alpha in ((7.0, 0.22), (3.4, 0.55), (1.6, 1.0)):
                col = Color(*RGBA_DIGITAL[:3], alpha)
                ln  = Line(points=[], width=width, cap="round", joint="round")
                self._trace_lines.append((col, ln))
            # Точка курсора справа.
            self._cursor_glow_color = Color(*RGBA_DIGITAL[:3], 0.32)
            self._cursor_glow       = Ellipse(pos=(0, 0), size=(0, 0))
            self._cursor_dot_color  = Color(*RGBA_DIGITAL)
            self._cursor_dot        = Ellipse(pos=(0, 0), size=(0, 0))

        # ---- большой readout текущего значения ----
        self._big_readout = Label(
            text="— — —", markup=False,
            color=hex_to_rgba(COL_DIGITAL_DIM),
            font_name="RobotoMono-Regular",
            font_size="22sp", bold=True,
            halign="right", valign="middle",
            size_hint=(None, None), size=(220, 36),
        )
        self._big_readout.bind(
            size=lambda *_: setattr(self._big_readout, "text_size",
                                    self._big_readout.size),
        )
        self._unit_lbl = Label(
            text=self._unit_label,
            color=hex_to_rgba(COL_LABEL),
            bold=True, font_size="9sp",
            halign="right", valign="middle",
            size_hint=(None, None), size=(220, 14),
        )
        self._unit_lbl.bind(
            size=lambda *_: setattr(self._unit_lbl, "text_size",
                                    self._unit_lbl.size),
        )
        self.add_widget(self._big_readout)
        self.add_widget(self._unit_lbl)

        # X-сетка / X-подписи (динамика). Отдельные long-lived Line + пул
        # Label-ов, чтобы не пересоздавать их каждые 50 мс.
        self._x_grid_lines: list[tuple[Color, Line]] = []
        self._x_lbls: list[Label] = []
        self._build_x_pool()

        # tick: продлеваем трассу + двигаем X-сетку.
        Clock.schedule_interval(lambda _dt: self._tick(), 1.0 / self.TICK_HZ)

    # ---- публичный API ------------------------------------------------

    def push_value(self, v: float) -> None:
        if self._t0 is None:
            self._t0 = time.monotonic()
        self._current  = float(v)
        self._has_data = True
        self._samples.append((time.monotonic() - self._t0, float(v)))

    def reset(self) -> None:
        self._samples.clear()
        self._t0       = None
        self._current  = self._idle_value
        self._has_data = False

    # ---- X-pool (создаётся один раз, переиспользуется) ---------------

    def _build_x_pool(self) -> None:
        # Сколько меток умещается в окне 30s с шагом 5s — 7 точек (на
        # -30, -25, ..., 0). С запасом — 10 Line + 10 Label.
        with self.canvas.before:
            r, g, b, _ = RGBA_DIGITAL
            for _ in range(10):
                col = Color(r, g, b, 0.22)
                ln  = Line(points=[0, 0, 0, 0], width=1.0)
                self._x_grid_lines.append((col, ln))
        for _ in range(10):
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

    # ---- tick ---------------------------------------------------------

    def _tick(self) -> None:
        # 1) продлеваем трассу последним значением — иначе при паузе
        #    телеметрии линия «застывает» и обрывается на старой точке.
        if self._t0 is not None:
            t = time.monotonic() - self._t0
            self._samples.append((t, self._current))
            cutoff = t - self.WINDOW_S - 0.5
            while len(self._samples) > 2 and self._samples[0][0] < cutoff:
                self._samples.popleft()

        self._rebuild_time_layer()
        self._rebuild_trace()
        self._update_cursor_and_readout()

    # ---- X-grid + подписи (двигаются с временем) --------------------

    def _rebuild_time_layer(self) -> None:
        if self.width <= 4 or self.height <= 4:
            for col, ln in self._x_grid_lines:
                ln.points = [0, 0, 0, 0]
            for lbl in self._x_lbls:
                lbl.text = ""
            return

        px, py, pw, ph = self._plot_rect()
        plot_l, plot_b = px, py
        plot_r = px + pw
        plot_t = py + ph

        t_now  = (time.monotonic() - self._t0) if self._t0 is not None else 0.0
        t_left = t_now - self.WINDOW_S

        def t_to_x(t: float) -> float:
            return plot_l + (t - t_left) / self.WINDOW_S * pw

        # Перебираем доступные слоты пула в порядке: первая мажорная
        # отметка, далее с шагом SEC_STEP_MAJOR.
        sec = math.floor(t_left / self.SEC_STEP_MAJOR) * self.SEC_STEP_MAJOR
        i_slot = 0
        while sec <= t_now + 1e-6 and i_slot < len(self._x_grid_lines):
            x = t_to_x(sec)
            if plot_l - 0.5 <= x <= plot_r + 0.5:
                _, ln = self._x_grid_lines[i_slot]
                ln.points = [x, plot_b, x, plot_t]
                lbl = self._x_lbls[i_slot]
                rel = sec - t_now
                lbl.text = f"{rel:+.0f}s" if abs(rel) > 1e-3 else "0s"
                lbl.pos  = (x - lbl.width / 2, plot_b - 22)
                i_slot += 1
            sec += self.SEC_STEP_MAJOR

        # Выключить неиспользованные слоты.
        for k in range(i_slot, len(self._x_grid_lines)):
            self._x_grid_lines[k][1].points = [0, 0, 0, 0]
            self._x_lbls[k].text = ""

    # ---- трасса -----------------------------------------------------

    def _rebuild_trace(self) -> None:
        if (self._t0 is None or len(self._samples) < 2
                or self.width <= 4 or self.height <= 4):
            for _c, ln in self._trace_lines:
                ln.points = []
            return

        px, py, pw, ph = self._plot_rect()
        plot_l, plot_b = px, py
        plot_r = px + pw

        t_now  = time.monotonic() - self._t0
        t_left = t_now - self.WINDOW_S

        def t_to_x(t: float) -> float:
            return plot_l + (t - t_left) / self.WINDOW_S * pw

        y_min, y_max = self._y_min, self._y_max

        pts: list[float] = []
        for ts, rv in self._samples:
            if ts < t_left - 0.05:
                continue
            x = t_to_x(ts)
            # клипуем по X тоже — линия не должна вылезать за рамку.
            x = max(plot_l, min(plot_r, x))
            rv_clip = max(y_min, min(y_max, rv))
            y = self.v_to_y(rv_clip)
            pts.append(x); pts.append(y)

        for _c, ln in self._trace_lines:
            ln.points = pts

    # ---- курсор + readout ------------------------------------------

    def _update_cursor_and_readout(self) -> None:
        if self.width <= 4 or self.height <= 4:
            return
        px, py, pw, ph = self._plot_rect()
        plot_r = px + pw
        plot_t = py + ph

        if self._has_data:
            cur_y = self.v_to_y(max(self._y_min, min(self._y_max, self._current)))
            r_glow = 11
            r_dot  = 5
            self._cursor_glow.pos  = (plot_r - r_glow, cur_y - r_glow)
            self._cursor_glow.size = (r_glow * 2, r_glow * 2)
            self._cursor_dot.pos   = (plot_r - r_dot, cur_y - r_dot)
            self._cursor_dot.size  = (r_dot * 2, r_dot * 2)
            self._big_readout.text = self._value_fmt.format(self._current)
            self._big_readout.color = hex_to_rgba(COL_DIGITAL)
        else:
            self._cursor_glow.size = (0, 0)
            self._cursor_dot.size  = (0, 0)
            self._big_readout.text = "— — —"
            self._big_readout.color = hex_to_rgba(COL_DIGITAL_DIM)

        # Поставить readout в правом верхнем углу plot rect.
        self._big_readout.pos = (
            plot_r - self._big_readout.width - 14,
            plot_t - self._big_readout.height - 6,
        )
        self._unit_lbl.pos = (
            plot_r - self._unit_lbl.width - 14,
            plot_t - self._big_readout.height - 6 - self._unit_lbl.height,
        )
