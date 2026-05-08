"""Высокоуровневый фасад устройства."""
from __future__ import annotations

from ..transport.base import Transport


class Device:
    def __init__(self, transport: Transport) -> None:
        self._t = transport

    def connect(self) -> None:
        self._t.open()

    def disconnect(self) -> None:
        self._t.close()