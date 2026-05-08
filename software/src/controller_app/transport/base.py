"""Абстракция транспорта."""
from __future__ import annotations

from abc import ABC, abstractmethod


class Transport(ABC):
    @abstractmethod
    def open(self) -> None: ...
    @abstractmethod
    def close(self) -> None: ...
    @abstractmethod
    def write(self, data: bytes) -> int: ...
    @abstractmethod
    def read(self, n: int, timeout_ms: int) -> bytes: ...
    @property
    @abstractmethod
    def is_open(self) -> bool: ...