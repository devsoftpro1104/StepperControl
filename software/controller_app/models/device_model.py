"""DeviceModel — единственный первоисточник о состоянии устройства.

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

    # Стримы датчиков. object — соответствующий dataclass из parser.py
    # (MotorSample / TempSample / HallSample / ProbeSample). Так view-слой
    # может подписаться напрямую и не зависит от формата сырой CLI-строки.
    motor_sample_received = Signal(object)
    temp_sample_received  = Signal(object)
    hall_sample_received  = Signal(object)
    probe_sample_received = Signal(object)

    # Ответы и async-события прошивки — для CSV-очереди в TerminalTab.
    ok_received    = Signal(str)              # payload без префикса "+OK "
    err_received   = Signal(str)              # payload без префикса "-ERR "
    event_received = Signal(str, str)         # tag, args (от "!TAG args")

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
        # Без dedup: даже повторный (False,"") нужен — иначе при провале
        # connect-а кнопка/LED во view не вернутся в состояние "не подключено".
        self._connected = connected
        self._port      = port
        self.connection_changed.emit(connected, port)

    def append_log(self, text: str, severity: str = LogSeverity.RAW) -> None:
        self.log_appended.emit(text, severity)

    def set_dump(self, snap: DumpSnapshot) -> None:
        self._last_dump = snap
        self.dump_completed.emit(snap)

    # ---- стримы датчиков (тонкие пуш-методы, без буферизации) ----------

    def push_motor_sample(self, sample: object) -> None:
        self.motor_sample_received.emit(sample)

    def push_temp_sample(self, sample: object) -> None:
        self.temp_sample_received.emit(sample)

    def push_hall_sample(self, sample: object) -> None:
        self.hall_sample_received.emit(sample)

    def push_probe_sample(self, sample: object) -> None:
        self.probe_sample_received.emit(sample)

    def push_ok(self, payload: str) -> None:
        self.ok_received.emit(payload)

    def push_err(self, payload: str) -> None:
        self.err_received.emit(payload)

    def push_event(self, tag: str, args: str) -> None:
        self.event_received.emit(tag, args)
