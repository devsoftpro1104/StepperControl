"""Снимок одного завершённого PROBE DUMP — сырые ADC + параметры дискретизации."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class DumpSnapshot:
    samples: np.ndarray         # uint16 raw ADC, длина N
    sample_hz: int
    lines_seen: int             # сколько $D-строк реально пришло
