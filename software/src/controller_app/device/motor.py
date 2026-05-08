"""Команды управления мотором."""
from __future__ import annotations


class Motor:
    """Тонкая обёртка над Device для команд MOTOR_*."""
    def __init__(self, device: object) -> None:
        self._d = device

    def move(self, steps: int, speed: int, accel: int) -> None:
        ...

    def stop(self) -> None:
        ...