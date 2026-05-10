"""Вкладка СОЕДИНЕНИЕ: подключение по COM + панель CLI-команд.

  - CONNECTION  — combo COM + Refresh + Connect/Disconnect
  - CLI COMMANDS — все команды прошивки, разложенные по подсистемам

CliControlPanel активна только когда есть подключение — иначе кнопки
отправят команды в никуда.
"""

from __future__ import annotations

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from serial.tools import list_ports

from .cli_control_panel import CliControlPanel
from .panel import Panel
from .widgets import IndustrialButton, IndustrialSpinner


class ConnectTab(BoxLayout):
    __events__ = (
        "on_connect_requested",
        "on_disconnect_requested",
        "on_command_requested",
    )

    def __init__(self, **kwargs) -> None:
        super().__init__(orientation="vertical", padding=12, spacing=10, **kwargs)
        self._connected = False
        self._port_map: dict[str, str] = {}

        scroll = ScrollView(
            do_scroll_x=False, do_scroll_y=True,
            bar_width=8, scroll_type=["bars", "content"],
        )
        inner = BoxLayout(
            orientation="vertical",
            size_hint_y=None, spacing=10,
        )
        inner.bind(minimum_height=inner.setter("height"))

        # ---- CONNECTION panel ----
        port_panel = Panel("CONNECTION", size_hint_y=None, height="84dp")

        row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None, height="40dp",
            spacing=8,
        )

        self.spinner_port = IndustrialSpinner(
            text="(нет портов)", values=[], size_hint_x=1,
        )

        self.btn_refresh = IndustrialButton(
            text="REFRESH", size_hint_x=None, width="120dp",
        )
        self.btn_refresh.bind(on_release=lambda _b: self.refresh_ports())

        self.btn_connect = IndustrialButton(
            text="CONNECT", size_hint_x=None, width="180dp",
        )
        self.btn_connect.bind(on_release=lambda _b: self._on_connect_clicked())

        row.add_widget(self.spinner_port)
        row.add_widget(self.btn_refresh)
        row.add_widget(self.btn_connect)
        port_panel.add_widget(row)

        inner.add_widget(port_panel)

        # ---- CLI COMMANDS panel ----
        cli_panel = Panel("CLI COMMANDS", size_hint_y=None)
        self.cli = CliControlPanel()
        self.cli.bind(on_command_requested=self._on_cli_command)
        cli_panel.add_widget(self.cli)
        # высота cli_panel = заголовок + padding + cli.height
        self.cli.bind(
            height=lambda _w, h: setattr(cli_panel, "height", h + 20 + 24),
        )

        inner.add_widget(cli_panel)
        inner.add_widget(BoxLayout(size_hint_y=None, height="6dp"))

        scroll.add_widget(inner)
        self.add_widget(scroll)

        self.refresh_ports()
        self._set_cli_enabled(False)

    # ---- ports ----------------------------------------------------------

    def refresh_ports(self) -> None:
        prev = self.spinner_port.text
        self._port_map.clear()
        labels: list[str] = []
        for p in list_ports.comports():
            label = f"{p.device}  —  {p.description}" if p.description else p.device
            self._port_map[label] = p.device
            labels.append(label)
        if not labels:
            labels = ["(нет портов)"]
        self.spinner_port.values = labels
        if prev in labels:
            self.spinner_port.text = prev
        else:
            self.spinner_port.text = labels[0]

    # ---- API из MainApp ------------------------------------------------

    def set_connected(self, connected: bool) -> None:
        self._connected = connected
        self.btn_connect.text = "DISCONNECT" if connected else "CONNECT"
        self.spinner_port.disabled = connected
        self.btn_refresh.disabled  = connected
        self._set_cli_enabled(connected)

    # ---- internals -----------------------------------------------------

    def _set_cli_enabled(self, enabled: bool) -> None:
        # Пробежать по всем кнопкам CliControlPanel и выставить disabled.
        # Slider-ы и SpinBox-ы просто перестанут эмитить команды (а
        # эмитят они через bind в строке выше — отключение кнопок этого
        # достаточно для безопасности).
        from kivy.uix.widget import Widget

        def walk(w: Widget):
            for child in w.children:
                if hasattr(child, "disabled"):
                    child.disabled = not enabled
                walk(child)
        walk(self.cli)

    def _on_connect_clicked(self) -> None:
        if self._connected:
            self.dispatch("on_disconnect_requested")
            return
        port = self._port_map.get(self.spinner_port.text)
        if port:
            self.dispatch("on_connect_requested", port)

    def _on_cli_command(self, _panel, cmd: str) -> None:
        self.dispatch("on_command_requested", cmd)

    def on_connect_requested(self, *_a, **_k) -> None: ...
    def on_disconnect_requested(self, *_a, **_k) -> None: ...
    def on_command_requested(self, *_a, **_k) -> None: ...
