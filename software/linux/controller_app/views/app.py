"""Главное Kivy-приложение: header + TabbedPanel + status bar.

Аналог MainWindow PySide6-версии: header с логотипом и LED-индикатором
LINK справа, индустриальные вкладки, нижний status bar с текстом
ONLINE/OFFLINE/STANDBY.
"""

from __future__ import annotations

from pathlib import Path

from kivy.app import App
from kivy.core.window import Window
from kivy.graphics import Color, Line, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelHeader

from .connect_tab import ConnectTab
from .led import Led
from .motor_tab import MotorTab
from .sensors_tab import SensorsTab
from .terminal_tab import TerminalTab
from .theme import (
    COL_DIGITAL, COL_LABEL, COL_PANEL_EDGE, COL_TEXT_DIM,
    RGBA_BG_IN, RGBA_BG_OUT, RGBA_DIGITAL, RGBA_DIGITAL_DIM,
    RGBA_PANEL_EDGE, RGBA_TAB_BG, RGBA_TEXT_DIM,
    hex_to_rgba,
)


# ---------------------------------------------------------------------------
#  Header (логотип + название + LED LINK)
# ---------------------------------------------------------------------------

class _Header(BoxLayout):
    def __init__(self, **kwargs) -> None:
        super().__init__(
            orientation="horizontal",
            size_hint_y=None, height="56dp",
            padding=("12dp", "6dp"), spacing=12,
            **kwargs,
        )

        # Левый отступ-стрейч
        self.add_widget(BoxLayout())

        # Логотип
        logo_path = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "controller_app" / "resource" / "izto_logo.png"
        )
        if logo_path.exists():
            self.logo = Image(
                source=str(logo_path),
                size_hint=(None, None), size=("44dp", "44dp"),
                allow_stretch=True, keep_ratio=True,
            )
            self.add_widget(self.logo)

        # Название
        title = Label(
            text=f"[b][color={COL_DIGITAL}]STEPPER CONTROL[/color][/b]"
                 f"  [color={COL_LABEL}]·  STM32F4 host[/color]",
            markup=True,
            size_hint_x=None, width="380dp",
            halign="left", valign="middle",
            font_size="17sp",
        )
        title.bind(size=lambda *_: setattr(title, "text_size", title.size))
        self.add_widget(title)

        # Правый отступ-стрейч
        self.add_widget(BoxLayout())

        # LED + LINK
        link_box = BoxLayout(
            orientation="horizontal",
            size_hint_x=None, width="80dp",
            spacing=6,
        )
        self.led = Led(color_on="#1ee05a")
        link_lbl = Label(
            text=f"[b][color={COL_LABEL}]LINK[/color][/b]",
            markup=True,
            size_hint_x=None, width="50dp",
            halign="left", valign="middle",
            font_size="12sp",
        )
        link_lbl.bind(size=lambda *_: setattr(link_lbl, "text_size", link_lbl.size))
        link_box.add_widget(self.led)
        link_box.add_widget(link_lbl)
        self.add_widget(link_box)

    def set_connected(self, connected: bool) -> None:
        self.led.set_on(connected)


# ---------------------------------------------------------------------------
#  Status bar (нижняя полоска как QStatusBar)
# ---------------------------------------------------------------------------

class _StatusBar(BoxLayout):
    def __init__(self, **kwargs) -> None:
        super().__init__(
            orientation="horizontal",
            size_hint_y=None, height="26dp",
            padding=("10dp", 0, "10dp", 0),
            **kwargs,
        )

        with self.canvas.before:
            self._bg_color   = Color(*RGBA_BG_IN)
            self._bg_rect    = Rectangle(pos=self.pos, size=self.size)
            self._edge_color = Color(*RGBA_PANEL_EDGE)
            # верхняя граница
            self._edge_line  = Line(points=[0, 0, 0, 0], width=1.0)
        self.bind(pos=self._update_canvas, size=self._update_canvas)

        self._lbl = Label(
            text=f"[color={COL_TEXT_DIM}]⏻  STANDBY  ·  не подключено[/color]",
            markup=True,
            halign="left", valign="middle",
            font_size="12sp",
        )
        self._lbl.bind(size=lambda *_: setattr(self._lbl, "text_size", self._lbl.size))
        self.add_widget(self._lbl)

    def _update_canvas(self, *_a) -> None:
        self._bg_rect.pos  = self.pos
        self._bg_rect.size = self.size
        self._edge_line.points = [
            self.x, self.y + self.height,
            self.x + self.width, self.y + self.height,
        ]

    def set_text(self, text: str) -> None:
        self._lbl.text = f"[color={COL_TEXT_DIM}]{text}[/color]"


# ---------------------------------------------------------------------------
#  Кастомизированный TabbedPanelHeader (под индустриальный стиль)
# ---------------------------------------------------------------------------

class _IndustrialTabHeader(TabbedPanelHeader):
    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down",   "")
        kwargs.setdefault("background_color",  (0, 0, 0, 0))
        kwargs.setdefault("color",  hex_to_rgba(COL_TEXT_DIM))
        kwargs.setdefault("bold",   True)
        kwargs.setdefault("font_size", "13sp")
        super().__init__(**kwargs)

        with self.canvas.before:
            self._bg_color   = Color(*RGBA_TAB_BG)
            self._bg_rect    = Rectangle(pos=self.pos, size=self.size)
            self._edge_color = Color(*RGBA_PANEL_EDGE)
            self._edge_line  = Line(rectangle=(*self.pos, *self.size), width=1.0)

        self.bind(pos=self._update_canvas, size=self._update_canvas,
                  state=self._update_state)

    def _update_canvas(self, *_a) -> None:
        self._bg_rect.pos  = self.pos
        self._bg_rect.size = self.size
        self._edge_line.rectangle = (*self.pos, *self.size)

    def _update_state(self, *_a) -> None:
        if self.state == "down":          # selected
            self._bg_color.rgba   = RGBA_DIGITAL_DIM
            self._edge_color.rgba = RGBA_DIGITAL
            self.color            = RGBA_DIGITAL
        else:
            self._bg_color.rgba   = RGBA_TAB_BG
            self._edge_color.rgba = RGBA_PANEL_EDGE
            self.color            = hex_to_rgba(COL_TEXT_DIM)


# ---------------------------------------------------------------------------
#  MainView
# ---------------------------------------------------------------------------

class MainView(BoxLayout):
    def __init__(self, **kwargs) -> None:
        super().__init__(orientation="vertical", **kwargs)

        # глобальный фон
        with self.canvas.before:
            self._bg_color = Color(*RGBA_BG_OUT)
            self._bg_rect  = Rectangle(pos=self.pos, size=self.size)
        self.bind(
            pos=lambda *_: setattr(self._bg_rect, "pos", self.pos),
            size=lambda *_: setattr(self._bg_rect, "size", self.size),
        )

        self.header = _Header()
        self.add_widget(self.header)

        # ---- tabs (без default-табы) ----
        self.tabs = TabbedPanel(
            do_default_tab=False,
            tab_width=180, tab_height=42,
            background_color=(0, 0, 0, 0),    # прозрачно — фон под нами
            background_image="",
            border=(0, 0, 0, 0),
        )
        # Унести bottom-bar's content_color (полоса под заголовками)
        self.tabs.background_color = RGBA_BG_OUT

        self.connect_tab  = ConnectTab()
        self.motor_tab    = MotorTab()
        self.sensors_tab  = SensorsTab()
        self.terminal_tab = TerminalTab()

        self._ti_connect = _IndustrialTabHeader(text="CONNECTION", content=self.connect_tab)
        self._ti_motor    = _IndustrialTabHeader(text="MOTOR",     content=self.motor_tab)
        self._ti_sensors  = _IndustrialTabHeader(text="SENSORS",   content=self.sensors_tab)
        self._ti_terminal = _IndustrialTabHeader(text="TERMINAL",  content=self.terminal_tab)
        self.tabs.add_widget(self._ti_connect)
        self.tabs.add_widget(self._ti_motor)
        self.tabs.add_widget(self._ti_sensors)
        self.tabs.add_widget(self._ti_terminal)
        self.tabs.default_tab = self._ti_connect
        self.tabs.switch_to(self._ti_connect)

        self.add_widget(self.tabs)

        # ---- status bar ----
        self.statusbar = _StatusBar()
        self.add_widget(self.statusbar)

    # ---- слоты модели --------------------------------------------------

    def set_connected(self, connected: bool, port: str = "") -> None:
        self.header.set_connected(connected)
        self.connect_tab.set_connected(connected)
        self.terminal_tab.set_connected(connected)

        if connected:
            self.statusbar.set_text(f"●  ONLINE  ·  {port}")
        else:
            self.statusbar.set_text("⏻  STANDBY  ·  не подключено")
            self.tabs.switch_to(self._ti_connect)
            # Очистить живые виджеты — иначе старые данные будут висеть
            # после ре-коннекта.
            self.motor_tab.reset()
            self.sensors_tab.reset()

    def append_log(self, text: str, severity: str) -> None:
        self.terminal_tab.append_log(text, severity)


# ---------------------------------------------------------------------------
#  App
# ---------------------------------------------------------------------------

class StepperControlApp(App):
    """Kivy App-обёртка. Wiring M/V/C — в `on_start`."""

    title = "STEPPER CONTROL  ·  STM32F4 host"

    def __init__(self, model, controller, **kwargs) -> None:
        super().__init__(**kwargs)
        self._model      = model
        self._controller = controller
        self.main_view: MainView | None = None

    def build(self) -> MainView:
        # глобальный фон окна — иначе вокруг нашего MainView Kivy показывает
        # дефолтный серый цвет.
        Window.clearcolor = RGBA_BG_OUT
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
        # Подтверждения для CSV-очереди в TerminalTab.
        model.bind(on_ok_received=lambda _m, payload: view.terminal_tab.on_ok(payload))
        model.bind(on_err_received=lambda _m, payload: view.terminal_tab.on_err(payload))
        model.bind(on_event_received=lambda _m, tag, args: view.terminal_tab.on_event(tag, args))
        # $M-стрим → Motor tab.
        model.bind(on_motor_sample_received=lambda _m, s: view.motor_tab.on_motor_sample(s))
        # $T18 / $H / PROBE DUMP → Sensors tab.
        model.bind(on_temp_sample_received=lambda _m, s: view.sensors_tab.on_temp_sample(s))
        model.bind(on_hall_sample_received=lambda _m, s: view.sensors_tab.on_hall_sample(s))
        model.bind(on_dump_completed=lambda _m, snap: view.sensors_tab.show_dump(snap))

        # ---- view -> controller ----
        view.connect_tab.bind(on_connect_requested=lambda _t, port: ctrl.connect_to(port))
        view.connect_tab.bind(on_disconnect_requested=lambda _t: ctrl.disconnect())
        view.connect_tab.bind(on_command_requested=lambda _t, cmd: ctrl.send_command(cmd))
        view.motor_tab.bind(on_command_requested=lambda _t, cmd: ctrl.send_command(cmd))
        view.terminal_tab.bind(on_command_submitted=lambda _t, cmd: ctrl.send_command(cmd))

    def on_stop(self) -> None:
        self._controller.shutdown()
