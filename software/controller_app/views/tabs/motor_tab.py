"""Вкладка МОТОР: ротор + цифровые показометры + waveform PROBE DUMP.

Layout:
    ┌────────────────────────┬───────────────────────────┐
    │                        │  POSITION   +0001234      │
    │    [ ANIMATED ROTOR ]  │  SPEED      0500 Hz       │
    │                        │  DIR        FRW           │
    │                        │  ENABLE     ON            │
    ├────────────────────────┴───────────────────────────┤
    │  ▼ PROBE DUMP WAVEFORM ─────────────────────────── │
    │  pyqtgraph (one-shot, после команды PROBE DUMP)    │
    └────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ..digital_readout import DigitalReadout, DirReadout, FreqReadout
from ..panel import Panel
from ..plot_panel import PlotPanel
from ..rotor_view import RotorView
from ..theme import COL_DIGITAL, COL_LABEL


class MotorTab(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")

        self.rotor = RotorView()
        self.pos   = DigitalReadout()
        self.dir   = DirReadout()
        self.freq  = FreqReadout()
        self.ena_lbl = QLabel("OFF")          # просто статус ENABLE
        self._style_ena(False)

        self.plot = PlotPanel()

        # ---- левая панель: ротор ----
        rotor_panel = Panel("ROTOR")
        rotor_panel.add(self.rotor, 1)

        # ---- правая панель: digital readouts ----
        readout_panel = Panel("LIVE STATUS")
        readout_panel.add(self._labeled("POSITION  ·  steps", self.pos))
        readout_panel.add(self._labeled("SPEED  ·  Hz",        self.freq))
        readout_panel.add(self._labeled("DIRECTION",            self.dir))
        readout_panel.add(self._labeled("ENABLE",               self.ena_lbl))

        # ---- waveform ----
        plot_panel = Panel("PROBE DUMP WAVEFORM")
        plot_panel.add(self.plot, 1)

        # ---- общий layout: верх (ротор+статус), низ (плот) ----
        top = QHBoxLayout()
        top.setSpacing(12)
        top.addWidget(rotor_panel,   3)
        top.addWidget(readout_panel, 2)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addLayout(top, 3)
        layout.addWidget(plot_panel, 2)

    # ---- слоты ---------------------------------------------------------

    def on_motor_sample(self, sample) -> None:
        # speed_sps — со знаком; знак = направление
        self.pos.set_value(sample.pos)
        self.freq.set_value(abs(sample.speed_sps))

        if sample.speed_sps > 0:
            self.dir.set_dir("FRW")
            self.rotor.set_freq_dir(abs(sample.speed_sps), 1)
        elif sample.speed_sps < 0:
            self.dir.set_dir("BCK")
            self.rotor.set_freq_dir(abs(sample.speed_sps), -1)
        else:
            self.dir.set_dir("STOP")
            self.rotor.set_freq_dir(0, 0)

        # Якорим угол ротора к фактической позиции мотора. Это снимает дрейф,
        # который накопила бы интерполяция по speed между $M (10 Гц по дефолту),
        # и гарантирует «при запуске программы — позиция 0»: первый $M обычно
        # приходит с pos=0, а до этого _angle уже 0 в __init__.
        self.rotor.set_position(sample.pos)

        self._style_ena(bool(sample.en))

    def show_dump(self, samples, sample_hz: int) -> None:
        self.plot.show_dump(samples, sample_hz)

    def reset(self) -> None:
        self.rotor.reset()
        self.pos.set_value(0)
        self.freq.set_value(0)
        self.dir.set_dir("STOP")
        self._style_ena(False)
        self.plot.clear()

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
