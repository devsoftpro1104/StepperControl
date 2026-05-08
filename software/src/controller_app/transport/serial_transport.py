"""Транспорт через COM-порт (pyserial)."""
from __future__ import annotations

import serial

from .base import Transport


class SerialTransport(Transport):
    def __init__(self, port: str, baudrate: int = 921_600) -> None:
        self._port = port
        self._baud = baudrate
        self._ser: serial.Serial | None = None

    def open(self) -> None:
        self._ser = serial.Serial(self._port, self._baud, timeout=0.2)

    def close(self) -> None:
        if self._ser:
            self._ser.close()
            self._ser = None

    def write(self, data: bytes) -> int:
        assert self._ser is not None
        return self._ser.write(data)

    def read(self, n: int, timeout_ms: int) -> bytes:
        assert self._ser is not None
        self._ser.timeout = timeout_ms / 1000.0
        return self._ser.read(n)

    @property
    def is_open(self) -> bool:
        return self._ser is not None and self._ser.is_open