"""Вкладка ТЕРМИНАЛ: цветной лог + ввод команды + CLEAR.

Высокочастотные стримы ($M, $T18, $H, $P) сюда не пишутся (в MVP они
вообще не визуализируются — см. README), иначе при 50–100 Hz терминал
перегрузится.

Эмитит kivy-событие `on_command_submitted(cmd)`. Очередь CSV-команд
(как в PySide6-версии) намеренно вынесена за пределы MVP.
"""

from __future__ import annotations

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput

from .log_panel import LogPanel
from .theme import COL_DIGITAL


class TerminalTab(BoxLayout):
    __events__ = ("on_command_submitted",)

    def __init__(self, **kwargs) -> None:
        super().__init__(orientation="vertical", padding=12, spacing=8, **kwargs)
        self._enabled = False

        # ---- header ----
        header = Label(
            text=f"[b][color={COL_DIGITAL}]TERMINAL[/color][/b]",
            markup=True,
            size_hint_y=None, height="32dp",
            halign="left", valign="middle",
        )
        header.bind(size=lambda *_: setattr(header, "text_size", header.size))
        self.add_widget(header)

        # ---- log ----
        self.log = LogPanel(size_hint_y=1)
        self.add_widget(self.log)

        # ---- command row ----
        cmd_row = BoxLayout(orientation="horizontal", size_hint_y=None, height="44dp", spacing=8)

        self.ti_cmd = TextInput(
            multiline=False,
            hint_text="введи команду и нажми Enter (например: PING)",
            size_hint_x=1,
            font_size="14sp",
        )
        self.ti_cmd.bind(on_text_validate=lambda _ti: self._submit())

        self.btn_send = Button(
            text="SEND", size_hint_x=None, width="120dp",
        )
        self.btn_send.bind(on_release=lambda _b: self._submit())

        self.btn_clear = Button(
            text="CLEAR", size_hint_x=None, width="120dp",
        )
        self.btn_clear.bind(on_release=lambda _b: self.log.clear())

        cmd_row.add_widget(self.ti_cmd)
        cmd_row.add_widget(self.btn_send)
        cmd_row.add_widget(self.btn_clear)
        self.add_widget(cmd_row)

        self._set_input_enabled(False)

    # ---- API из MainApp -------------------------------------------------

    def append_log(self, text: str, severity: str = "raw") -> None:
        self.log.append_line(text, severity)

    def set_connected(self, connected: bool) -> None:
        self._set_input_enabled(connected)

    # ---- internals ------------------------------------------------------

    def _set_input_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self.ti_cmd.disabled = not enabled
        self.btn_send.disabled = not enabled

    def _submit(self) -> None:
        if not self._enabled:
            return
        cmd = self.ti_cmd.text.strip()
        if not cmd:
            return
        self.dispatch("on_command_submitted", cmd)
        self.ti_cmd.text = ""

    # ---- default handlers ----------------------------------------------

    def on_command_submitted(self, *_a, **_k) -> None: ...
