"""Фикстуры сквозных тестов «прошивка ↔ хост».

Тесты этого уровня требуют:
- подключённую плату (или QEMU/симулятор), либо
- запущенный mock-устройство (в `software/tests/integration` уже покрыто).
"""
from __future__ import annotations

import pytest


@pytest.fixture(scope="session")
def serial_port() -> str:
    import os
    return os.environ.get("SC_TEST_PORT", "COM3")