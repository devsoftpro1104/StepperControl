"""Кольцевой буфер телеметрии (под графики)."""
from __future__ import annotations

from collections import deque
from typing import Iterable


class TelemetryBuffer:
    def __init__(self, capacity: int = 10_000) -> None:
        self._cap = capacity
        self._t: deque[float] = deque(maxlen=capacity)
        self._v: deque[float] = deque(maxlen=capacity)

    def append(self, t: float, v: float) -> None:
        self._t.append(t)
        self._v.append(v)

    def snapshot(self) -> tuple[Iterable[float], Iterable[float]]:
        return list(self._t), list(self._v)

    def clear(self) -> None:
        self._t.clear()
        self._v.clear()