"""Все CLI-команды прошивки, организованные по подсистемам в 2-колоночную сетку.

Эмитит один сигнал `command_requested(str)` с готовой строкой команды;
вверх по wiring-у она уходит в DeviceController.send_command. Никакой
бизнес-логики здесь нет, только ergonomic group-и кнопок/слайдеров.

Новая подсистема в прошивке = ещё один Panel в сетке. Помощник
`_stream_panel` шаблонизирует «ON/OFF/READ + RATE» под любую из них.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QGridLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QSlider,
    QSpinBox, QWidget,
)

from .panel import Panel
from .theme import (
    COL_DIGITAL, COL_LABEL, industrial_button_qss, slider_qss, spinbox_qss,
)


# ============================================================================
#  Внутренний RateRow — слайдер с дросселированной отправкой
# ============================================================================
class _RateRow(QWidget):
    """Слайдер RATE + value-label. Эмитит rate_changed(int) не чаще 10 Hz —
    при быстром перетягивании UART не захлёстывается лишними строками."""

    rate_changed = Signal(int)

    def __init__(self, lo: int, hi: int, default: int,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        lbl = QLabel("RATE")
        f = QFont(); f.setBold(True); f.setPointSize(9)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        lbl.setFont(f)
        lbl.setStyleSheet(f"color: {COL_LABEL}; background: transparent;")
        row.addWidget(lbl)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(lo, hi)
        self.slider.setValue(default)
        self.slider.setStyleSheet(slider_qss())
        self.slider.setSingleStep(1)
        self.slider.setPageStep(max(1, (hi - lo) // 10))
        row.addWidget(self.slider, 1)

        self.value_lbl = QLabel(f"{default} Hz")
        vlf = QFont("Consolas"); vlf.setBold(True); vlf.setPointSize(11)
        self.value_lbl.setFont(vlf)
        self.value_lbl.setMinimumWidth(70)
        self.value_lbl.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        self.value_lbl.setStyleSheet(
            f"color: {COL_DIGITAL}; background: transparent; letter-spacing: 2px;"
        )
        row.addWidget(self.value_lbl)

        self._pending      = default
        self._last_emitted: Optional[int] = None
        self._throttle = QTimer(self)
        self._throttle.setInterval(100)
        self._throttle.timeout.connect(self._flush)
        self._throttle.start()

        self.slider.valueChanged.connect(self._on_change)

    def _on_change(self, v: int) -> None:
        self.value_lbl.setText(f"{v} Hz")
        self._pending = v

    def _flush(self) -> None:
        if self._pending == self._last_emitted:
            return
        self.rate_changed.emit(self._pending)
        self._last_emitted = self._pending


# ============================================================================
#  Главная панель
# ============================================================================
class CliControlPanel(QWidget):
    command_requested = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum,
        )

        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)

        grid.addWidget(self._outputs_panel(), 0, 0)
        grid.addWidget(self._move_panel(),    0, 1)
        grid.addWidget(self._motor_panel(),   1, 0)
        grid.addWidget(self._probe_panel(),   1, 1)
        grid.addWidget(self._hall_panel(),    2, 0)
        grid.addWidget(self._temp_panel(),    2, 1)
        grid.addWidget(self._system_panel(),  3, 0, 1, 2)

        # Все sub-панели одной ширины:
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

    # ---- секции -------------------------------------------------------

    def _outputs_panel(self) -> Panel:
        p = Panel("OUTPUTS")
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(self._lbl("EN"))
        row.addWidget(self._btn("ON",  "EN ON"))
        row.addWidget(self._btn("OFF", "EN OFF"))
        row.addSpacing(20)
        row.addWidget(self._lbl("DIR"))
        row.addWidget(self._btn("FRW", "DIR FRW"))
        row.addWidget(self._btn("BCK", "DIR BCK"))
        row.addStretch(1)
        p.add_layout(row)
        return p

    def _move_panel(self) -> Panel:
        p = Panel("MOVE")
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(self._lbl("STEPS"))

        self.spn_steps = QSpinBox()
        self.spn_steps.setRange(-1_000_000, 1_000_000)
        self.spn_steps.setValue(1000)
        self.spn_steps.setStyleSheet(spinbox_qss())
        self.spn_steps.setMinimumWidth(110)
        row.addWidget(self.spn_steps, 1)

        row.addWidget(self._lbl("SPEED"))
        self.spn_speed = QSpinBox()
        self.spn_speed.setRange(1, 5000)
        self.spn_speed.setValue(300)
        self.spn_speed.setSuffix(" Hz")
        self.spn_speed.setStyleSheet(spinbox_qss())
        self.spn_speed.setMinimumWidth(120)
        row.addWidget(self.spn_speed, 1)

        btn_go = self._btn("GO")
        btn_go.clicked.connect(self._on_move_go)
        btn_go.setMinimumWidth(70)
        row.addWidget(btn_go)
        p.add_layout(row)
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
        p = Panel("SYSTEM")
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(self._btn("PING", "PING"))
        row.addWidget(self._btn("HELP", "HELP"))
        row.addStretch(1)
        p.add_layout(row)
        return p

    # ---- генератор для ON/OFF/READ + опц. ZERO/DUMP + RATE ------------

    def _stream_panel(
        self, *, title: str, prefix: str,
        lo: int, hi: int, default: int,
        has_zero: bool = False, has_dump: bool = False,
    ) -> Panel:
        p = Panel(title)

        row1 = QHBoxLayout()
        row1.setSpacing(6)
        row1.addWidget(self._btn("ON",   f"{prefix} ON"))
        row1.addWidget(self._btn("OFF",  f"{prefix} OFF"))
        row1.addWidget(self._btn("READ", f"{prefix} READ"))
        if has_dump:
            row1.addWidget(self._btn("DUMP", f"{prefix} DUMP"))
        if has_zero:
            row1.addSpacing(12)
            row1.addWidget(self._btn("ZERO",    f"{prefix} ZERO"))
            row1.addWidget(self._btn("ZEROCLR", f"{prefix} ZEROCLR"))
        row1.addStretch(1)
        p.add_layout(row1)

        # Если диапазон вырожденный (например, TEMP — 1..1) — не показываем слайдер.
        if hi > lo:
            rate_row = _RateRow(lo, hi, default)
            rate_row.rate_changed.connect(
                lambda hz, pf=prefix: self.command_requested.emit(f"{pf} RATE {hz}")
            )
            p.add(rate_row)

        return p

    # ---- builders -----------------------------------------------------

    def _btn(self, label: str, cmd: str = "") -> QPushButton:
        btn = QPushButton(label)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(industrial_button_qss())
        btn.setMinimumHeight(30)
        if cmd:
            btn.clicked.connect(lambda _=False, c=cmd: self.command_requested.emit(c))
        return btn

    def _lbl(self, text: str) -> QLabel:
        lbl = QLabel(text)
        f = QFont(); f.setBold(True); f.setPointSize(9)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        lbl.setFont(f)
        lbl.setStyleSheet(f"color: {COL_LABEL}; background: transparent;")
        return lbl

    def _on_move_go(self) -> None:
        self.command_requested.emit(
            f"MOVE {self.spn_steps.value()} {self.spn_speed.value()}"
        )
