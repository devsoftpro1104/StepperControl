"""Цветной лог: ScrollView + Label с markup в стиле PySide6 textedit.

Тёмный inset-фон (#050708), рамка COL_PANEL_EDGE, моноширинный шрифт.
"""

from __future__ import annotations

from kivy.graphics import Color, Line, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

from .theme import (
    COL_TEXT, INPUT_RADIUS, RGBA_BG_INSET, RGBA_PANEL_EDGE, SEVERITY_COLOR,
)


def _escape_markup(text: str) -> str:
    return text.replace("&", "&amp;").replace("[", "&bl;").replace("]", "&br;")


class LogPanel(BoxLayout):
    def __init__(self, **kwargs) -> None:
        super().__init__(orientation="vertical", **kwargs)

        # Фон + рамка как у textedit_qss().
        with self.canvas.before:
            self._bg_color   = Color(*RGBA_BG_INSET)
            self._bg_rect    = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[INPUT_RADIUS],
            )
            self._edge_color = Color(*RGBA_PANEL_EDGE)
            self._edge_line  = Line(
                rounded_rectangle=(*self.pos, *self.size, INPUT_RADIUS),
                width=1.0,
            )
        self.bind(pos=self._update_canvas, size=self._update_canvas)

        self._scroll = ScrollView(
            do_scroll_x=False, do_scroll_y=True,
            bar_width=8, scroll_type=["bars", "content"],
        )
        self._label = Label(
            text="",
            markup=True,
            halign="left",
            valign="top",
            size_hint_y=None,
            color=(1, 1, 1, 1),
            font_name="RobotoMono-Regular",
            font_size="13sp",
            padding=(8, 6),
        )
        self._label.bind(
            width=lambda *_: self._update_text_size(),
            texture_size=lambda *_: setattr(
                self._label, "height", self._label.texture_size[1],
            ),
        )

        self._scroll.add_widget(self._label)
        self.add_widget(self._scroll)

    def _update_canvas(self, *_a) -> None:
        self._bg_rect.pos  = self.pos
        self._bg_rect.size = self.size
        self._edge_line.rounded_rectangle = (*self.pos, *self.size, INPUT_RADIUS)

    def _update_text_size(self) -> None:
        self._label.text_size = (self._label.width, None)

    # ---- public API ----------------------------------------------------

    def append_line(self, text: str, severity: str = "raw") -> None:
        color = SEVERITY_COLOR.get(severity, COL_TEXT)
        line = f"[color={color}]{_escape_markup(text)}[/color]"
        self._label.text = (self._label.text + ("\n" if self._label.text else "")) + line
        self._scroll.scroll_y = 0

    def clear(self) -> None:
        self._label.text = ""
