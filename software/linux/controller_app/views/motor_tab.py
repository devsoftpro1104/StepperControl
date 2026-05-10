"""Вкладка МОТОР: ротор + цифровые показометры + TARGET-блок.

Layout:
    ┌────────────────────────┬───────────────────────────┐
    │                        │  LIVE STATUS              │
    │                        │   POSITION   +0001234     │
    │    [ ANIMATED ROTOR ]  │   SPEED      0500 Hz      │
    │                        │   DIR        FRW          │
    │                        │   ENABLE     ON           │
    │                        ├───────────────────────────┤
    │                        │  TARGET                   │
    │                        │   [pos] [speed]           │
    │                        │   [GO ]  [STOP]           │
    └────────────────────────┴───────────────────────────┘

GO считает дельту от текущей позиции и шлёт `MOVE <delta> <speed>`.
Через 100 мс дополнительно шлёт `PROBE DUMP` — мотор уже стабильно
крутится, ring-буфер ADC2 захватит настоящие пульсации.
"""

from __future__ import annotations

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

from .digital_readout import (
    DigitalReadout, DirReadout, EnableReadout, FreqReadout,
)
from .panel import Panel
from .rotor_view import RotorView
from .theme import COL_LABEL, hex_to_rgba
from .widgets import IndustrialButton, IndustrialSpinBox


# Метрики раскладки. Считаются один раз, чтобы Panel-ы получили
# фиксированную высоту (BoxLayout с size_hint_y=None у дочерних не
# растягивает их сам).
_CAP_H        = 14    # caption (POSITION · STEPS)
_ROW_GAP      = 4
_PANEL_PAD    = 12 + 12     # верх + низ
_PANEL_TITLE  = 20
_PANEL_INNER  = 8           # spacing внутри Panel между строками


def _row_h(widget_h: int) -> int:
    """Высота `_labeled` строки = caption + spacing + widget."""
    return _CAP_H + _ROW_GAP + widget_h


class MotorTab(BoxLayout):
    __events__ = ("on_command_requested",)

    def __init__(self, **kwargs) -> None:
        super().__init__(orientation="horizontal", padding=12, spacing=12, **kwargs)

        self._cur_pos: int = 0   # последняя пришедшая позиция от $M

        # ============================================================
        #  ЛЕВО: ротор
        # ============================================================
        rotor_panel = Panel("ROTOR", size_hint_x=3)
        self.rotor = RotorView()
        rotor_panel.add_widget(self.rotor)
        self.add_widget(rotor_panel)

        # ============================================================
        #  ПРАВО: LIVE STATUS + TARGET (фиксированные высоты)
        # ============================================================
        right = BoxLayout(orientation="vertical", spacing=10, size_hint_x=2)

        # ---- LIVE STATUS ----
        # 4 строки: POSITION (56dp) + SPEED (44dp) + DIR (40dp) + ENABLE (40dp)
        self.pos_readout  = DigitalReadout()
        self.freq_readout = FreqReadout()
        self.dir_readout  = DirReadout()
        self.ena_readout  = EnableReadout()

        live_h = (
            _PANEL_TITLE + _PANEL_PAD
            + _row_h(56) + _row_h(44) + _row_h(40) + _row_h(40)
            + _PANEL_INNER * 3
        )
        live = Panel(
            "LIVE STATUS", size_hint_y=None, height=live_h, spacing=_PANEL_INNER,
        )
        live.add_widget(self._labeled("POSITION  ·  STEPS", self.pos_readout))
        live.add_widget(self._labeled("SPEED  ·  Hz",       self.freq_readout))
        live.add_widget(self._labeled("DIRECTION",          self.dir_readout))
        live.add_widget(self._labeled("ENABLE",             self.ena_readout))
        right.add_widget(live)

        # ---- TARGET ----
        # 2 строки spinbox (36dp) + ряд кнопок (40dp)
        self.spn_target = IndustrialSpinBox(
            value=100, value_min=-1_000_000, value_max=1_000_000, step=100,
            size_hint_y=None, height="36dp",
        )
        self.spn_speed = IndustrialSpinBox(
            value=300, value_min=1, value_max=5000, step=50, suffix=" Hz",
            size_hint_y=None, height="36dp",
        )

        target_h = (
            _PANEL_TITLE + _PANEL_PAD
            + _row_h(36) + _row_h(36) + 40
            + _PANEL_INNER * 3
        )
        target = Panel(
            "TARGET", size_hint_y=None, height=target_h, spacing=_PANEL_INNER,
        )
        target.add_widget(self._labeled("POSITION  ·  STEPS (abs)", self.spn_target))
        target.add_widget(self._labeled("SPEED  ·  steps/s",        self.spn_speed))

        btn_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None, height="40dp", spacing=8,
        )
        self.btn_go   = IndustrialButton(text="GO",   size_hint_x=1)
        self.btn_stop = IndustrialButton(text="STOP", size_hint_x=1)
        self.btn_go.bind(on_release=lambda _b: self._on_go())
        self.btn_stop.bind(on_release=lambda _b: self._on_stop())
        btn_row.add_widget(self.btn_go)
        btn_row.add_widget(self.btn_stop)
        target.add_widget(btn_row)

        right.add_widget(target)

        # Спейсер растягивает оставшееся вверх — обе панели прилипают к верху.
        right.add_widget(BoxLayout())

        self.add_widget(right)

    # ---- слоты ---------------------------------------------------------

    def on_motor_sample(self, sample) -> None:
        self._cur_pos = int(sample.pos)
        self.pos_readout.set_value(sample.pos)
        self.freq_readout.set_value(sample.speed_sps)

        # speed_sps от $M беззнаковый; знак — отдельным полем direction
        # (0 = FRW, 1 = BCK).
        sign = -1 if sample.direction == 1 else +1
        if sample.speed_sps == 0:
            self.dir_readout.set_dir("STOP")
        elif sign > 0:
            self.dir_readout.set_dir("FRW")
        else:
            self.dir_readout.set_dir("BCK")

        self.rotor.set_state(int(sample.pos), int(sample.speed_sps) * sign)
        self.ena_readout.set_enabled(bool(sample.en))

    def reset(self) -> None:
        self.rotor.reset()
        self.pos_readout.set_value(0)
        self.freq_readout.set_value(0)
        self.dir_readout.set_dir("STOP")
        self.ena_readout.set_enabled(False)
        self._cur_pos = 0

    # ---- target controls ----------------------------------------------

    def _on_go(self) -> None:
        target = int(self.spn_target.value)
        speed  = int(self.spn_speed.value)
        delta  = target - self._cur_pos
        if delta == 0:
            return
        self.dispatch("on_command_requested", f"MOVE {delta} {speed}")
        # Дамп STEP-сигнала через 100 мс — мотор уже стабильно крутится.
        Clock.schedule_once(
            lambda _dt: self.dispatch("on_command_requested", "PROBE DUMP"),
            0.1,
        )

    def _on_stop(self) -> None:
        self.dispatch("on_command_requested", "STOP")

    # ---- helpers -------------------------------------------------------

    def _labeled(self, caption: str, widget) -> BoxLayout:
        """Caption (uppercase, COL_LABEL) сверху + widget снизу. Фиксированная
        высота, чтобы Panel правильно посчитал свой минимум."""
        widget_h = widget.height
        wrap = BoxLayout(
            orientation="vertical",
            spacing=_ROW_GAP,
            size_hint_y=None,
            height=_CAP_H + _ROW_GAP + widget_h,
        )
        cap = Label(
            text=f"[b]{caption.upper()}[/b]",
            markup=True,
            color=hex_to_rgba(COL_LABEL),
            size_hint_y=None, height=_CAP_H,
            halign="left", valign="bottom",
            font_size="9sp",
        )
        cap.bind(size=lambda *_: setattr(cap, "text_size", cap.size))
        wrap.add_widget(cap)
        wrap.add_widget(widget)
        return wrap

    def on_command_requested(self, *_a, **_k) -> None: ...
