"""pyserial-обёртка в обычном threading.Thread.

Поток держит порт, в цикле читает входящие байты, режет на строки по \\r\\n
и зовёт колбэки. Запись в порт — метод `write_line`, вызывать с UI-потока
безопасно (один writer, pyserial.write thread-safe для непересекающихся
вызовов).

Колбэки вызываются ИЗ РАБОЧЕГО ПОТОКА. Получатель сам обязан переключиться
на UI-поток (`kivy.clock.Clock.schedule_once`), чтобы не трогать виджеты
вне main thread'а. В этом отличие от Qt-версии, где Signal делает это сам.
"""

from __future__ import annotations

import threading
from typing import Callable, Optional

import serial


class SerialWorker(threading.Thread):

    def __init__(
        self,
        port: str,
        baud: int = 115200,
        on_line: Optional[Callable[[str], None]]   = None,
        on_connected: Optional[Callable[[str], None]] = None,
        on_disconnected: Optional[Callable[[], None]] = None,
        on_error: Optional[Callable[[str], None]]  = None,
    ) -> None:
        super().__init__(daemon=True)
        self._port = port
        self._baud = baud
        self._ser: Optional[serial.Serial] = None
        self._stop = threading.Event()
        self._buf  = ""

        self._on_line         = on_line         or (lambda _l: None)
        self._on_connected    = on_connected    or (lambda _p: None)
        self._on_disconnected = on_disconnected or (lambda: None)
        self._on_error        = on_error        or (lambda _m: None)

    # ---- thread loop ----

    def run(self) -> None:
        try:
            self._ser = serial.Serial(
                port=self._port,
                baudrate=self._baud,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.05,
                write_timeout=1.0,
            )
        except serial.SerialException as exc:
            self._on_error(f"open failed: {exc}")
            return

        self._on_connected(self._port)

        try:
            while not self._stop.is_set():
                data = self._ser.read(self._ser.in_waiting or 1)
                if not data:
                    continue
                self._buf += data.decode("ascii", errors="replace")
                while "\n" in self._buf:
                    line, _, self._buf = self._buf.partition("\n")
                    line = line.rstrip("\r")
                    if line:
                        self._on_line(line)
        except serial.SerialException as exc:
            self._on_error(f"read failed: {exc}")
        finally:
            try:
                if self._ser and self._ser.is_open:
                    self._ser.close()
            except Exception:
                pass
            self._on_disconnected()

    # ---- внешний API ----

    def stop(self) -> None:
        self._stop.set()

    def write_line(self, line: str) -> None:
        """Отправить строку с CRLF. Игнорирует если порт закрыт."""
        if self._ser is None or not self._ser.is_open:
            return
        try:
            self._ser.write((line + "\r\n").encode("ascii"))
        except serial.SerialException as exc:
            self._on_error(f"write failed: {exc}")
