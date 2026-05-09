"""Главное окно: COM-порт, лог входящих, поле команды, кнопка PROBE DUMP, график.

Layout:
    ┌──────────────────────────────────────────────────────────────┐
    │ [COM5 ▼] [Refresh] [Connect]   [PROBE DUMP]  [Clear log]     │
    ├──────────────────────────────────────────────────────────────┤
    │ Log area (read-only, color-coded)                            │
    │                                                              │
    ├──────────────────────────────────────────────────────────────┤
    │ Cmd: [____________________] [Send]                           │
    ├──────────────────────────────────────────────────────────────┤
    │ Waveform plot (pyqtgraph)                                    │
    │                                                              │
    └──────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QTextCharFormat, QColor, QTextCursor
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLineEdit, QMainWindow, QPushButton,
    QTextEdit, QVBoxLayout, QWidget,
)
from serial.tools import list_ports

from .parser import (
    AsyncEvent, CommentEvent, DumpLine, ErrEvent, OkEvent,
    parse_line, ProbeSample, UnknownLine,
)
from .probe_collector import ProbeDumpCollector
from .serial_worker import SerialWorker


_COLOR_OK     = QColor("#7ec77e")
_COLOR_ERR    = QColor("#e26464")
_COLOR_EVENT  = QColor("#e2c264")
_COLOR_STREAM = QColor("#7ec0e2")
_COLOR_CMT    = QColor("#999999")
_COLOR_RAW    = QColor("#cccccc")
_COLOR_TX     = QColor("#ffffff")


class MainWindow(QMainWindow):
    BAUD = 115200

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("StepperControl host")
        self.resize(1100, 800)

        self._worker: Optional[SerialWorker] = None
        self._probe = ProbeDumpCollector()
        self._build_ui()
        self._refresh_ports()

    # ---- UI ----

    def _build_ui(self) -> None:
        central = QWidget(self)
        layout  = QVBoxLayout(central)

        # row 1 — порт + кнопки
        top = QHBoxLayout()
        self.cb_port = QComboBox()
        self.cb_port.setMinimumWidth(160)
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self._refresh_ports)
        self.btn_connect = QPushButton("Connect")
        self.btn_connect.clicked.connect(self._toggle_connect)
        self.btn_dump = QPushButton("PROBE DUMP")
        self.btn_dump.setEnabled(False)
        self.btn_dump.clicked.connect(lambda: self._send("PROBE DUMP"))
        self.btn_clear = QPushButton("Clear log")
        self.btn_clear.clicked.connect(lambda: self.log.clear())
        top.addWidget(self.cb_port)
        top.addWidget(self.btn_refresh)
        top.addWidget(self.btn_connect)
        top.addStretch(1)
        top.addWidget(self.btn_dump)
        top.addWidget(self.btn_clear)
        layout.addLayout(top)

        # лог
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setStyleSheet("background:#1e1e1e; color:#eaeaea; font-family:Consolas,monospace; font-size:11pt;")
        layout.addWidget(self.log, stretch=2)

        # ввод команды
        cmd_row = QHBoxLayout()
        self.le_cmd = QLineEdit()
        self.le_cmd.setPlaceholderText("введи команду и нажми Enter (например: PING)")
        self.le_cmd.returnPressed.connect(self._on_send)
        self.btn_send = QPushButton("Send")
        self.btn_send.setEnabled(False)
        self.btn_send.clicked.connect(self._on_send)
        cmd_row.addWidget(self.le_cmd)
        cmd_row.addWidget(self.btn_send)
        layout.addLayout(cmd_row)

        # plot
        pg.setConfigOption("background", "#1e1e1e")
        pg.setConfigOption("foreground", "#cccccc")
        self.plot = pg.PlotWidget(title="PROBE DUMP waveform")
        self.plot.setLabel("bottom", "time", units="µs")
        self.plot.setLabel("left",   "voltage", units="V")
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.plot_curve = self.plot.plot(pen=pg.mkPen("#ffd054", width=1))
        layout.addWidget(self.plot, stretch=3)

        self.setCentralWidget(central)

    # ---- COM-порты ----

    def _refresh_ports(self) -> None:
        self.cb_port.clear()
        for p in list_ports.comports():
            label = f"{p.device}  ({p.description})" if p.description else p.device
            self.cb_port.addItem(label, userData=p.device)
        if self.cb_port.count() == 0:
            self.cb_port.addItem("(нет портов)", userData=None)

    # ---- connect / disconnect ----

    def _toggle_connect(self) -> None:
        if self._worker is None:
            port = self.cb_port.currentData()
            if not port:
                self._append_line("(нет выбранного порта)", _COLOR_ERR)
                return
            self._worker = SerialWorker(port=port, baud=self.BAUD)
            self._worker.line_received.connect(self._on_line)
            self._worker.connected.connect(self._on_connected)
            self._worker.disconnected.connect(self._on_disconnected)
            self._worker.error.connect(lambda s: self._append_line(f"[serial] {s}", _COLOR_ERR))
            self._worker.start()
            self.btn_connect.setText("Disconnect")
        else:
            self._worker.stop()
            self._worker.wait(2000)
            self._worker = None
            self.btn_connect.setText("Connect")
            self.btn_dump.setEnabled(False)
            self.btn_send.setEnabled(False)

    @Slot(str)
    def _on_connected(self, port: str) -> None:
        self._append_line(f"[connected to {port} @ {self.BAUD}]", _COLOR_OK)
        self.btn_dump.setEnabled(True)
        self.btn_send.setEnabled(True)

    @Slot()
    def _on_disconnected(self) -> None:
        self._append_line("[disconnected]", _COLOR_CMT)
        self.btn_dump.setEnabled(False)
        self.btn_send.setEnabled(False)

    # ---- отправка ----

    def _on_send(self) -> None:
        cmd = self.le_cmd.text().strip()
        if not cmd:
            return
        self._send(cmd)
        self.le_cmd.clear()

    def _send(self, cmd: str) -> None:
        if not self._worker:
            return
        self._append_line(f">>> {cmd}", _COLOR_TX)
        self._worker.write_line(cmd)

    # ---- приём ----

    @Slot(str)
    def _on_line(self, line: str) -> None:
        evt = parse_line(line)

        # OK/ERR — могут нести begin/end PROBE DUMP
        if isinstance(evt, OkEvent):
            if self._probe.feed_ok(evt.payload):
                if self._probe.complete:
                    self._plot_dump()
            self._append_line(f"+OK {evt.payload}", _COLOR_OK)
            return
        if isinstance(evt, ErrEvent):
            self._append_line(f"-ERR {evt.payload}", _COLOR_ERR)
            return
        if isinstance(evt, AsyncEvent):
            self._append_line(f"!{evt.tag} {evt.args}".rstrip(), _COLOR_EVENT)
            return
        if isinstance(evt, CommentEvent):
            self._append_line(f"# {evt.text}", _COLOR_CMT)
            return
        if isinstance(evt, DumpLine):
            self._probe.feed_line(evt)
            # сами строки $D в лог не пихаем — слишком много
            return
        if isinstance(evt, ProbeSample):
            self._append_line(
                f"$P ts={evt.ts_ms} freq={evt.freq_hz} adc={evt.adc}",
                _COLOR_STREAM,
            )
            return
        if isinstance(evt, UnknownLine):
            self._append_line(evt.raw, _COLOR_RAW)
            return

        # остальные стримы — компактным однострочником
        self._append_line(f"[stream] {evt}", _COLOR_STREAM)

    # ---- waveform ----

    def _plot_dump(self) -> None:
        t   = self._probe.time_axis_us()
        v   = self._probe.voltage_axis()
        raw = self._probe.samples_array()
        self.plot_curve.setData(t, v)
        self.plot.enableAutoRange(axis="xy", enable=True)
        self.plot.autoRange()

        if raw.size:
            adc_min, adc_max = int(raw.min()), int(raw.max())
        else:
            adc_min = adc_max = 0
        self._append_line(
            f"[dump] lines={self._probe.lines_seen}/32  "
            f"samples={len(v)}  {self._probe.sample_hz} Hz  "
            f"window={len(v) * 1e6 / self._probe.sample_hz:.1f} µs  "
            f"adc=[{adc_min}..{adc_max}]",
            _COLOR_OK,
        )
        # сбрасываем коллектор для следующего DUMP
        self._probe.reset()

    # ---- лог ----

    def _append_line(self, text: str, color: QColor) -> None:
        cursor = self.log.textCursor()
        cursor.movePosition(QTextCursor.End)
        fmt = QTextCharFormat()
        fmt.setForeground(color)
        cursor.insertText(text + "\n", fmt)
        self.log.setTextCursor(cursor)
        self.log.ensureCursorVisible()

    # ---- чистый shutdown ----

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if self._worker is not None:
            self._worker.stop()
            self._worker.wait(2000)
        super().closeEvent(event)
