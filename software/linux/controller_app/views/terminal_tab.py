"""Вкладка ТЕРМИНАЛ: цветной лог + ввод команды + ADD/CANCEL/CLEAR.

Лог тут — единственное окно, куда падают `+OK` / `-ERR` / `!event` /
комментарии и неизвестные строки. Высокочастотные стримы ($M, $T18, $H, $P)
сюда не пишутся (они визуализируются на других вкладках) — иначе при
50–100 Hz терминал перегружается.

Кнопка ADD открывает file-picker для .csv с командами (g-code-подобный
формат). Команды выполняются строго по очереди: следующая отправляется
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

from kivy.uix.boxlayout import BoxLayout

from .file_picker import CsvFilePicker
from .log_panel import LogPanel
from .panel import Panel
from .widgets import IndustrialButton, IndustrialTextInput


class TerminalTab(BoxLayout):
    __events__ = ("on_command_submitted",)

    def __init__(self, **kwargs) -> None:
        super().__init__(orientation="vertical", padding=12, spacing=10, **kwargs)
        self._enabled = False

        # ---- LOG panel ----
        log_panel = Panel("LOG", size_hint_y=1)
        self.log = LogPanel()
        log_panel.add_widget(self.log)
        self.add_widget(log_panel)

        # ---- COMMAND panel ----
        cmd_panel = Panel("COMMAND", size_hint_y=None)
        cmd_panel.height = 20 + 24 + 40 + 10

        cmd_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None, height="40dp",
            spacing=8,
        )

        self.ti_cmd = IndustrialTextInput(
            hint_text="введи команду и нажми Enter (например: PING)",
            size_hint_x=1,
        )
        self.ti_cmd.bind(on_text_validate=lambda _ti: self._submit_manual())

        self.btn_send = IndustrialButton(
            text="SEND", size_hint_x=None, width="100dp",
        )
        self.btn_send.bind(on_release=lambda _b: self._submit_manual())

        self.btn_add = IndustrialButton(
            text="ADD", size_hint_x=None, width="100dp",
        )
        self.btn_add.bind(on_release=lambda _b: self._on_add())

        self.btn_cancel = IndustrialButton(
            text="CANCEL", size_hint_x=None, width="100dp",
        )
        self.btn_cancel.bind(on_release=lambda _b: self._on_cancel())
        self.btn_cancel.disabled = True   # активна только во время очереди

        self.btn_clear = IndustrialButton(
            text="CLEAR", size_hint_x=None, width="100dp",
        )
        self.btn_clear.bind(on_release=lambda _b: self.log.clear())

        cmd_row.add_widget(self.ti_cmd)
        cmd_row.add_widget(self.btn_send)
        cmd_row.add_widget(self.btn_add)
        cmd_row.add_widget(self.btn_cancel)
        cmd_row.add_widget(self.btn_clear)

        cmd_panel.add_widget(cmd_row)
        self.add_widget(cmd_panel)

        self._set_input_enabled(False)

        # ---- очередь CSV-команд ----
        self._queue:    deque[str]    = deque()
        self._pending:  Optional[str] = None    # отправленная, ждём подтверждения
        self._wait_done: bool         = False   # для MOVE — ждать !DONE MOVE

    # ---- API из MainApp -------------------------------------------------

    def append_log(self, text: str, severity: str = "raw") -> None:
        self.log.append_line(text, severity)

    def set_connected(self, connected: bool) -> None:
        self._set_input_enabled(connected)
        if not connected:
            # Подключение оборвалось — очистить очередь, чтобы при ре-коннекте
            # старые команды не «доехали».
            self._queue.clear()
            self._pending  = None
            self._wait_done = False
            self._set_running(False)

    # ---- слоты для ответов прошивки (зовутся из app.py через model.bind)

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

    # ---- internals ------------------------------------------------------

    def _set_input_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        # Когда очередь крутится — manual-инпут заблокирован независимо от
        # connected. _set_running накладывает свой disabled поверх этого.
        self.ti_cmd.disabled   = not enabled
        self.btn_send.disabled = not enabled
        self.btn_add.disabled  = not enabled

    def _submit_manual(self) -> None:
        if not self._enabled or self._pending is not None:
            return
        cmd = self.ti_cmd.text.strip()
        if not cmd:
            return
        self.dispatch("on_command_submitted", cmd)
        self.ti_cmd.text = ""

    # ---- CSV loader -----------------------------------------------------

    def _on_add(self) -> None:
        if self._pending is not None or not self._enabled:
            return
        CsvFilePicker.open_for(self._on_csv_picked)

    def _on_csv_picked(self, path: Optional[str]) -> None:
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
        self.dispatch("on_command_submitted", "STOP")

    # ---- queue internals ------------------------------------------------

    def _send_next(self) -> None:
        if not self._queue:
            self._pending   = None
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
        self.dispatch("on_command_submitted", cmd)

    def _advance(self) -> None:
        self._pending  = None
        self._wait_done = False
        self._send_next()

    def _set_running(self, running: bool) -> None:
        # Пока крутится очередь — повторная загрузка CSV запрещена,
        # активна кнопка CANCEL для ручного аборта; manual-ввод тоже
        # запрещён (иначе чужой `+OK` сломает state-machine).
        self.btn_add.disabled    = running or not self._enabled
        self.btn_cancel.disabled = not running
        self.ti_cmd.disabled     = running or not self._enabled
        self.btn_send.disabled   = running or not self._enabled

    def on_command_submitted(self, *_a, **_k) -> None: ...
