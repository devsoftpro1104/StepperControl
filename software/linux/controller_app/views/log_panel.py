"""Цветной лог: ScrollView + Label с markup.

Для MVP-объёма строк (десятки-сотни) Label с разметкой достаточно. Если
лог пухнет (больше нескольких тысяч строк) — заменить на RecycleView,
интерфейс append_line/clear оставить таким же.
"""

from __future__ import annotations

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

from .theme import COL_TEXT, SEVERITY_COLOR


def _escape_markup(text: str) -> str:
    # Без экранирования любые '[' в тексте сломают разметку Label.
    return text.replace("&", "&amp;").replace("[", "&bl;").replace("]", "&br;")


class LogPanel(BoxLayout):
    def __init__(self, **kwargs) -> None:
        super().__init__(orientation="vertical", **kwargs)

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
        # text_size.width привязываем к ширине ScrollView, чтобы перенос
        # строк работал; height растёт от texture_size.
        self._label.bind(
            width=lambda *_: self._update_text_size(),
            texture_size=lambda *_: setattr(self._label, "height", self._label.texture_size[1]),
        )

        self._scroll.add_widget(self._label)
        self.add_widget(self._scroll)

    def _update_text_size(self) -> None:
        self._label.text_size = (self._label.width, None)

    # ---- public API ----------------------------------------------------

    def append_line(self, text: str, severity: str = "raw") -> None:
        color = SEVERITY_COLOR.get(severity, COL_TEXT)
        line = f"[color={color}]{_escape_markup(text)}[/color]"
        self._label.text = (self._label.text + ("\n" if self._label.text else "")) + line
        # Прокрутить вниз; ScrollView пересчитывает после раскладки кадра.
        self._scroll.scroll_y = 0

    def clear(self) -> None:
        self._label.text = ""
