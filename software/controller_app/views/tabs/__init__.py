"""Вкладки главного окна. Каждая — самодостаточный QWidget с собственными
сигналами наружу и слотами для обновления от модели."""

from .connect_tab import ConnectTab
from .motor_tab import MotorTab
from .sensors_tab import SensorsTab
from .terminal_tab import TerminalTab

__all__ = ["ConnectTab", "MotorTab", "SensorsTab", "TerminalTab"]
