"""USB-CDC поверх pyserial — фактически тот же COM, но без скоростного флоуконтроля."""
from __future__ import annotations

from .serial_transport import SerialTransport


class UsbCdcTransport(SerialTransport):
    """USB-CDC устройства видны как обычный COM-порт; baudrate игнорируется хостом."""