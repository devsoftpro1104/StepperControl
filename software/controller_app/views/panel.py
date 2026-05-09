"""Panel — контейнер с тёмным фоном, рамкой и uppercase-заголовком.

Используется как обёртка для логических панелей: `Panel("PORT")` →
добавил внутрь любой контент через `.add(widget)` или `.add_layout(lay)`.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QLayout, QVBoxLayout, QWidget

from .theme import COL_BG_IN, COL_LABEL, COL_PANEL_EDGE


class Panel(QWidget):
    def __init__(self, title: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("panel")
        self.setStyleSheet(f"""
            QWidget#panel {{
                background: {COL_BG_IN};
                border: 1px solid {COL_PANEL_EDGE};
                border-radius: 8px;
            }}
        """)

        self._inner = QVBoxLayout(self)
        self._inner.setContentsMargins(14, 12, 14, 12)
        self._inner.setSpacing(10)

        if title:
            lbl = QLabel(title.upper())
            f = QFont()
            f.setBold(True)
            f.setPointSize(9)
            f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.5)
            lbl.setFont(f)
            lbl.setStyleSheet(
                f"color: {COL_LABEL}; background: transparent; border: 0;"
            )
            self._inner.addWidget(lbl)

    def add(self, w: QWidget, stretch: int = 0) -> None:
        self._inner.addWidget(w, stretch)

    def add_layout(self, lay: QLayout) -> None:
        self._inner.addLayout(lay)
