# StepperControl

Контроллер шагового двигателя на STM32F407 + хост-GUI на Python / PySide6.
Связь — UART2 (115200 8N1), текстовый CLI-протокол.

## Состав репозитория

```
project-root/
├── docs/        ← документация и ADR
├── shared/      ← кросс-проектные артефакты (YAML-описание протокола)
├── firmware/    ← прошивка STM32F407 (CMake + arm-none-eabi-gcc)
├── software/    ← десктопное GUI (PySide6, MVC)
├── tools/       ← скрипты сборки/прошивки/релиза
└── tests/       ← сквозные тесты «прошивка ↔ хост»
```

Подробное описание каждой папки, слоёв прошивки и правил расширения — в
**[docs/architecture.md](docs/architecture.md)** (обязательное чтение перед
первым PR).

## Документация

| Файл                                           | О чём                                                                  |
|------------------------------------------------|------------------------------------------------------------------------|
| [docs/architecture.md](docs/architecture.md)   | Карта проекта: что в каких папках, границы ответственности, правила     |
| [docs/cli.md](docs/cli.md)                     | Текстовый CLI-протокол (грамматика команд, стримы `$M/$T18/$H/$P/$D`)  |
| [docs/tasks.md](docs/tasks.md)                 | FreeRTOS-задачи: приоритеты, стеки, периоды, шаблон task ↔ service     |
| [docs/clocks.md](docs/clocks.md)               | Тактирование, частоты шин, карта периферии                              |
| [docs/pinout.md](docs/pinout.md)               | Карта выводов MCU                                                       |
| [docs/memory_map.md](docs/memory_map.md)       | Карта FLASH/RAM, синхронна с linker-скриптом                            |
| [docs/motor.md](docs/motor.md)                 | STEP/DIR/EN, TIM1 PWM, асинхронная схема `MOVE`                         |
| [docs/probe.md](docs/probe.md)                 | Самодиагностика STEP через ADC2 (PA8↔PA0 перемычка)                     |
| [docs/ah49e.md](docs/ah49e.md)                 | Линейный Hall AH49E через ADC1                                          |
| [docs/ds18b20.md](docs/ds18b20.md)             | Термосенсор DS18B20, 1-Wire bit-bang                                    |
| [docs/watchdog.md](docs/watchdog.md)           | IWDG: параметры, расчёт запаса, отладка под JTAG                        |
| [docs/protocol.md](docs/protocol.md)           | Заметка про бинарный TLV-канал (план, не задействован)                  |
| [docs/developer_setup.md](docs/developer_setup.md) | Установка тулчейна и сборка                                          |
| [docs/user_manual.md](docs/user_manual.md)     | Как пользоваться GUI                                                    |
| [docs/adr/](docs/adr/)                         | Architecture Decision Records (LL vs HAL, FreeRTOS, Qt6, …)             |

## Быстрый старт

**Прошивка** — см. [docs/developer_setup.md](docs/developer_setup.md).
**Хост-GUI** — см. [software/README.md](software/README.md).
