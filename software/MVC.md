# MVC-архитектура хост-приложения

Документ описывает раскладку и правила взаимодействия трёх слоёв
(`controller_app/models`, `controller_app/controllers`, `controller_app/views`).

## Зачем MVC

UART-протокол MCU будет разрастаться (новые команды, новые `$`-стримы,
новые панели в UI). Без слоёв это превращается в один большой
`main_window.py` с `if isinstance(evt, ...)` посреди разметки. Чтобы
этого не случилось, ввели жёсткое разделение:

- **Model** хранит **что есть** (состояние) и **что приходит из железа**
  (парсер, коллекторы, транспорт). Не знает про Qt-виджеты.
- **View** показывает состояние пользователю и эмитит сигналы о его
  действиях. Не знает про serial, парсер и dump-сборщик.
- **Controller** связывает первое со вторым. Только он знает обе стороны.

## Раскладка файлов

```
software/
├── run.py                          ← точка входа (открыть, нажать ▷)
└── controller_app/
    ├── __init__.py
    ├── __main__.py                 ← wiring M / V / C
    │
    ├── models/                     ─── M ─────────────────────────────
    │   ├── __init__.py             ← re-export всего публичного
    │   ├── device_model.py         ← DeviceModel (state + Qt-сигналы)
    │   ├── dump_snapshot.py        ← DumpSnapshot (один PROBE DUMP)
    │   ├── log_severity.py         ← LogSeverity (теги-строки)
    │   ├── parser.py               ← CLI-строки → события
    │   ├── probe_collector.py      ← сборка $D-снимка
    │   └── serial_worker.py        ← pyserial в QThread
    │
    ├── controllers/                ─── C ─────────────────────────────
    │   ├── __init__.py
    │   └── device_controller.py    ← клей: транспорт/парсер → model
    │
    └── views/                      ─── V ─────────────────────────────
        ├── __init__.py
        ├── main_window.py          ← собирает панели в layout
        ├── connection_panel.py     ← порт + Connect/Disconnect/DUMP
        ├── log_panel.py            ← цветной лог (severity → QColor)
        ├── command_panel.py        ← QLineEdit + Send
        └── plot_panel.py           ← pyqtgraph waveform
```

## Поток данных

```
─── входящий поток ────────────────────────────────────────────────────
  UART bytes
    │
    ▼
  SerialWorker            (models/serial_worker.py, QThread)
    │ line_received(str)
    ▼
  DeviceController._on_line                             ← C
    │
    ├─ parse_line(line)   (models/parser.py)            ← M (pure)
    │
    ├─ ProbeDumpCollector.feed_*  (models/probe_collector.py)
    │
    └─ DeviceModel.append_log / set_dump / set_connection
                                                        ← M (state)
         │ log_appended / dump_completed / connection_changed
         ▼
       LogPanel.append_line / PlotPanel.show_dump / MainWindow.set_connected
                                                        ← V

─── действие пользователя ────────────────────────────────────────────
  click / Enter
    │
    ▼
  ConnectionPanel / CommandPanel                        ← V
    │ connect_requested(port) / command_submitted(cmd) / dump_requested()
    ▼
  MainWindow re-emit
    │
    ▼
  DeviceController.connect_to / send_command / request_probe_dump   ← C
    │
    ▼
  SerialWorker.write_line                               ← M
    │
    ▼
  UART bytes
```

## Правила импортов

| Слой | Кому может импортировать | Кому НЕ может |
|------|---------------------------|---------------|
| `models/`      | `models/*` (внутри)              | `views/`, `controllers/` |
| `controllers/` | `models/*`                       | `views/` |
| `views/`       | `views/*` (внутри), Qt           | `models/`, `controllers/` |
| `__main__.py`  | всё (там точка сборки)           | — |

Если эти стрелки нарушены — слой стал «знать» лишнего и MVC
сломалось. Это самое важное правило файла.

Конкретные следствия:

- **Модель не импортит `QtWidgets` / `pyqtgraph`** — только `QtCore`
  ради `QObject`/`Signal`. Цвета severity живут в `views/log_panel.py`,
  не в модели.
- **View не парсит строки.** Получает только готовый `(text, severity)`
  и `DumpSnapshot`. Не знает, что пришло по UART.
- **Контроллер не лазает в виджеты.** Пишет в model, view сам обновится.

## Сигнатуры центральных контрактов

### DeviceModel (`models/device_model.py`)

Эмитит:
```python
connection_changed = Signal(bool, str)          # connected, port
log_appended       = Signal(str, str)           # text, severity
dump_completed     = Signal(object)             # DumpSnapshot
```

Принимает (вызывает контроллер):
```python
set_connection(connected: bool, port: str = "") -> None
append_log(text: str, severity: str = LogSeverity.RAW) -> None
set_dump(snap: DumpSnapshot) -> None
```

### MainWindow (`views/main_window.py`)

Эмитит наружу (для контроллера):
```python
connect_requested    = Signal(str)              # port
disconnect_requested = Signal()
dump_requested       = Signal()
command_submitted    = Signal(str)
```

Слот:
```python
set_connected(connected: bool) -> None
```

Под-панели в нём (`connection`, `log`, `command`, `plot`) тоже видны
снаружи — `__main__.py` подписывает `model.log_appended →
view.log.append_line` и `model.dump_completed → view.plot.show_dump`
напрямую.

### DeviceController (`controllers/device_controller.py`)

Слоты для view-сигналов:
```python
@Slot(str) connect_to(port)
@Slot()    disconnect()
@Slot(str) send_command(cmd)
@Slot()    request_probe_dump()
shutdown()                  # вызывается из app.aboutToQuit
```

## Wiring (`__main__.py`)

```python
model      = DeviceModel()
view       = MainWindow()
controller = DeviceController(model)

# model -> view
model.connection_changed.connect(lambda c, _p: view.set_connected(c))
model.log_appended.connect(view.log.append_line)
model.dump_completed.connect(lambda s: view.plot.show_dump(s.samples, s.sample_hz))

# view -> controller
view.connect_requested.connect(controller.connect_to)
view.disconnect_requested.connect(controller.disconnect)
view.dump_requested.connect(controller.request_probe_dump)
view.command_submitted.connect(controller.send_command)

app.aboutToQuit.connect(controller.shutdown)
```

Это **единственное место** где знают друг о друге все три слоя.

## Как добавить фичу

### Новая команда без UI (например, PING по таймеру)

1. Добавить слот в `DeviceController`:
   ```python
   @Slot()
   def ping(self) -> None:
       self.send_command("PING")
   ```
2. Подписать его в `__main__.py` на нужный сигнал (QTimer / кнопка).

Изменений в model и view — ноль.

### Новая кнопка в существующей панели

1. В `views/connection_panel.py` (или другой):
   ```python
   self.btn_ping = QPushButton("Ping")
   self.btn_ping.clicked.connect(self.ping_requested)
   row.addWidget(self.btn_ping)
   ```
2. Объявить сигнал `ping_requested = Signal()`.
3. Пробросить в `MainWindow` (re-emit) и в `__main__.py` подписать на
   `controller.ping`.

### Новая панель с новой функциональностью (например, motor control)

1. Создать `views/motor_panel.py` с виджетами и сигналами `motor_on_requested`, `motor_dir_changed(int)`, `motor_speed_changed(int)`...
2. Добавить её в `MainWindow.__init__`:
   ```python
   self.motor = MotorPanel()
   layout.addWidget(self.motor)
   ```
3. Re-emit-нуть нужные сигналы наружу из `MainWindow` (или подписать
   в `__main__.py` напрямую через `view.motor.motor_on_requested`).
4. В `DeviceController` добавить слоты-команды.
5. В `__main__.py` соединить.

### Новая телеметрия из MCU (живой график, например, $T18)

1. В `models/parser.py` уже есть `TempSample` — он парсится. Если новый
   стрим — добавить regex и dataclass там.
2. В `models/device_model.py` — новый сигнал и сеттер:
   ```python
   temp_received = Signal(float, int)          # temp_c, ts_ms
   def push_temp(self, temp_c: float, ts_ms: int) -> None:
       self.temp_received.emit(temp_c, ts_ms)
   ```
3. В `controllers/device_controller.py._on_line` — обработать
   `TempSample`:
   ```python
   if isinstance(evt, TempSample):
       self._model.push_temp(evt.temp_c, evt.ts_ms)
       return
   ```
4. В `views/temp_panel.py` — новая панель с pyqtgraph rolling-плотом и
   слотом `on_temp(temp_c, ts_ms)`.
5. В `__main__.py`: `model.temp_received.connect(view.temp.on_temp)`.

В каждом слое — точечное изменение, остальные не трогаются.

## Запуск

- VS Code: открыть [run.py](run.py) → ▷ «Run Python File».
- Терминал: `cd software && .venv\Scripts\python.exe -m controller_app`.

## Что осталось вне MVC (намеренно)

- **Бинарный протокол** — когда добавится, появится `models/protocol_binary.py`
  рядом с `parser.py`. Контроллер выбирает, какой парсер использовать.
- **Сохранение настроек** — `models/settings.py` (QSettings обёртка) +
  слот в контроллере на `app.aboutToQuit`.
- **Тесты** — `tests/` отдельно. Парсер и `ProbeDumpCollector`
  тестируются без Qt; модель — с `pytest-qt` (sigspy на `log_appended`,
  `dump_completed`); контроллер — с фейковым SerialWorker.
