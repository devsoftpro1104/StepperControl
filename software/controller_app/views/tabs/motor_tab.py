"""Вкладка МОТОР: ротор + цифровые показометры + блок TARGET.

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
Прошивка отрабатывает ровно столько шагов и тормозит на цели — мотор
остаётся EN ON, драйвер удерживает обмотки под током (holding torque).
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from ..digital_readout import DigitalReadout, DirReadout, FreqReadout
from ..panel import Panel
from ..rotor_view import RotorView
from ..theme import COL_DIGITAL, COL_LABEL, industrial_button_qss, spinbox_qss


class MotorTab(QWidget):
    command_requested = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")

        self.rotor = RotorView()
        self.pos   = DigitalReadout()
        self.dir   = DirReadout()
        self.freq  = FreqReadout()
        self.ena_lbl = QLabel("OFF")
        self._style_ena(False)

        self._cur_pos: int = 0   # последняя пришедшая позиция от $M

        # ---- левая панель: ротор ----
        rotor_panel = Panel("ROTOR")
        rotor_panel.add(self.rotor, 1)

        # ---- правая верх: digital readouts ----
        readout_panel = Panel("LIVE STATUS")
        readout_panel.add(self._labeled("POSITION  ·  steps", self.pos))
        readout_panel.add(self._labeled("SPEED  ·  Hz",        self.freq))
        readout_panel.add(self._labeled("DIRECTION",            self.dir))
        readout_panel.add(self._labeled("ENABLE",               self.ena_lbl))

        # ---- правая низ: TARGET ----
        target_panel = Panel("TARGET")

        self.spn_target = QSpinBox()
        self.spn_target.setRange(-1_000_000, 1_000_000)
        self.spn_target.setValue(100)
        self.spn_target.setStyleSheet(spinbox_qss())
        self.spn_target.setMinimumHeight(30)

        self.spn_speed = QSpinBox()
        self.spn_speed.setRange(1, 5000)
        self.spn_speed.setValue(300)
        self.spn_speed.setSuffix(" Hz")
        self.spn_speed.setStyleSheet(spinbox_qss())
        self.spn_speed.setMinimumHeight(30)

        target_panel.add(self._labeled("POSITION  ·  steps (abs)", self.spn_target))
        target_panel.add(self._labeled("SPEED  ·  steps/s",        self.spn_speed))

        btn_go   = QPushButton("GO")
        btn_stop = QPushButton("STOP")
        for b in (btn_go, btn_stop):
            b.setMinimumHeight(36)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(industrial_button_qss())
        btn_go.clicked.connect(self._on_go)
        btn_stop.clicked.connect(self._on_stop)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addWidget(btn_go,   1)
        btn_row.addWidget(btn_stop, 1)
        target_panel.add_layout(btn_row)

        # ---- общий layout ----
        right = QVBoxLayout()
        right.setSpacing(10)
        right.addWidget(readout_panel, 3)
        right.addWidget(target_panel,  2)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        layout.addWidget(rotor_panel, 3)
        layout.addLayout(right,       2)

    # ---- слоты ---------------------------------------------------------

    def on_motor_sample(self, sample) -> None:
        self._cur_pos = int(sample.pos)
        self.pos.set_value(sample.pos)
        self.freq.set_value(sample.speed_sps)

        # speed_sps от $M беззнаковый; знак — отдельным полем direction
        # (0 = FRW, 1 = BCK).
        sign = -1 if sample.direction == 1 else +1
        if sample.speed_sps == 0:
            self.dir.set_dir("STOP")
        elif sign > 0:
            self.dir.set_dir("FRW")
        else:
            self.dir.set_dir("BCK")

        self.rotor.set_state(int(sample.pos), int(sample.speed_sps) * sign)
        self._style_ena(bool(sample.en))

    def reset(self) -> None:
        self.rotor.reset()
        self.pos.set_value(0)
        self.freq.set_value(0)
        self.dir.set_dir("STOP")
        self._style_ena(False)
        self._cur_pos = 0

    # ---- target controls ----------------------------------------------

    def _on_go(self) -> None:
        target = int(self.spn_target.value())
        speed  = int(self.spn_speed.value())
        delta  = target - self._cur_pos
        if delta == 0:
            return
        self.command_requested.emit(f"MOVE {delta} {speed}")
        # Дамп STEP-сигнала через 100 мс — мотор уже стабильно крутится,
        # ring-буфер ADC2 (~7.8 мс окно) захватит настоящие пульсации.
        QTimer.singleShot(100, lambda: self.command_requested.emit("PROBE DUMP"))

    def _on_stop(self) -> None:
        self.command_requested.emit("STOP")

    # ---- helpers -------------------------------------------------------

    def _labeled(self, caption: str, widget: QWidget) -> QWidget:
        wrap = QWidget()
        wrap.setStyleSheet("background: transparent;")
        col = QVBoxLayout(wrap)
        col.setContentsMargins(0, 0, 0, 6)
        col.setSpacing(2)

        cap = QLabel(caption.upper())
        f = QFont(); f.setBold(True); f.setPointSize(8)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3)
        cap.setFont(f)
        cap.setStyleSheet(f"color: {COL_LABEL}; background: transparent;")
        col.addWidget(cap)
        col.addWidget(widget)
        return wrap

    def _style_ena(self, on: bool) -> None:
        self.ena_lbl.setText("ON" if on else "OFF")
        f = QFont("Consolas"); f.setBold(True); f.setPointSize(18)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3)
        self.ena_lbl.setFont(f)
        self.ena_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        color = COL_DIGITAL if on else "#6f7a82"
        self.ena_lbl.setStyleSheet(f"""
            QLabel {{
                color: {color};
                background: #050708;
                border: 2px solid {('#0f3a4a' if on else '#2a3138')};
                border-radius: 6px;
                padding: 6px 12px;
            }}
        """)
