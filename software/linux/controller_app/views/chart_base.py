"""Базовый класс для осциллографов: фон, рамка, Y-сетка, Y-подписи,
вертикальный axis label и горизонтальный TIME label.

ScopeChart и DumpChart наследуются от `_BaseChart` и добавляют свою
специфику: rolling-буфер с экстраполяцией / one-shot-сэмплы и
измерение частоты.

Все статичные элементы (рамка, сетка, подписи Y, axis label, TIME label)
строятся ОДИН РАЗ в `_rebuild_static` при resize. Это критично для
производительности: PySide6 рисует всё в одном paintEvent через QPainter,
а в Kivy за рисование платит CPU+GPU при каждом обновлении canvas.
"""

from __future__ import annotations

from typing import Iterable, Optional

from kivy.graphics import (
    Color, Line, Rectangle,
)
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from .theme import (
    COL_LABEL, COL_TEXT_DIM,
    RGBA_BG_INSET, RGBA_DIGITAL, RGBA_PANEL_EDGE,
    hex_to_rgba,
)


class _BaseChart(Widget):
    # Поля графика: левый — место для Y-подписей, нижний — для X-меток.
    M_LEFT, M_RIGHT, M_TOP, M_BOTTOM = 70, 28, 40, 36

    def __init__(
        self,
        *,
        y_min: float, y_max: float,
        y_step_major: float, y_step_minor: float,
        axis_label: str = "",
        tick_fmt: str = "{:+.0f}",
        zero_line: bool = False,
        time_label: str = "TIME",
        **kwargs,
    ) -> None:
        kwargs.setdefault("size_hint", (1, 1))
        super().__init__(**kwargs)

        self._y_min      = float(y_min)
        self._y_max      = float(y_max)
        self._step_major = float(y_step_major)
        self._step_minor = float(y_step_minor)
        self._axis_label = axis_label
        self._tick_fmt   = tick_fmt
        self._zero_line  = zero_line and y_min <= 0 <= y_max
        self._time_label = time_label

        # Лейблы Y-меток создаются в _rebuild_static (по числу делений).
        self._y_value_lbls: list[Label] = []
        # Лейбл оси (вертикальный) и TIME (горизонтальный).
        # Для axis_label — берём 1-3 символа и пишем по вертикали (\n).
        self._axis_lbl = Label(
            text=self._wrap_axis_label(axis_label),
            color=hex_to_rgba(COL_LABEL),
            bold=True, font_size="10sp",
            halign="center", valign="middle",
            size_hint=(None, None), size=(40, 100),
        )
        self._axis_lbl.bind(
            size=lambda *_: setattr(self._axis_lbl, "text_size", self._axis_lbl.size),
        )
        self.add_widget(self._axis_lbl)

        self._time_lbl = Label(
            text=time_label,
            color=hex_to_rgba(COL_LABEL),
            bold=True, font_size="9sp",
            halign="center", valign="middle",
            size_hint=(None, None),
        )
        self._time_lbl.bind(
            size=lambda *_: setattr(self._time_lbl, "text_size", self._time_lbl.size),
        )
        self.add_widget(self._time_lbl)

        self.bind(pos=self._rebuild_static, size=self._rebuild_static)

    @staticmethod
    def _wrap_axis_label(text: str) -> str:
        """Превратить '°C' в '°\nC' — компромисс вместо повёрнутого Label."""
        return "\n".join(text)

    # ---- доступ к plot-rect (low-left x, y, width, height) ----------

    def _plot_rect(self) -> tuple[float, float, float, float]:
        x = self.x + self.M_LEFT
        y = self.y + self.M_BOTTOM
        w = max(50.0, self.width  - self.M_LEFT - self.M_RIGHT)
        h = max(50.0, self.height - self.M_TOP  - self.M_BOTTOM)
        return x, y, w, h

    def v_to_y(self, v: float) -> float:
        _x, py, _w, ph = self._plot_rect()
        rng = self._y_max - self._y_min if self._y_max > self._y_min else 1.0
        return py + (v - self._y_min) / rng * ph

    def _iter_grid(self, step: float) -> Iterable[float]:
        if step <= 0:
            return
        i = 0
        while True:
            v = self._y_min + i * step
            if v > self._y_max + 1e-6:
                return
            yield v
            i += 1

    # ---- статичный layer (canvas.before) ----------------------------

    def _rebuild_static(self, *_a) -> None:
        # Очищаем накопленное.
        self.canvas.before.clear()
        for lbl in self._y_value_lbls:
            self.remove_widget(lbl)
        self._y_value_lbls.clear()

        if self.width <= 4 or self.height <= 4:
            return

        px, py, pw, ph = self._plot_rect()
        plot_l, plot_b = px, py
        plot_r = px + pw
        plot_t = py + ph

        with self.canvas.before:
            # ---- общий чёрный фон по всему widget ----
            Color(*RGBA_BG_INSET)
            Rectangle(pos=self.pos, size=self.size)

            # ---- коробка осциллографа (плоская заливка #03080d) ----
            Color(0.011, 0.031, 0.05, 1.0)
            Rectangle(pos=(plot_l, plot_b), size=(pw, ph))
            Color(*RGBA_PANEL_EDGE)
            Line(rectangle=(plot_l, plot_b, pw, ph), width=1.0)

            # ---- Y-сетка ----
            r, g, b, _ = RGBA_DIGITAL
            majors_set = set()
            majors_v = list(self._iter_grid(self._step_major))
            for v in majors_v:
                majors_set.add(round(v / self._step_major)
                               if self._step_major > 0 else None)

            # Минорная сетка (пунктирная)
            for v in self._iter_grid(self._step_minor):
                idx_major = (round(v / self._step_major)
                             if self._step_major > 0 else None)
                if idx_major in majors_set and abs(
                    v - idx_major * self._step_major
                ) < 1e-6:
                    continue
                yy = self.v_to_y(v)
                Color(r, g, b, 0.09)
                Line(
                    points=[plot_l, yy, plot_r, yy],
                    width=1.0,
                    dash_offset=3, dash_length=2,
                )

            # Major сетка (сплошная)
            Color(r, g, b, 0.22)
            for v in majors_v:
                yy = self.v_to_y(v)
                Line(points=[plot_l, yy, plot_r, yy], width=1.0)

            if self._zero_line:
                Color(*RGBA_DIGITAL)
                yy = self.v_to_y(0.0)
                Line(points=[plot_l, yy, plot_r, yy], width=1.4)

        # ---- Y подписи (Label-ы как child widgets) ----
        for v in majors_v:
            yy = self.v_to_y(v)
            lbl = Label(
                text=self._tick_fmt.format(v),
                color=hex_to_rgba(COL_TEXT_DIM),
                bold=True, font_size="9sp",
                font_name="RobotoMono-Regular",
                halign="right", valign="middle",
                size_hint=(None, None),
                size=(self.M_LEFT - 8, 18),
            )
            lbl.bind(
                size=lambda i, _s: setattr(i, "text_size", i.size),
            )
            lbl.pos = (self.x, yy - 9)
            self.add_widget(lbl)
            self._y_value_lbls.append(lbl)

        # ---- axis label (слева, по центру по вертикали) ----
        ax_h = min(120, ph)
        self._axis_lbl.size = (40, ax_h)
        self._axis_lbl.pos  = (self.x, py + (ph - ax_h) / 2)

        # ---- TIME label под графиком ----
        self._time_lbl.size = (pw, 16)
        self._time_lbl.pos  = (plot_l, self.y + 4)
