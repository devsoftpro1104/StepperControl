"""DeviceController — клей между транспортом, парсером и моделью.

Владеет SerialWorker. View его не знает: вызывает методы `connect_to`,
`disconnect`, `send_command` и слушает изменения через DeviceModel.

Колбэки SerialWorker'а прилетают из рабочего потока — каждый из них
маршалится на UI-thread Kivy через `Clock.schedule_once`. Это аналог
автоматического queued-connection из Qt-версии.
"""

from __future__ import annotations

from typing import Optional

from kivy.clock import Clock

from ..models import (
    AsyncEvent, CommentEvent, DeviceModel, DumpLine, ErrEvent,
    HallSample, LogSeverity, MotorSample, OkEvent, parse_line,
    ProbeSample, SerialWorker, TempSample, UnknownLine,
)


class DeviceController:
    BAUD = 115200

    INIT_SEQUENCE = (
        "MOTOR ZERO",
        "MOTOR ON",
        "TEMP ON",
        "HALL ON",
        "HALL ZERO",
    )

    def __init__(self, model: DeviceModel) -> None:
        self._model:  DeviceModel = model
        self._worker: Optional[SerialWorker] = None

    # ---- API для view --------------------------------------------------

    def connect_to(self, port: str) -> None:
        if self._worker is not None or not port:
            return
        w = SerialWorker(
            port=port, baud=self.BAUD,
            on_line=self._post_line,
            on_connected=self._post_connected,
            on_disconnected=self._post_disconnected,
            on_error=self._post_error,
        )
        self._worker = w
        w.start()

    def disconnect(self) -> None:
        if self._worker is None:
            return
        self._worker.stop()
        self._worker.join(timeout=2.0)
        self._worker = None

    def send_command(self, cmd: str) -> None:
        cmd = cmd.strip()
        if not cmd or self._worker is None:
            return
        self._model.append_log(f">>> {cmd}", LogSeverity.TX)
        self._worker.write_line(cmd)

    def request_probe_dump(self) -> None:
        self.send_command("PROBE DUMP")

    def shutdown(self) -> None:
        if self._worker is not None:
            self._worker.stop()
            self._worker.join(timeout=2.0)
            self._worker = None

    # ---- маршалинг колбэков на UI-thread -------------------------------
    # Worker дёргает _post_*; они через Clock.schedule_once дёргают _on_*
    # уже на main thread'е, где безопасно трогать модель/виджеты.

    def _post_line(self, line: str) -> None:
        Clock.schedule_once(lambda _dt, l=line: self._on_line(l), 0)

    def _post_connected(self, port: str) -> None:
        Clock.schedule_once(lambda _dt, p=port: self._on_serial_connected(p), 0)

    def _post_disconnected(self) -> None:
        Clock.schedule_once(lambda _dt: self._on_serial_disconnected(), 0)

    def _post_error(self, msg: str) -> None:
        Clock.schedule_once(lambda _dt, m=msg: self._on_serial_error(m), 0)

    # ---- main-thread обработчики ---------------------------------------

    def _on_serial_connected(self, port: str) -> None:
        self._model.append_log(f"[connected to {port} @ {self.BAUD}]", LogSeverity.OK)
        self._model.set_connection(True, port)
        for cmd in self.INIT_SEQUENCE:
            self.send_command(cmd)

    def _on_serial_disconnected(self) -> None:
        self._model.append_log("[disconnected]", LogSeverity.CMT)
        self._model.set_connection(False, "")

    def _on_serial_error(self, msg: str) -> None:
        self._model.append_log(f"[serial] {msg}", LogSeverity.ERR)

    def _on_line(self, line: str) -> None:
        evt = parse_line(line)
        if evt is None:
            return

        if isinstance(evt, OkEvent):
            self._model.append_log(f"+OK {evt.payload}", LogSeverity.OK)
            self._model.push_ok(evt.payload)
            return
        if isinstance(evt, ErrEvent):
            self._model.append_log(f"-ERR {evt.payload}", LogSeverity.ERR)
            self._model.push_err(evt.payload)
            return
        if isinstance(evt, AsyncEvent):
            self._model.append_log(f"!{evt.tag} {evt.args}".rstrip(), LogSeverity.EVENT)
            self._model.push_event(evt.tag, evt.args)
            return
        if isinstance(evt, CommentEvent):
            self._model.append_log(f"# {evt.text}", LogSeverity.CMT)
            return
        if isinstance(evt, DumpLine):
            # MVP: PROBE DUMP не визуализируется (см. README) — сырые $D
            # просто пропускаем.
            return

        if isinstance(evt, MotorSample):
            self._model.push_motor_sample(evt)
            return
        if isinstance(evt, TempSample):
            self._model.push_temp_sample(evt)
            return
        if isinstance(evt, HallSample):
            self._model.push_hall_sample(evt)
            return
        if isinstance(evt, ProbeSample):
            self._model.push_probe_sample(evt)
            return

        if isinstance(evt, UnknownLine):
            self._model.append_log(evt.raw, LogSeverity.RAW)
            return

        self._model.append_log(f"[stream] {evt}", LogSeverity.STREAM)
