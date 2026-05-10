"""Panel — контейнер с тёмным фоном, рамкой и uppercase-заголовком.

Эквивалент `views/panel.py` из PySide6-версии. Используется как обёртка
для логических панелей: `Panel("PORT")` → внутрь любой контент через
`add_widget(...)` (BoxLayout-наследник).
"""

from __future__ import annotations

from typing import Optional

from kivy.graphics import Color, Line, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

from .theme import (
    COL_LABEL,
    PANEL_RADIUS,
    RGBA_BG_IN,
    RGBA_PANEL_EDGE,
)


class Panel(BoxLayout):
    """Вертикальный контейнер. Заголовок (если задан) — uppercase,
    разреженный шрифт, цвет COL_LABEL.

    Padding/spacing подобраны под PySide6-вариант (14/12/14/12, spacing 10).
    """

    def __init__(self, title: str = "", **kwargs) -> None:
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("padding", (14, 12, 14, 12))
        kwargs.setdefault("spacing", 10)
        super().__init__(**kwargs)

        self._radius = PANEL_RADIUS

        # Фон + рамка через canvas.before — родной для Kivy способ.
        with self.canvas.before:
            self._bg_color   = Color(*RGBA_BG_IN)
            self._bg_rect    = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[self._radius],
            )
            self._edge_color = Color(*RGBA_PANEL_EDGE)
            self._edge_line  = Line(
                rounded_rectangle=(*self.pos, *self.size, self._radius),
                width=1.0,
            )

        self.bind(pos=self._update_canvas, size=self._update_canvas)

        if title:
            self._title = Label(
                text=f"[b]{title.upper()}[/b]",
                markup=True,
                color=(0, 0, 0, 0),     # сразу выставится из COL_LABEL ниже
                halign="left",
                valign="middle",
                size_hint_y=None,
                height="20dp",
                font_size="11sp",
            )
            # COL_LABEL → RGBA через rgba_setter; здесь напрямую:
            from .theme import hex_to_rgba
            self._title.color = hex_to_rgba(COL_LABEL)
            self._title.bind(size=self._sync_title_text_size)
            self.add_widget(self._title)

    def _update_canvas(self, *_a) -> None:
        self._bg_rect.pos  = self.pos
        self._bg_rect.size = self.size
        self._edge_line.rounded_rectangle = (*self.pos, *self.size, self._radius)

    def _sync_title_text_size(self, instance: Label, _size) -> None:
        instance.text_size = instance.size
