# StepperControl host — Kivy-версия

Линуксовая версия GUI на **Kivy** поверх UART CLI-протокола MCU. Параллельная
ветка PySide6-приложения из [../controller_app/](../controller_app/), та же
архитектура MVC, тот же парсер CLI-строк, та же логика транспорта.

## Что входит в MVP

- Вкладка **CONNECTION** — выбор COM-порта, Refresh, Connect/Disconnect.
- Вкладка **TERMINAL** — цветной лог (`+OK` / `-ERR` / `!event` / комментарии),
  ввод команды по Enter, кнопка CLEAR.
- Header с индикатором ONLINE/OFFLINE и именем порта.

Намеренно **не входит** в MVP (есть в PySide6-версии):

- Вкладка **MOTOR** (анимированный ротор + DRO + scope).
- Вкладка **SENSORS** (rolling-графики TEMP/HALL + waveform PROBE DUMP).
- CSV-очередь команд во вкладке TERMINAL с ожиданием `!DONE MOVE`.
- Панель CLI-команд во вкладке CONNECTION (готовый набор кнопок).

Графики, когда будут добавлены, нарисованы через `kivy_garden.graph` —
зависимость уже в [requirements.txt](requirements.txt).

## Установка

```bash
cd software/linux
python -m venv .venv
source .venv/bin/activate           # Linux/Mac
# .venv\Scripts\activate            # Windows
pip install -r requirements.txt
```

Требуется Python ≥ 3.10.

## Запуск

```bash
python run.py
# или
python -m controller_app
```

## Структура

```
software/linux/
├── README.md
├── requirements.txt
├── run.py                          ← точка входа
└── controller_app/
    ├── __init__.py
    ├── __main__.py                 ← wiring M / V / C
    │
    ├── models/                     ─── M ─────────────────────────────
    │   ├── __init__.py
    │   ├── device_model.py         ← DeviceModel (state + Kivy events)
    │   ├── log_severity.py         ← LogSeverity (теги-строки)
    │   ├── parser.py               ← CLI-строки → события (pure-python)
    │   └── serial_worker.py        ← pyserial в threading.Thread
    │
    ├── controllers/                ─── C ─────────────────────────────
    │   ├── __init__.py
    │   └── device_controller.py    ← клей: транспорт/парсер → model
    │
    └── views/                      ─── V ─────────────────────────────
        ├── __init__.py
        ├── app.py                  ← StepperControlApp + MainView + Header
        ├── connect_tab.py          ← порт + Connect/Disconnect
        ├── terminal_tab.py         ← log + raw command-line
        ├── log_panel.py            ← цветной лог через Label markup
        └── theme.py                ← палитра + severity → hex
```

## Отличия от PySide6-версии

| | PySide6 | Kivy |
|---|---|---|
| Сигналы model | `Signal(...)` | `__events__` + `dispatch(...)` |
| Транспорт | `QThread` + сигнал | `threading.Thread` + колбэки |
| Маршалинг с фонового потока | автоматически (queued connection) | `Clock.schedule_once(...)` в `DeviceController._post_*` |
| Список COM-портов | `serial.tools.list_ports` | то же |
| Парсер | [parser.py](../controller_app/models/parser.py) | копия |
| Лог | `QTextEdit` + `QTextCharFormat` | `Label(markup=True)` в `ScrollView` |
| Графики | `pyqtgraph` | (план) `kivy_garden.graph` |

## Как добавить фичу

Все три слоя независимы — расширение точечное:

- **Новая команда без UI** (например, PING по таймеру) — добавить метод в
  `DeviceController`, в `__main__.py` подписать на нужный триггер
  (`Clock.schedule_interval` / кнопка).
- **Новая кнопка в существующей вкладке** — добавить `Button` в нужный
  `*_tab.py`, эмитить новое kivy-событие, в `__main__.py` подписать его
  на метод контроллера.
- **Новая телеметрия из MCU** (живой график TEMP/HALL) — событие в
  `DeviceModel` (`__events__`) уже есть для всех стримов; нужно только
  добавить вкладку и подписать `model.bind(on_temp_sample_received=...)`.
