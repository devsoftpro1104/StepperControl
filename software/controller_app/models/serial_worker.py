"""pyserial-обёртка в QThread.

Поток держит порт, в цикле читает входящие байты, режет на строки по \\r\\n
и эмитит сигнал `line_received`. Запись в порт — метод `write_line`,
безопасно вызывать из UI-потока (pyserial.write thread-safe для не пересекающихся
вызовов; здесь от UI один writer).
"""

from __future__ import annotations

from typing import Optional

import serial
from PySide6.QtCore import QThread, Signal


class SerialWorker(QThread):
    line_received = Signal(str)            # одна строка без \r\n
    connected     = Signal(str)            # имя порта
    disconnected  = Signal()
    error         = Signal(str)            # текст ошибки

    def __init__(
        self,
        port: str,
        baud: int = 115200,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._port = port
        self._baud = baud
        self._ser: Optional[serial.Serial] = None
        self._stop = False
        self._buf  = ""

    # ---- thread loop ----

    def run(self) -> None:
        try:
            self._ser = serial.Serial(
                port=self._port,
                baudrate=self._baud,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.05,           # короткий блок-таймаут чтобы реагировать на stop
                write_timeout=1.0,
            )
        except serial.SerialException as exc:
            self.error.emit(f"open failed: {exc}")
            return

        self.connected.emit(self._port)

        try:
            while not self._stop:
                # read возвращает что есть в буфере (или ничего за timeout)
                data = self._ser.read(self._ser.in_waiting or 1)
                if not data:
                    continue
                self._buf += data.decode("ascii", errors="replace")
                while "\n" in self._buf:
                    line, _, self._buf = self._buf.partition("\n")
                    line = line.rstrip("\r")
                    if line:
                        self.line_received.emit(line)
        except serial.SerialException as exc:
            self.error.emit(f"read failed: {exc}")
        finally:
            try:
                if self._ser and self._ser.is_open:
                    self._ser.close()
            except Exception:
                pass
            self.disconnected.emit()

    # ---- внешний API ----

    def stop(self) -> None:
        self._stop = True

    def write_line(self, line: str) -> None:
        """Отправить строку с CRLF. Игнорирует если порт закрыт."""
        if self._ser is None or not self._ser.is_open:
            return
        try:
            self._ser.write((line + "\r\n").encode("ascii"))
        except serial.SerialException as exc:
            self.error.emit(f"write failed: {exc}")
