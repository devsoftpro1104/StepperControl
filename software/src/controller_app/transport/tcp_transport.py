"""Транспорт через TCP (для удалённой отладки)."""
from __future__ import annotations

import socket

from .base import Transport


class TcpTransport(Transport):
    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port
        self._sock: socket.socket | None = None

    def open(self) -> None:
        s = socket.create_connection((self._host, self._port), timeout=2.0)
        s.settimeout(0.2)
        self._sock = s

    def close(self) -> None:
        if self._sock:
            self._sock.close()
            self._sock = None

    def write(self, data: bytes) -> int:
        assert self._sock is not None
        return self._sock.send(data)

    def read(self, n: int, timeout_ms: int) -> bytes:
        assert self._sock is not None
        self._sock.settimeout(timeout_ms / 1000.0)
        try:
            return self._sock.recv(n)
        except TimeoutError:
            return b""

    @property
    def is_open(self) -> bool:
        return self._sock is not None