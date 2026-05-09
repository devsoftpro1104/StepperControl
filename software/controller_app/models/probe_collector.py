"""Сборка PROBE DUMP-снимка из последовательности строк.

MCU отдаёт:
    +OK PROBE DUMP begin samples=4096 sample_hz=525000
    $D, 0,  <128 × 3 hex>
    ...
    $D, 31, <128 × 3 hex>
    +OK PROBE DUMP end

Сценарий использования:
    col = ProbeDumpCollector()
    col.feed_ok("PROBE DUMP begin samples=4096 sample_hz=525000")  # из OkEvent.payload
    for dl in dump_lines:
        col.feed_line(dl)
    col.feed_ok("PROBE DUMP end")
    if col.complete:
        samples = col.samples_array()      # numpy uint16, длина 4096
        time_us = col.time_axis_us()       # numpy float64, та же длина
"""

from __future__ import annotations

import re
from typing import Optional

import numpy as np

from .parser import DumpLine


_RE_BEGIN = re.compile(
    r"^PROBE DUMP begin samples=(\d+) sample_hz=(\d+)\s*$"
)


class ProbeDumpCollector:

    LINE_SAMPLES = 128            # совпадает с PROBE_DUMP_LINE_SAMPLES в shell.c

    def __init__(self) -> None:
        self.reset()

    # ---- состояние ----

    def reset(self) -> None:
        self.expected_samples: int = 0
        self.sample_hz: int = 0
        self._buf: Optional[np.ndarray] = None
        self._lines_seen: int = 0
        self.complete: bool = False
        self.in_progress: bool = False

    # ---- скармливание ----

    def feed_ok(self, payload: str) -> bool:
        """Передать payload OkEvent. True если это begin/end PROBE DUMP."""
        if (m := _RE_BEGIN.match(payload)) is not None:
            self.expected_samples = int(m.group(1))
            self.sample_hz        = int(m.group(2))
            self._buf             = np.zeros(self.expected_samples, dtype=np.uint16)
            self._lines_seen      = 0
            self.complete         = False
            self.in_progress      = True
            return True
        if payload.strip() == "PROBE DUMP end":
            # «end» считаем валидным только если был begin и набрали все строки
            if self.in_progress and self._buf is not None:
                self.complete    = True
                self.in_progress = False
            return True
        return False

    def feed_line(self, dl: DumpLine) -> None:
        if not self.in_progress or self._buf is None:
            return
        base = dl.line_idx * self.LINE_SAMPLES
        # 12-бит значения, по 3 hex-символа на сэмпл
        for i in range(self.LINE_SAMPLES):
            chunk = dl.hex_data[i * 3 : (i + 1) * 3]
            if len(chunk) != 3:
                break
            try:
                v = int(chunk, 16)
            except ValueError:
                continue
            idx = base + i
            if idx < self.expected_samples:
                self._buf[idx] = v
        self._lines_seen += 1

    # ---- результат ----

    @property
    def lines_seen(self) -> int:
        return self._lines_seen

    def samples_array(self) -> np.ndarray:
        if self._buf is None:
            return np.zeros(0, dtype=np.uint16)
        return self._buf

    def time_axis_us(self) -> np.ndarray:
        if self._buf is None or self.sample_hz == 0:
            return np.zeros(0, dtype=np.float64)
        n = self._buf.shape[0]
        return np.arange(n, dtype=np.float64) * (1_000_000.0 / self.sample_hz)

    def voltage_axis(self, vref: float = 3.3) -> np.ndarray:
        if self._buf is None:
            return np.zeros(0, dtype=np.float64)
        return self._buf.astype(np.float64) * (vref / 4095.0)
