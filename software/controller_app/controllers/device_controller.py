"""DeviceController — клей между транспортом, парсером и моделью.

Владеет SerialWorker и ProbeDumpCollector. View его не знает: подписан на
`connect_requested`, `disconnect_requested`, `command_submitted` от UI и
толкает результаты в DeviceModel — view обновляется через сигналы модели.

Расширение протокола: добавить новый тип события в parser.py и обработать
его в `_on_line` (одна ветка `isinstance`). Новая команда → метод-слот
`@Slot(...)` + сигнал из view → connect в `__main__.py`.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, Slot

from ..models import (
    AsyncEvent, CommentEvent, DeviceModel, DumpLine, DumpSnapshot,
    ErrEvent, HallSample, LogSeverity, MotorSample, OkEvent, parse_line,
    ProbeDumpCollector, ProbeSample, SerialWorker, TempSample, UnknownLine,
)


class DeviceController(QObject):
    BAUD = 115200

    def __init__(self, model: DeviceModel, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._model:  DeviceModel = model
        self._worker: Optional[SerialWorker] = None
        self._probe:  ProbeDumpCollector = ProbeDumpCollector()

    # ---- слоты для view-сигналов --------------------------------------

    @Slot(str)
    def connect_to(self, port: str) -> None:
        if self._worker is not None or not port:
            return
        w = SerialWorker(port=port, baud=self.BAUD)
        w.line_received.connect(self._on_line)
        w.connected.connect(self._on_serial_connected)
        w.disconnected.connect(self._on_serial_disconnected)
        w.error.connect(self._on_serial_error)
        self._worker = w
        w.start()

    @Slot()
    def disconnect(self) -> None:
        if self._worker is None:
            return
        self._worker.stop()
        self._worker.wait(2000)
        self._worker = None

    @Slot(str)
    def send_command(self, cmd: str) -> None:
        cmd = cmd.strip()
        if not cmd or self._worker is None:
            return
        self._model.append_log(f">>> {cmd}", LogSeverity.TX)
        self._worker.write_line(cmd)

    @Slot()
    def request_probe_dump(self) -> None:
        self.send_command("PROBE DUMP")

    def shutdown(self) -> None:
        if self._worker is not None:
            self._worker.stop()
            self._worker.wait(2000)
            self._worker = None

    # ---- слоты воркера ------------------------------------------------

    INIT_SEQUENCE = (
        "MOTOR ZERO",     # обнулить счётчик шагов (требует перепрошитой firmware)
        "MOTOR ON",       # $M-стрим
        "TEMP ON",        # $T18-стрим
        "HALL ON",        # $H-стрим
        "HALL ZERO",      # калибровка нуля Hall-датчика
    )

    @Slot(str)
    def _on_serial_connected(self, port: str) -> None:
        self._model.append_log(f"[connected to {port} @ {self.BAUD}]", LogSeverity.OK)
        self._model.set_connection(True, port)
        # Init sequence: каждая команда отдельной строкой. Если одна
        # неизвестна старой прошивке (-ERR unknown), остальные всё равно
        # отрабатывают.
        for cmd in self.INIT_SEQUENCE:
            self.send_command(cmd)

    @Slot()
    def _on_serial_disconnected(self) -> None:
        self._model.append_log("[disconnected]", LogSeverity.CMT)
        self._model.set_connection(False, "")

    @Slot(str)
    def _on_serial_error(self, msg: str) -> None:
        self._model.append_log(f"[serial] {msg}", LogSeverity.ERR)

    @Slot(str)
    def _on_line(self, line: str) -> None:
        evt = parse_line(line)
        if evt is None:
            return

        if isinstance(evt, OkEvent):
            if self._probe.feed_ok(evt.payload) and self._probe.complete:
                self._emit_dump()
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
            self._probe.feed_line(evt)
            return

        # Высокочастотные стримы — в model для UI (графики/ротор/readout),
        # без логирования: на 50–100 Hz они захлестнули бы терминал.
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

        # неизвестный тип события — пишем в лог, чтобы не потерять
        self._model.append_log(f"[stream] {evt}", LogSeverity.STREAM)

    # ---- внутреннее ---------------------------------------------------

    def _emit_dump(self) -> None:
        samples   = self._probe.samples_array().copy()
        sample_hz = self._probe.sample_hz
        lines     = self._probe.lines_seen
        n         = samples.size

        adc_min = int(samples.min()) if n else 0
        adc_max = int(samples.max()) if n else 0
        win_us  = (n * 1e6 / sample_hz) if sample_hz else 0.0

        self._model.append_log(
            f"[dump] lines={lines}/32  samples={n}  {sample_hz} Hz  "
            f"window={win_us:.1f} µs  adc=[{adc_min}..{adc_max}]",
            LogSeverity.OK,
        )
        self._model.set_dump(DumpSnapshot(
            samples=samples, sample_hz=sample_hz, lines_seen=lines,
        ))
        self._probe.reset()
