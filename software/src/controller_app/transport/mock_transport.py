"""In-memory транспорт для тестов."""
from __future__ import annotations

from collections import deque

from .base import Transport


class MockTransport(Transport):
    def __init__(self) -> None:
        self._open = False
        self._rx: deque[int] = deque()
        self.tx: bytearray = bytearray()

    def open(self) -> None:
        self._open = True

    def close(self) -> None:
        self._open = False

    def write(self, data: bytes) -> int:
        self.tx.extend(data)
        return len(data)

    def read(self, n: int, timeout_ms: int) -> bytes:
        out = bytearray()
        while self._rx and len(out) < n:
            out.append(self._rx.popleft())
        return bytes(out)

    def feed_rx(self, data: bytes) -> None:
        self._rx.extend(data)

    @property
    def is_open(self) -> bool:
        return self._open