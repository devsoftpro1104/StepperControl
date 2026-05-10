"""Все CLI-команды прошивки, организованные по подсистемам в 2-колоночную сетку.

Эмитит одно событие `on_command_requested(str)` — готовая строка команды,
которую `ConnectTab` пробросит наверх в DeviceController.

Эквивалент `software/controller_app/views/cli_control_panel.py`. Помощник
`_stream_panel` шаблонизирует «ON/OFF/READ + RATE» под любую подсистему.
"""

from __future__ import annotations

from typing import Optional

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label

from .panel import Panel
from .theme import COL_DIGITAL, COL_LABEL, hex_to_rgba
from .widgets import IndustrialButton, IndustrialSlider, IndustrialSpinBox


# ---------------------------------------------------------------------------
#  _RateRow — слайдер RATE с дросселированной отправкой (10 Hz)
# ---------------------------------------------------------------------------

class _RateRow(BoxLayout):
    """RATE-слайдер + value-label. Эмитит `on_rate_changed(int)` не чаще
    10 Hz — иначе быстрое перетягивание захлёстывает UART лишними
    `* RATE …` строками."""

    __events__ = ("on_rate_changed",)

    def __init__(self, lo: int, hi: int, default: int, **kwargs) -> None:
        kwargs.setdefault("orientation", "horizontal")
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", "32dp")
        kwargs.setdefault("spacing", 8)
        super().__init__(**kwargs)

        # «RATE» подпись слева
        cap = Label(
            text="[b]RATE[/b]", markup=True,
            color=hex_to_rgba(COL_LABEL),
            size_hint_x=None, width="60dp",
            halign="left", valign="middle",
            font_size="11sp",
        )
        cap.bind(size=lambda *_: setattr(cap, "text_size", cap.size))
        self.add_widget(cap)

        self.slider = IndustrialSlider(
            min=lo, max=hi, value=default, step=1,
            size_hint_x=1,
        )
        self.add_widget(self.slider)

        self.value_lbl = Label(
            text=f"[b]{default} Hz[/b]", markup=True,
            color=hex_to_rgba(COL_DIGITAL),
            size_hint_x=None, width="80dp",
            halign="right", valign="middle",
            font_name="RobotoMono-Regular", font_size="13sp",
        )
        self.value_lbl.bind(
            size=lambda *_: setattr(self.value_lbl, "text_size", self.value_lbl.size),
        )
        self.add_widget(self.value_lbl)

        self._pending: int = default
        self._last_emitted: Optional[int] = None
        self.slider.bind(value=self._on_change)

        # Дроссель: 10 Hz, как QTimer(interval=100) в PySide6.
        Clock.schedule_interval(lambda _dt: self._flush(), 0.1)

    def _on_change(self, _slider, v: float) -> None:
        v_int = int(round(v))
        self.value_lbl.text = f"[b]{v_int} Hz[/b]"
        self._pending = v_int

    def _flush(self) -> None:
        if self._pending == self._last_emitted:
            return
        self.dispatch("on_rate_changed", self._pending)
        self._last_emitted = self._pending

    def on_rate_changed(self, *_a, **_k) -> None: ...


# ---------------------------------------------------------------------------
#  CliControlPanel — главная сетка команд
# ---------------------------------------------------------------------------

class CliControlPanel(BoxLayout):
    __events__ = ("on_command_requested",)

    # Высоты панелей подобраны под фиксированный layout — Kivy не умеет
    # «по содержимому» в GridLayout без хаков. Если высота не совпадёт с
    # содержимым — увеличить здесь.
    H_BASIC      = 90      # OUTPUTS / SYSTEM (без RATE)
    H_MOVE       = 120     # MOVE — есть SpinBox-ы
    H_STREAM     = 140     # с RATE
    H_STREAM_NR  = 90      # без RATE (TEMP)
    H_PROBE      = 140

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("spacing", 10)
        kwargs.setdefault("size_hint_y", None)
        super().__init__(**kwargs)

        grid = GridLayout(
            cols=2, spacing=10, size_hint_y=None,
        )
        grid.bind(minimum_height=grid.setter("height"))

        # Порядок: как в PySide6.
        grid.add_widget(self._outputs_panel())   # 0,0
        grid.add_widget(self._move_panel())      # 0,1
        grid.add_widget(self._motor_panel())     # 1,0
        grid.add_widget(self._probe_panel())     # 1,1
        grid.add_widget(self._hall_panel())      # 2,0
        grid.add_widget(self._temp_panel())      # 2,1

        self.add_widget(grid)
        self.add_widget(self._system_panel())   # на всю ширину

        # Внешняя высота — сумма дочерних. Плюс заголовок не нужен,
        # сетка сама её посчитает.
        self.bind(minimum_height=self.setter("height"))

    # ---- секции -------------------------------------------------------

    def _outputs_panel(self) -> Panel:
        p = Panel("OUTPUTS", size_hint_y=None, height=self.H_BASIC)

        row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None, height="32dp", spacing=6,
        )
        row.add_widget(self._lbl("EN", width="32dp"))
        row.add_widget(self._btn("ON",  "EN ON",  width="60dp"))
        row.add_widget(self._btn("OFF", "EN OFF", width="60dp"))
        row.add_widget(BoxLayout(size_hint_x=None, width="20dp"))
        row.add_widget(self._lbl("DIR", width="40dp"))
        row.add_widget(self._btn("FRW", "DIR FRW", width="60dp"))
        row.add_widget(self._btn("BCK", "DIR BCK", width="60dp"))
        row.add_widget(BoxLayout())   # стрейч
        p.add_widget(row)
        return p

    def _move_panel(self) -> Panel:
        p = Panel("MOVE", size_hint_y=None, height=self.H_MOVE)

        row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None, height="32dp", spacing=8,
        )
        row.add_widget(self._lbl("STEPS", width="60dp"))
        self.spn_steps = IndustrialSpinBox(
            value=1000, value_min=-1_000_000, value_max=1_000_000, step=100,
            size_hint_x=1,
        )
        row.add_widget(self.spn_steps)

        row.add_widget(self._lbl("SPEED", width="60dp"))
        self.spn_speed_move = IndustrialSpinBox(
            value=300, value_min=1, value_max=5000, step=50, suffix=" Hz",
            size_hint_x=1,
        )
        row.add_widget(self.spn_speed_move)

        btn_go = self._btn("GO", width="80dp")
        btn_go.bind(on_release=lambda _b: self._on_move_go())
        row.add_widget(btn_go)
        p.add_widget(row)
        return p

    def _motor_panel(self) -> Panel:
        return self._stream_panel(
            title="MOTOR STREAM  ·  $M", prefix="MOTOR",
            lo=1, hi=50, default=10,
        )

    def _temp_panel(self) -> Panel:
        return self._stream_panel(
            title="TEMP DS18B20  ·  $T18", prefix="TEMP",
            lo=1, hi=1, default=1,
        )

    def _hall_panel(self) -> Panel:
        return self._stream_panel(
            title="HALL AH49E  ·  $H", prefix="HALL",
            lo=1, hi=100, default=20, has_zero=True,
        )

    def _probe_panel(self) -> Panel:
        return self._stream_panel(
            title="PROBE SELF  ·  $P / $D", prefix="PROBE",
            lo=1, hi=50, default=10, has_dump=True,
        )

    def _system_panel(self) -> Panel:
        p = Panel("SYSTEM", size_hint_y=None, height=self.H_BASIC)
        row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None, height="32dp", spacing=6,
        )
        row.add_widget(self._btn("PING", "PING", width="80dp"))
        row.add_widget(self._btn("HELP", "HELP", width="80dp"))
        row.add_widget(BoxLayout())
        p.add_widget(row)
        return p

    # ---- генератор для ON/OFF/READ + опц. ZERO/DUMP + RATE ------------

    def _stream_panel(
        self, *, title: str, prefix: str,
        lo: int, hi: int, default: int,
        has_zero: bool = False, has_dump: bool = False,
    ) -> Panel:
        height = self.H_STREAM if hi > lo else self.H_STREAM_NR
        p = Panel(title, size_hint_y=None, height=height)

        row1 = BoxLayout(
            orientation="horizontal",
            size_hint_y=None, height="32dp", spacing=6,
        )
        row1.add_widget(self._btn("ON",   f"{prefix} ON",   width="60dp"))
        row1.add_widget(self._btn("OFF",  f"{prefix} OFF",  width="60dp"))
        row1.add_widget(self._btn("READ", f"{prefix} READ", width="64dp"))
        if has_dump:
            row1.add_widget(self._btn("DUMP", f"{prefix} DUMP", width="64dp"))
        if has_zero:
            row1.add_widget(BoxLayout(size_hint_x=None, width="12dp"))
            row1.add_widget(self._btn("ZERO",    f"{prefix} ZERO",    width="64dp"))
            row1.add_widget(self._btn("ZEROCLR", f"{prefix} ZEROCLR", width="84dp"))
        row1.add_widget(BoxLayout())
        p.add_widget(row1)

        # Если диапазон вырожденный (TEMP — 1..1) — не показываем слайдер.
        if hi > lo:
            rate = _RateRow(lo, hi, default)
            rate.bind(on_rate_changed=lambda _r, hz, pf=prefix:
                      self.dispatch("on_command_requested", f"{pf} RATE {hz}"))
            p.add_widget(rate)

        return p

    # ---- builders -----------------------------------------------------

    def _btn(self, label: str, cmd: str = "", width: str = "60dp") -> IndustrialButton:
        btn = IndustrialButton(
            text=label, size_hint_x=None, width=width,
            size_hint_y=None, height="32dp",
        )
        if cmd:
            btn.bind(on_release=lambda _b, c=cmd: self.dispatch("on_command_requested", c))
        return btn

    def _lbl(self, text: str, width: str = "60dp") -> Label:
        lbl = Label(
            text=f"[b]{text}[/b]", markup=True,
            color=hex_to_rgba(COL_LABEL),
            size_hint_x=None, width=width,
            halign="left", valign="middle",
            font_size="11sp",
        )
        lbl.bind(size=lambda *_: setattr(lbl, "text_size", lbl.size))
        return lbl

    def _on_move_go(self) -> None:
        self.dispatch(
            "on_command_requested",
            f"MOVE {self.spn_steps.value} {self.spn_speed_move.value}",
        )

    # ---- default handler ----------------------------------------------

    def on_command_requested(self, *_a, **_k) -> None: ...
