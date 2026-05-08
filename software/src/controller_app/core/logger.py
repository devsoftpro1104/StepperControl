"""Конфигурация logging для приложения."""
from __future__ import annotations

import logging
import sys


def configure(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )