"""Парсер строк CLI-протокола STM32 → структурированные события.

Идентичен парсеру PySide6-версии: pure-python, без UI-зависимостей.
Первоисточник по формату — docs/cli.md в корне репо.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Union


@dataclass(frozen=True)
class OkEvent:
    payload: str


@dataclass(frozen=True)
class ErrEvent:
    payload: str


@dataclass(frozen=True)
class AsyncEvent:
    tag: str
    args: str


@dataclass(frozen=True)
class CommentEvent:
    text: str


@dataclass(frozen=True)
class TempSample:
    ts_ms: int
    temp_c: float


@dataclass(frozen=True)
class HallSample:
    ts_ms: int
    raw: int
    centered: int


@dataclass(frozen=True)
class MotorSample:
    ts_ms: int
    pos: int
    speed_sps: int
    target: int
    en: int
    direction: int


@dataclass(frozen=True)
class ProbeSample:
    ts_ms: int
    freq_hz: int
    adc: int


@dataclass(frozen=True)
class DumpLine:
    line_idx: int
    hex_data: str


@dataclass(frozen=True)
class UnknownLine:
    raw: str


Event = Union[
    OkEvent, ErrEvent, AsyncEvent, CommentEvent,
    TempSample, HallSample, MotorSample, ProbeSample, DumpLine,
    UnknownLine,
]


_RE_T18 = re.compile(r"^\$T18,\s*(\d+),\s*(-?\d+(?:\.\d+)?)\s*$")
_RE_H   = re.compile(r"^\$H,\s*(\d+),\s*(\d+),\s*(-?\d+)\s*$")
_RE_M   = re.compile(r"^\$M,\s*(\d+),\s*(-?\d+),\s*(\d+),\s*(-?\d+),\s*(\d+),\s*(\d+)\s*$")
_RE_P   = re.compile(r"^\$P,\s*(\d+),\s*(\d+),\s*(\d+)\s*$")
_RE_D   = re.compile(r"^\$D,\s*(\d+),\s*([0-9a-fA-F]+)\s*$")
_RE_EVT = re.compile(r"^!([A-Z][A-Z0-9_]*)\s*(.*)$")


def parse_line(line: str) -> Optional[Event]:
    """Один pass по строке. Возвращает Event или None для пустых строк."""
    line = line.rstrip("\r\n").strip()
    if not line:
        return None

    if line.startswith("+OK"):
        return OkEvent(payload=line[3:].lstrip(" "))

    if line.startswith("-ERR"):
        return ErrEvent(payload=line[4:].lstrip(" "))

    if line.startswith("#"):
        return CommentEvent(text=line[1:].lstrip(" "))

    if (m := _RE_EVT.match(line)) is not None:
        return AsyncEvent(tag=m.group(1), args=m.group(2).strip())

    if line.startswith("$"):
        if (m := _RE_T18.match(line)) is not None:
            return TempSample(int(m.group(1)), float(m.group(2)))
        if (m := _RE_H.match(line)) is not None:
            return HallSample(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if (m := _RE_M.match(line)) is not None:
            g = m.groups()
            return MotorSample(
                ts_ms=int(g[0]), pos=int(g[1]), speed_sps=int(g[2]),
                target=int(g[3]), en=int(g[4]), direction=int(g[5]),
            )
        if (m := _RE_P.match(line)) is not None:
            return ProbeSample(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if (m := _RE_D.match(line)) is not None:
            return DumpLine(line_idx=int(m.group(1)), hex_data=m.group(2))

    return UnknownLine(raw=line)
