"""Общие фикстуры для тестов хост-приложения."""
from __future__ import annotations

import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def _qt_offscreen() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")