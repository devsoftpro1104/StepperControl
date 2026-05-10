"""DeviceModel — единственный первоисточник о состоянии устройства.

Хранит состояние и эмитит Kivy-события об изменениях. Никакой логики
протокола или транспорта здесь нет: контроллер пишет, view слушает.

Все события зарегистрированы как `on_<имя>` — слушатели подключаются через
`bind(on_xxx=callback)`. Идентичен по семантике PySide6-версии (Signal →
register_event_type/dispatch).
"""

from __future__ import annotations

from typing import Optional

from kivy.event import EventDispatcher

from .dump_snapshot import DumpSnapshot
from .log_severity import LogSeverity


class DeviceModel(EventDispatcher):
    # Имена событий для bind(on_xxx=...). Подписи в комментариях — просто
    # документация, как в Qt Signal(...).

    __events__ = (
        "on_connection_changed",        # (connected: bool, port: str)
        "on_log_appended",              # (text: str, severity: str)
        "on_dump_completed",            # (snap: DumpSnapshot,)

        "on_motor_sample_received",     # (sample,)
        "on_temp_sample_received",      # (sample,)
        "on_hall_sample_received",      # (sample,)
        "on_probe_sample_received",     # (sample,)

        "on_ok_received",               # (payload: str,)
        "on_err_received",              # (payload: str,)
        "on_event_received",            # (tag: str, args: str)
    )

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
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
        # connect-а UI не вернётся в состояние "не подключено".
        self._connected = connected
        self._port      = port
        self.dispatch("on_connection_changed", connected, port)

    def append_log(self, text: str, severity: str = LogSeverity.RAW) -> None:
        self.dispatch("on_log_appended", text, severity)

    def set_dump(self, snap: DumpSnapshot) -> None:
        self._last_dump = snap
        self.dispatch("on_dump_completed", snap)

    # ---- стримы датчиков (тонкие пуш-методы, без буферизации) -----------

    def push_motor_sample(self, sample: object) -> None:
        self.dispatch("on_motor_sample_received", sample)

    def push_temp_sample(self, sample: object) -> None:
        self.dispatch("on_temp_sample_received", sample)

    def push_hall_sample(self, sample: object) -> None:
        self.dispatch("on_hall_sample_received", sample)

    def push_probe_sample(self, sample: object) -> None:
        self.dispatch("on_probe_sample_received", sample)

    def push_ok(self, payload: str) -> None:
        self.dispatch("on_ok_received", payload)

    def push_err(self, payload: str) -> None:
        self.dispatch("on_err_received", payload)

    def push_event(self, tag: str, args: str) -> None:
        self.dispatch("on_event_received", tag, args)

    # ---- default handlers (Kivy требует) ---------------------------------
    # Каждое событие должно иметь дефолтный обработчик с тем же именем,
    # иначе EventDispatcher падает при dispatch. Мы используем no-op.

    def on_connection_changed(self, *_a, **_k) -> None: ...
    def on_log_appended(self, *_a, **_k) -> None: ...
    def on_dump_completed(self, *_a, **_k) -> None: ...
    def on_motor_sample_received(self, *_a, **_k) -> None: ...
    def on_temp_sample_received(self, *_a, **_k) -> None: ...
    def on_hall_sample_received(self, *_a, **_k) -> None: ...
    def on_probe_sample_received(self, *_a, **_k) -> None: ...
    def on_ok_received(self, *_a, **_k) -> None: ...
    def on_err_received(self, *_a, **_k) -> None: ...
    def on_event_received(self, *_a, **_k) -> None: ...
