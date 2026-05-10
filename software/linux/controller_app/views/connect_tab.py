"""Вкладка СОЕДИНЕНИЕ: COM-порт + Refresh + Connect/Disconnect.

Эмитит kivy-события `on_connect_requested(port)` и `on_disconnect_requested()`.
MainApp слушает их через bind() и вызывает контроллер.
"""

from __future__ import annotations

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from serial.tools import list_ports

from .theme import COL_DIGITAL, COL_LABEL


class ConnectTab(BoxLayout):
    # BoxLayout уже EventDispatcher — собственные события регистрируем тут.
    __events__ = ("on_connect_requested", "on_disconnect_requested")

    def __init__(self, **kwargs) -> None:
        super().__init__(orientation="vertical", padding=12, spacing=12, **kwargs)

        self._connected = False
        self._port_map: dict[str, str] = {}    # label -> device

        # ---- header ----
        header = Label(
            text=f"[b][color={COL_DIGITAL}]CONNECTION[/color][/b]",
            markup=True,
            size_hint_y=None, height="32dp",
            halign="left", valign="middle",
        )
        header.bind(size=lambda *_: setattr(header, "text_size", header.size))
        self.add_widget(header)

        # ---- row: combo + refresh + connect ----
        row = BoxLayout(orientation="horizontal", size_hint_y=None, height="48dp", spacing=8)

        self.spinner_port = Spinner(
            text="(нет портов)",
            values=[],
            size_hint_x=1,
        )

        self.btn_refresh = Button(
            text="REFRESH", size_hint_x=None, width="120dp",
        )
        self.btn_refresh.bind(on_release=lambda _b: self.refresh_ports())

        self.btn_connect = Button(
            text="CONNECT", size_hint_x=None, width="180dp",
        )
        self.btn_connect.bind(on_release=lambda _b: self._on_connect_clicked())

        row.add_widget(self.spinner_port)
        row.add_widget(self.btn_refresh)
        row.add_widget(self.btn_connect)
        self.add_widget(row)

        # ---- hint ----
        hint = Label(
            text=f"[color={COL_LABEL}]Выбери COM-порт и нажми CONNECT. "
                 f"После подключения переходи на вкладку TERMINAL.[/color]",
            markup=True,
            size_hint_y=None, height="28dp",
            halign="left", valign="middle",
        )
        hint.bind(size=lambda *_: setattr(hint, "text_size", hint.size))
        self.add_widget(hint)

        # ---- spacer ----
        self.add_widget(BoxLayout())

        self.refresh_ports()

    # ---- ports ----------------------------------------------------------

    def refresh_ports(self) -> None:
        prev_label = self.spinner_port.text
        self._port_map.clear()
        labels: list[str] = []
        for p in list_ports.comports():
            label = f"{p.device}  —  {p.description}" if p.description else p.device
            self._port_map[label] = p.device
            labels.append(label)
        if not labels:
            labels = ["(нет портов)"]
        self.spinner_port.values = labels
        # Сохранить выбранный порт, если он всё ещё в списке.
        if prev_label in labels:
            self.spinner_port.text = prev_label
        else:
            self.spinner_port.text = labels[0]

    # ---- API из контроллера/MainApp ------------------------------------

    def set_connected(self, connected: bool) -> None:
        self._connected = connected
        self.btn_connect.text = "DISCONNECT" if connected else "CONNECT"
        # Во время сессии запретить смену порта.
        self.spinner_port.disabled = connected
        self.btn_refresh.disabled  = connected

    # ---- internals ------------------------------------------------------

    def _on_connect_clicked(self) -> None:
        if self._connected:
            self.dispatch("on_disconnect_requested")
            return
        port = self._port_map.get(self.spinner_port.text)
        if port:
            self.dispatch("on_connect_requested", port)

    # ---- default handlers ----------------------------------------------

    def on_connect_requested(self, *_a, **_k) -> None: ...
    def on_disconnect_requested(self, *_a, **_k) -> None: ...
