"""Главное окно: собирает панели в layout и пробрасывает их сигналы наружу.

Никакой логики протокола или транспорта здесь нет. Контроллер видит
окно как набор сигналов (`connect_requested`, `command_submitted`, …)
и слотов (`set_connected`, лог/плот через под-панели).

Расширение: новая фича = новая панель в `views/` + добавить в layout +
прокинуть её сигнал наружу + подписать в `__main__.py`.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget

from .command_panel import CommandPanel
from .connection_panel import ConnectionPanel
from .log_panel import LogPanel
from .plot_panel import PlotPanel


class MainWindow(QMainWindow):
    # пробрасываемые наружу сигналы пользовательских действий
    connect_requested    = Signal(str)
    disconnect_requested = Signal()
    dump_requested       = Signal()
    command_submitted    = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("StepperControl host")
        self.resize(1100, 800)

        self.connection = ConnectionPanel()
        self.log        = LogPanel()
        self.command    = CommandPanel()
        self.plot       = PlotPanel()

        central = QWidget(self)
        layout  = QVBoxLayout(central)
        layout.addWidget(self.connection)
        layout.addWidget(self.log,     stretch=2)
        layout.addWidget(self.command)
        layout.addWidget(self.plot,    stretch=3)
        self.setCentralWidget(central)

        # пробрасываем сигналы под-панелей наружу + локальные wiring
        self.connection.connect_requested.connect(self.connect_requested)
        self.connection.disconnect_requested.connect(self.disconnect_requested)
        self.connection.dump_requested.connect(self.dump_requested)
        self.connection.clear_log_requested.connect(self.log.clear)
        self.command.command_submitted.connect(self.command_submitted)

    # ---- слоты модели -------------------------------------------------

    def set_connected(self, connected: bool) -> None:
        self.connection.set_connected(connected)
        self.command.setEnabled(connected)
