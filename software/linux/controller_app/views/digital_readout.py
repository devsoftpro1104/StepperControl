"""Цифровые табло в стиле 7-сегментников ЧПУ-стойки.

  - DigitalReadout — большое моноширинное число с цианистым свечением.
                     POSITION (steps) на вкладке мотора.
  - DirReadout     — индикатор направления (FRW / BCK / STOP) с цветами.
  - FreqReadout    — компактные 4 цифры частоты PUL.

Эквивалент `views/digital_readout.py` PySide6-версии. Реализовано через
Label + canvas.before (тёмный фон BG_INSET + рамка PANEL_EDGE).
"""

from __future__ import annotations

from kivy.graphics import Color, Line, RoundedRectangle
from kivy.uix.label import Label

from .theme import (
    COL_AMBER, COL_DIGITAL, COL_GRN, COL_TEXT_DIM,
    INPUT_RADIUS, RGBA_BG_INSET, RGBA_PANEL_EDGE, hex_to_rgba,
)


class _BorderedReadout(Label):
    """База: тёмный inset-фон + рамка + центрирование текста."""

    def __init__(self, font_size: str = "32sp", **kwargs) -> None:
        kwargs.setdefault("markup", False)
        kwargs.setdefault("font_name", "RobotoMono-Regular")
        kwargs.setdefault("font_size", font_size)
        kwargs.setdefault("bold", True)
        kwargs.setdefault("halign", "right")
        kwargs.setdefault("valign", "middle")
        kwargs.setdefault("padding", (16, 8))
        super().__init__(**kwargs)

        self._radius = INPUT_RADIUS + 2

        with self.canvas.before:
            self._bg_color   = Color(*RGBA_BG_INSET)
            self._bg_rect    = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[self._radius],
            )
            self._edge_color = Color(*RGBA_PANEL_EDGE)
            self._edge_line  = Line(
                rounded_rectangle=(*self.pos, *self.size, self._radius),
                width=1.4,
            )

        self.bind(pos=self._update_canvas, size=self._sync_text_size)
        self.bind(size=self._update_canvas)

    def _update_canvas(self, *_a) -> None:
        self._bg_rect.pos  = self.pos
        self._bg_rect.size = self.size
        self._edge_line.rounded_rectangle = (
            *self.pos, *self.size, self._radius,
        )

    def _sync_text_size(self, *_a) -> None:
        self.text_size = self.size


class DigitalReadout(_BorderedReadout):
    """Большое 7-сегментоподобное число. `set_value(int)` → форматирует
    как `+0001234` / `-0001234`."""

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("font_size", "32sp")
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", "56dp")
        super().__init__(**kwargs)
        self.color = hex_to_rgba(COL_DIGITAL)
        self.set_value(0)

    def set_value(self, value: int) -> None:
        sign = "+" if value >= 0 else "-"
        self.text = f"{sign}{abs(int(value)):07d}"


class FreqReadout(_BorderedReadout):
    """Компактные цифры частоты PUL (4 знака, Hz)."""

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("font_size", "22sp")
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", "44dp")
        super().__init__(**kwargs)
        self.color = hex_to_rgba(COL_DIGITAL)
        self.set_value(0)

    def set_value(self, hz: int) -> None:
        self.text = f"{abs(int(hz)):04d}"


class DirReadout(_BorderedReadout):
    """Индикатор направления: FRW / BCK / STOP с цветовой индикацией."""

    _COLORS = {
        "FRW":  COL_GRN,
        "BCK":  COL_AMBER,
        "STOP": COL_TEXT_DIM,
    }

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("font_size", "18sp")
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", "40dp")
        kwargs.setdefault("halign", "center")
        super().__init__(**kwargs)
        self.set_dir("STOP")

    def set_dir(self, direction: str) -> None:
        direction = direction.upper()
        self.text  = direction
        self.color = hex_to_rgba(self._COLORS.get(direction, COL_TEXT_DIM))


class EnableReadout(_BorderedReadout):
    """Индикатор ENABLE: ON (DIGITAL) / OFF (TEXT_DIM)."""

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("font_size", "18sp")
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", "40dp")
        kwargs.setdefault("halign", "center")
        super().__init__(**kwargs)
        self.set_enabled(False)

    def set_enabled(self, on: bool) -> None:
        self.text  = "ON" if on else "OFF"
        self.color = hex_to_rgba(COL_DIGITAL if on else COL_TEXT_DIM)
