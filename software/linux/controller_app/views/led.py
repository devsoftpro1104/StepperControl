"""Светодиодный индикатор: круглый огонёк с радиальным glow.

Эквивалент PySide6-варианта, но через kivy.graphics. Радиальный градиент
имитирован тремя кругами разного радиуса/прозрачности — выглядит почти
как `QRadialGradient`, без честной растровой генерации.
"""

from __future__ import annotations

from kivy.graphics import Color, Ellipse, Line
from kivy.uix.widget import Widget

from .theme import (
    RGBA_GRN, RGBA_LED_OFF, RGBA_PANEL_EDGE, hex_to_rgba,
)


class Led(Widget):
    """Маленький LED 18×18 px. `set_on(True)` → светится цветом `color_on`."""

    def __init__(self, color_on: str = "#1ee05a", **kwargs) -> None:
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("size", (18, 18))
        super().__init__(**kwargs)
        self._on    = False
        self._rgba_on = hex_to_rgba(color_on)
        self._build()

        self.bind(pos=lambda *_: self._build(), size=lambda *_: self._build())

    def _build(self) -> None:
        self.canvas.clear()

        cx = self.x + self.width  / 2
        cy = self.y + self.height / 2
        r  = min(self.width, self.height) / 2 - 2

        with self.canvas:
            if self._on:
                # Имитация радиального градиента: glow halo + основной круг.
                gr, gg, gb, _ = self._rgba_on
                # halo
                Color(gr, gg, gb, 0.30)
                rh = r * 1.6
                Ellipse(pos=(cx - rh, cy - rh), size=(rh * 2, rh * 2))
                # outer ring (более тёмный)
                Color(gr * 0.7, gg * 0.7, gb * 0.7, 1.0)
                Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))
                # inner highlight (светлый кружок выше-левее центра)
                Color(min(gr * 1.4, 1.0), min(gg * 1.4, 1.0), min(gb * 1.4, 1.0), 1.0)
                hi_r = r * 0.65
                Ellipse(
                    pos=(cx - hi_r - r * 0.15, cy - hi_r + r * 0.15),
                    size=(hi_r * 2, hi_r * 2),
                )
            else:
                Color(*RGBA_LED_OFF)
                Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))
                Color(*RGBA_PANEL_EDGE)
                Line(circle=(cx, cy, r), width=1.2)

    def set_on(self, on: bool) -> None:
        if on != self._on:
            self._on = on
            self._build()
