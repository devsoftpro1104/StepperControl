"""Вкладка ТЕРМИНАЛ: лог прошивки + raw command-line + clear/add-кнопки.

Лог тут — единственное окно, куда падают `+OK` / `-ERR` / `!event` /
комментарии и неизвестные строки. Высокочастотные стримы ($M, $T18, $H, $P)
сюда не пишутся (они визуализируются на других вкладках) — иначе при
50–100 Hz терминал перегружается.

Кнопка ADD открывает file-picker для .csv с командами (g-code-подобный
формат). Команды выполняются строго ПО ОЧЕРЕДИ: следующая отправляется
только когда прошивка подтвердила завершение текущей.

Логика подтверждений:
  • MOVE  → ждём событие `!DONE MOVE` (фактическое окончание движения,
            а не `+OK MOVE`, который приходит сразу при старте)
  • прочие → ждём `+OK …` или `-ERR …`
  • `-ERR` ⇒ пропускаем команду и идём дальше (одна ошибка не должна
            ломать всю последовательность)

Пока очередь активна, command-line и кнопка ADD блокируются — иначе
ответы прошивки на ручные команды ошибочно «закрывали» бы очередь.
"""

from __future__ import annotations

from collections import deque
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QPushButton, QVBoxLayout, QWidget,
)

from ..command_panel import CommandPanel
from ..log_panel import LogPanel
from ..panel import Panel
from ..theme import industrial_button_qss


class TerminalTab(QWidget):
    command_submitted = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")

        self.log = LogPanel()
        self.cmd = CommandPanel()

        self.btn_add    = QPushButton("ADD")
        self.btn_cancel = QPushButton("CANCEL")
        self.btn_clear  = QPushButton("CLEAR")
        for b in (self.btn_add, self.btn_cancel, self.btn_clear):
            b.setMinimumHeight(36)
            b.setMinimumWidth(110)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(industrial_button_qss())
        self.btn_cancel.setEnabled(False)        # активна только во время очереди
        self.btn_add.clicked.connect(self._on_add)
        self.btn_cancel.clicked.connect(self._on_cancel)
        self.btn_clear.clicked.connect(self.log.clear)

        log_panel = Panel("LOG")
        log_panel.add(self.log, 1)

        cmd_row = QHBoxLayout()
        cmd_row.setSpacing(8)
        cmd_row.addWidget(self.cmd, 1)
        cmd_row.addWidget(self.btn_add)
        cmd_row.addWidget(self.btn_cancel)
        cmd_row.addWidget(self.btn_clear)

        cmd_panel = Panel("COMMAND")
        cmd_panel.add_layout(cmd_row)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(log_panel, 1)
        layout.addWidget(cmd_panel)

        # forward
        self.cmd.command_submitted.connect(self.command_submitted)

        # очередь CSV-команд
        self._queue:    deque[str]    = deque()
        self._pending:  Optional[str] = None    # отправленная, ждём подтверждения
        self._wait_done: bool         = False   # для MOVE — ждать !DONE MOVE

    def append_log(self, text: str, severity: str = "raw") -> None:
        self.log.append_line(text, severity)

    # ---- слоты для ответов прошивки -----------------------------------

    def on_ok(self, _payload: str) -> None:
        if self._pending is None:
            return
        if self._wait_done:
            # MOVE: +OK прилетел, но движение только запущено. Ждём !DONE.
            return
        self._advance()

    def on_err(self, payload: str) -> None:
        if self._pending is None:
            return
        # Команда отвергнута (busy/bad-arg/…). Логируем причину и идём дальше.
        self.append_log(
            f"[csv] '{self._pending}' → ERR ({payload}), пропуск",
            "err",
        )
        self._advance()

    def on_event(self, tag: str, args: str) -> None:
        if self._pending is None or not self._wait_done:
            return
        if tag == "DONE" and "MOVE" in args.upper():
            self._advance()

    # ---- CSV loader ----------------------------------------------------

    def _on_add(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите .csv файл с командами",
            "",
            "CSV files (*.csv);;All files (*.*)",
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                raw_lines = f.readlines()
        except OSError as exc:
            self.append_log(f"[csv] read error: {exc}", "err")
            return

        commands: list[str] = []
        for raw in raw_lines:
            line = raw.strip()
            if not line or line.startswith("#") or line.startswith(";"):
                continue
            # CSV-формат «MOVE,100,300» → «MOVE 100 300».
            if "," in line:
                line = " ".join(p.strip() for p in line.split(",") if p.strip())
            if line:
                commands.append(line)

        if not commands:
            self.append_log(f"[csv] {path}: нет команд для отправки", "err")
            return

        self.append_log(
            f"[csv] {path} → {len(commands)} cmd, выполнение по очереди",
            "ok",
        )
        self._queue.extend(commands)
        if self._pending is None:
            self._set_running(True)
            self._send_next()

    def _on_cancel(self) -> None:
        n_left = len(self._queue) + (1 if self._pending else 0)
        self._queue.clear()
        self._pending  = None
        self._wait_done = False
        self._set_running(False)
        self.append_log(f"[csv] отменено, в очереди было {n_left} cmd", "err")
        # Сам мотор глушим явно — иначе текущий MOVE доедет до цели сам.
        self.command_submitted.emit("STOP")

    # ---- queue internals ----------------------------------------------

    def _send_next(self) -> None:
        if not self._queue:
            self._pending = None
            self._wait_done = False
            self._set_running(False)
            self.append_log("[csv] очередь завершена", "ok")
            return
        cmd = self._queue.popleft()
        self._pending = cmd
        # MOVE требует !DONE; MOVETO пока stub в прошивке — обрабатываем как
        # обычную команду (сразу +ERR).
        upper_parts = cmd.upper().split()
        self._wait_done = bool(upper_parts) and upper_parts[0] == "MOVE"
        self.command_submitted.emit(cmd)

    def _advance(self) -> None:
        self._pending  = None
        self._wait_done = False
        self._send_next()

    def _set_running(self, running: bool) -> None:
        # Пока крутится очередь — повторная загрузка CSV запрещена,
        # активна кнопка CANCEL для ручного аборта.
        self.btn_add.setEnabled(not running)
        self.btn_cancel.setEnabled(running)
