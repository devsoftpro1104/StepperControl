"""Сборка/разбор кадров протокола."""
from __future__ import annotations

import struct

from .crc import crc16_ccitt_false

SOF = 0xA5


def encode_frame(cmd: int, seq: int, payload: bytes) -> bytes:
    header = struct.pack("<BHBB", SOF, len(payload), cmd, seq)
    body   = header[1:] + payload  # CRC по len..payload? см. protocol.md
    crc    = crc16_ccitt_false(struct.pack("<BB", cmd, seq) + payload)
    return header + payload + struct.pack("<H", crc)


def decode_frame(buf: bytes) -> tuple[int, int, bytes] | None:
    """Возвращает (cmd, seq, payload) или None при недостатке данных/ошибке."""
    if len(buf) < 7 or buf[0] != SOF:
        return None
    (length,) = struct.unpack_from("<H", buf, 1)
    total = 1 + 2 + 1 + 1 + length + 2
    if len(buf) < total:
        return None
    cmd = buf[3]
    seq = buf[4]
    payload = bytes(buf[5:5 + length])
    (crc,) = struct.unpack_from("<H", buf, 5 + length)
    if crc16_ccitt_false(bytes([cmd, seq]) + payload) != crc:
        return None
    return cmd, seq, payload