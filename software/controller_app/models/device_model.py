"""DeviceModel — единственный источник правды о состоянии устройства.

Хранит состояние, эмитит сигналы об изменениях. Никакой логики протокола
или транспорта здесь нет: контроллер пишет, view читает.

Расширение: добавить новое поле состояния (например, motor_state) →
завести у DeviceModel приватный атрибут, public-property для чтения,
сеттер `set_xxx(...)` и сигнал `xxx_changed(...)` — и подписать на него view.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, Signal

from .dump_snapshot import DumpSnapshot
from .log_severity import LogSeverity


class DeviceModel(QObject):
    connection_changed = Signal(bool, str)         # connected, port
    log_appended       = Signal(str, str)          # text, severity
    dump_completed     = Signal(object)            # DumpSnapshot

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._connected: bool = False
        self._port: str = ""
        self._last_dump: Optional[DumpSnapshot] = None

    # ---- read access ----

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def port(self) -> str:
        return self._port

    @property
    def last_dump(self) -> Optional[DumpSnapshot]:
        return self._last_dump

    # ---- mutations (для контроллера) ----

    def set_connection(self, connected: bool, port: str = "") -> None:
        if (self._connected, self._port) == (connected, port):
            return
        self._connected = connected
        self._port      = port
        self.connection_changed.emit(connected, port)

    def append_log(self, text: str, severity: str = LogSeverity.RAW) -> None:
        self.log_appended.emit(text, severity)

    def set_dump(self, snap: DumpSnapshot) -> None:
        self._last_dump = snap
        self.dump_completed.emit(snap)
