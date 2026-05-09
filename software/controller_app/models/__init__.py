"""Model-слой: чистое состояние, домен-типы и инфраструктура связи с MCU.

  - DeviceModel       — состояние + Qt-сигналы об изменениях
  - DumpSnapshot      — один завершённый PROBE DUMP
  - LogSeverity       — теги логирования (строки, не QColor)
  - parser            — построчный диспетчер CLI
  - ProbeDumpCollector — сборка $D-снимка
  - SerialWorker      — pyserial в QThread

Не зависит от QtWidgets/pyqtgraph: ни одного UI-импорта.
"""

from .device_model import DeviceModel
from .dump_snapshot import DumpSnapshot
from .log_severity import LogSeverity
from .parser import (
    AsyncEvent, CommentEvent, DumpLine, ErrEvent, Event, HallSample,
    MotorSample, OkEvent, ProbeSample, TempSample, UnknownLine,
    parse_line,
)
from .probe_collector import ProbeDumpCollector
from .serial_worker import SerialWorker

__all__ = [
    # state / domain
    "DeviceModel", "DumpSnapshot", "LogSeverity",
    # parser
    "parse_line",
    "AsyncEvent", "CommentEvent", "DumpLine", "ErrEvent", "Event",
    "HallSample", "MotorSample", "OkEvent", "ProbeSample",
    "TempSample", "UnknownLine",
    # transport / collectors
    "ProbeDumpCollector", "SerialWorker",
]
