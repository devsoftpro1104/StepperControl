# StepperControl host

GUI на PySide6 для общения с прошивкой по UART (CLI-протокол).

## Установка

```bash
cd software
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac
pip install -r requirements.txt
```

Требуется Python ≥ 3.10.

## Запуск

```bash
python -m controller_app
```

В UI:
1. Выбери COM-порт в выпадающем списке (`Refresh` обновляет).
2. Жми `Connect` — появится текстовый лог с входящими строками.
3. Внизу — поле команды, по `Enter` уходит в MCU с CRLF.
4. Кнопка `PROBE DUMP` — отправляет команду и рисует waveform на графике.

## Что сейчас умеет

- Транспорт `pyserial` в отдельном `QThread`, неблокирующий чтение.
- Парсер строк: `+OK`, `-ERR`, `!event`, `#comment`, `$T18`, `$H`, `$M`, `$P`, `$D`.
- Сборщик `PROBE DUMP` — собирает 4096 семплов и плоттит на `pyqtgraph`.
- Цветной лог.

Не умеет (намеренно — добавляется по мере надобности):
- Графики `$T18` / `$H` / `$M` / `$P` в реальном времени.
- Сохранение/загрузку настроек.
- Бинарный TLV-протокол (см. `docs/protocol.md` в корне репо).

## Структура

```
software/
├── requirements.txt
├── README.md
└── controller_app/
    ├── __init__.py
    ├── __main__.py            # python -m controller_app
    ├── parser.py              # построчный диспетчер CLI
    ├── probe_collector.py     # сборка $D-дампов
    ├── serial_worker.py       # pyserial в QThread
    └── main_window.py         # Qt UI
```
