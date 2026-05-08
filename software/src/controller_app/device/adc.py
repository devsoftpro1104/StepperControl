"""Чтение ADC (ADS1115 + встроенный)."""
from __future__ import annotations


class Adc:
    def __init__(self, device: object) -> None:
        self._d = device

    def read_current_ma(self) -> float:
        ...