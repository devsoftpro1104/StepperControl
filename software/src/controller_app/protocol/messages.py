"""Сгенерировано из shared/protocol/protocol.yaml — НЕ РЕДАКТИРОВАТЬ ВРУЧНУЮ.

Сейчас здесь ручные dataclass-ы для нескольких команд; будут заменены кодогенерацией.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class Cmd(IntEnum):
    PING             = 0x01
    GET_VERSION      = 0x02
    MOTOR_MOVE       = 0x10
    MOTOR_STOP       = 0x11
    STREAM_TELEMETRY = 0x20


@dataclass(frozen=True)
class MotorMoveReq:
    steps: int
    speed: int
    accel: int


@dataclass(frozen=True)
class TelemetrySample:
    ts_ms: int
    position: int
    current: int
    temp_c10: int