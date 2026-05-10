"""Главное Kivy-приложение: header + TabbedPanel(CONNECTION, TERMINAL).

Аналог MainWindow из PySide6-версии. MVP включает только две вкладки —
MOTOR / SENSORS будут добавлены позже отдельным этапом (см. linux/README.md).

Wiring DeviceModel ↔ View ↔ DeviceController живёт в `__main__.py`, как
и в PySide6-варианте.
"""

from __future__ import annotations

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem

from .connect_tab import ConnectTab
from .terminal_tab import TerminalTab
from .theme import COL_DIGITAL, COL_GRN, COL_LABEL, COL_RED


class _Header(BoxLayout):
    def __init__(self, **kwargs) -> None:
        super().__init__(
            orientation="horizontal",
            size_hint_y=None, height="48dp",
            padding=("12dp", "6dp"), spacing=12,
            **kwargs,
        )

        title = Label(
            text=f"[b][color={COL_DIGITAL}]STEPPER CONTROL[/color][/b]"
                 f"  [color={COL_LABEL}]· STM32F4 host (Kivy)[/color]",
            markup=True,
            halign="left", valign="middle",
        )
        title.bind(size=lambda *_: setattr(title, "text_size", title.size))

        self.lbl_link = Label(
            text=f"[b][color={COL_RED}]○ OFFLINE[/color][/b]",
            markup=True,
            size_hint_x=None, width="200dp",
            halign="right", valign="middle",
        )
        self.lbl_link.bind(size=lambda *_: setattr(self.lbl_link, "text_size", self.lbl_link.size))

        self.add_widget(title)
        self.add_widget(self.lbl_link)

    def set_connected(self, connected: bool, port: str = "") -> None:
        if connected:
            self.lbl_link.text = f"[b][color={COL_GRN}]● ONLINE  ·  {port}[/color][/b]"
        else:
            self.lbl_link.text = f"[b][color={COL_RED}]○ OFFLINE[/color][/b]"


class MainView(BoxLayout):
    def __init__(self, **kwargs) -> None:
        super().__init__(orientation="vertical", **kwargs)

        self.header = _Header()
        self.add_widget(self.header)

        self.connect_tab  = ConnectTab()
        self.terminal_tab = TerminalTab()

        self.tabs = TabbedPanel(do_default_tab=False, tab_width=160)

        ti_connect = TabbedPanelItem(text="CONNECTION")
        ti_connect.add_widget(self.connect_tab)
        self.tabs.add_widget(ti_connect)

        ti_terminal = TabbedPanelItem(text="TERMINAL")
        ti_terminal.add_widget(self.terminal_tab)
        self.tabs.add_widget(ti_terminal)
        self._ti_connect = ti_connect

        self.add_widget(self.tabs)

    # ---- слоты модели (зовутся из __main__.py через bind на DeviceModel)

    def set_connected(self, connected: bool, port: str = "") -> None:
        self.header.set_connected(connected, port)
        self.connect_tab.set_connected(connected)
        self.terminal_tab.set_connected(connected)
        # Если только что отключились — вернуться на CONNECTION.
        if not connected:
            self.tabs.switch_to(self._ti_connect)

    def append_log(self, text: str, severity: str) -> None:
        self.terminal_tab.append_log(text, severity)


class StepperControlApp(App):
    """Kivy App-обёртка.

    Принимает model и controller — wiring между ними делается в `on_start`,
    когда корневой виджет уже построен. Делать это в `__main__.py` через
    второй вызов `build()` нельзя: `App.run()` зовёт `build()` сам.
    """

    title = "STEPPER CONTROL  ·  STM32F4 host"

    def __init__(self, model, controller, **kwargs) -> None:
        super().__init__(**kwargs)
        self._model      = model
        self._controller = controller
        self.main_view: MainView | None = None

    def build(self) -> MainView:
        self.main_view = MainView()
        return self.main_view

    def on_start(self) -> None:
        view  = self.main_view
        model = self._model
        ctrl  = self._controller
        assert view is not None

        # ---- model -> view ----
        model.bind(on_connection_changed=lambda _m, c, p: view.set_connected(c, p))
        model.bind(on_log_appended=lambda _m, t, s: view.append_log(t, s))

        # ---- view -> controller ----
        view.connect_tab.bind(on_connect_requested=lambda _t, port: ctrl.connect_to(port))
        view.connect_tab.bind(on_disconnect_requested=lambda _t: ctrl.disconnect())
        view.terminal_tab.bind(on_command_submitted=lambda _t, cmd: ctrl.send_command(cmd))

    def on_stop(self) -> None:
        self._controller.shutdown()
