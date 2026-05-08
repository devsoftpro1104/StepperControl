"""Главное окно."""
from __future__ import annotations

from PyQt6.QtWidgets import QMainWindow


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Stepper Controller")
        self.resize(1100, 700)