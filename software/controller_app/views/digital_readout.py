"""Цифровые табло в стиле 7-сегментников ЧПУ-стойки.

  - DigitalReadout — большое моноширинное число с цианистым свечением.
                     Используется для POSITION (steps) на вкладке мотора.
  - DirReadout     — индикатор направления (CW / CCW / STOP) с цветами.
  - FreqReadout    — компактные 4 цифры частоты PUL.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel

from .theme import (
    COL_AMBER, COL_BG_INSET, COL_DIGITAL, COL_GRN, COL_PANEL_EDGE,
    COL_TEXT_DIM,
)


class DigitalReadout(QLabel):
    """Большой 7-сегментоподобный экран. Показ значения через `set_value(int)`."""

    def __init__(self, parent: Optional[QLabel] = None) -> None:
        super().__init__(parent)
        self.setText("+0000000")
        self.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        f = QFont("Consolas")
        f.setStyleHint(QFont.StyleHint.Monospace)
        f.setPointSize(48)
        f.setBold(True)
        self.setFont(f)
        self.setStyleSheet(f"""
            QLabel {{
                color: {COL_DIGITAL};
                background: {COL_BG_INSET};
                border: 2px solid {COL_PANEL_EDGE};
                border-radius: 6px;
                padding: 12px 18px;
                letter-spacing: 4px;
            }}
        """)
        self.setMinimumWidth(360)

    def set_value(self, value: int) -> None:
        sign = "+" if value >= 0 else "-"
        self.setText(f"{sign}{abs(value):07d}")


class FreqReadout(QLabel):
    """Компактные цифры частоты PUL (4 знака, Hz)."""

    def __init__(self, parent: Optional[QLabel] = None) -> None:
        super().__init__(parent)
        self.setText("0000")
        self.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        f = QFont("Consolas")
        f.setStyleHint(QFont.StyleHint.Monospace)
        f.setPointSize(22)
        f.setBold(True)
        self.setFont(f)
        self.setStyleSheet(f"""
            QLabel {{
                color: {COL_DIGITAL};
                background: {COL_BG_INSET};
                border: 2px solid {COL_PANEL_EDGE};
                border-radius: 6px;
                padding: 6px 12px;
                letter-spacing: 3px;
            }}
        """)
        self.setMinimumWidth(140)

    def set_value(self, hz: int) -> None:
        self.setText(f"{abs(hz):04d}")


class DirReadout(QLabel):
    """Индикатор направления: CW / CCW / STOP, цветной."""

    _COLORS = {
        "CW":   COL_GRN,
        "CCW":  COL_AMBER,
        "STOP": COL_TEXT_DIM,
    }

    def __init__(self, parent: Optional[QLabel] = None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f = QFont("Consolas")
        f.setStyleHint(QFont.StyleHint.Monospace)
        f.setPointSize(18)
        f.setBold(True)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3)
        self.setFont(f)
        self.setMinimumWidth(110)
        self.set_dir("STOP")

    def set_dir(self, direction: str) -> None:
        direction = direction.upper()
        color = self._COLORS.get(direction, COL_TEXT_DIM)
        self.setText(direction)
        self.setStyleSheet(f"""
            QLabel {{
                color: {color};
                background: {COL_BG_INSET};
                border: 2px solid {COL_PANEL_EDGE};
                border-radius: 6px;
                padding: 6px 12px;
            }}
        """)
