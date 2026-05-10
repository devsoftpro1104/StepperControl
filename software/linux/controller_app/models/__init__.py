"""Model-слой Kivy-версии: чистое состояние, домен-типы, транспорт.

  - DeviceModel  — состояние + Kivy-события об изменениях
  - LogSeverity  — теги логирования (строки)
  - parser       — построчный диспетчер CLI (тот же, что в PySide6-версии)
  - SerialWorker — pyserial в обычном threading.Thread

Не зависит от Kivy-виджетов: только kivy.event.EventDispatcher.
"""

from .device_model import DeviceModel
from .log_severity import LogSeverity
from .parser import (
    AsyncEvent, CommentEvent, DumpLine, ErrEvent, Event, HallSample,
    MotorSample, OkEvent, ProbeSample, TempSample, UnknownLine,
    parse_line,
)
from .serial_worker import SerialWorker

__all__ = [
    "DeviceModel", "LogSeverity",
    "parse_line",
    "AsyncEvent", "CommentEvent", "DumpLine", "ErrEvent", "Event",
    "HallSample", "MotorSample", "OkEvent", "ProbeSample",
    "TempSample", "UnknownLine",
    "SerialWorker",
]
