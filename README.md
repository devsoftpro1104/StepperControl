# StepperControl

Управление шаговым двигателем на STM32F407 + хост-приложение на PyQt6.

См. [docs/architecture.md](docs/architecture.md) для архитектуры проекта.

## Состав
- `firmware/`  — прошивка STM32 (LL + FreeRTOS, CMake, arm-none-eabi-gcc)
- `software/` — хост-GUI (Python 3.11+, PyQt6)
- `shared/`    — единый источник правды по протоколу обмена
- `docs/`      — документация и ADR
- `tools/`     — скрипты CI/релиза
- `tests/`     — интеграционные тесты «прошивка ↔ хост»

## Сборка
```
cmake --preset firmware-debug
cmake --build --preset firmware-debug
```

## Хост
```
cd software
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements-dev.txt
python -m controller_app
```