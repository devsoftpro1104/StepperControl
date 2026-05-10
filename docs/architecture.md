# Архитектура проекта StepperControl

Документ описывает физический и логический состав репозитория: что лежит в каждой
директории, зачем она нужна, какие у неё границы ответственности и как разделы
связаны между собой. Документ — обязательное чтение перед первым PR в проект.

## 1. Контекст и цели

Проект разрабатывает связку «контроллер шагового двигателя на STM32F407 + хост-GUI
на Python / PySide6». Цели архитектуры:

- **Чёткое разделение слоёв.** Прикладной код прошивки не должен зависеть от
  конкретного семейства STM32, а UI хоста — от конкретного транспорта.
- **Единый источник правды по протоколу.** Прошивка и хост используют одну
  и ту же грамматику команд; рассинхронизация невозможна по построению.
  Сейчас канал — текстовый CLI ([cli.md](cli.md)); бинарный TLV из
  `shared/protocol/protocol.yaml` запланирован, но пока не задействован.
- **Тестируемость без железа.** Долгосрочная цель — слой моков для unit/
  integration-тестов на CI. На сегодня — заготовлена структура каталогов,
  тестов и моков ещё нет.
- **Воспроизводимая сборка.** Тулчейн ARM (CMake + arm-none-eabi-gcc),
  фиксированные версии third_party (FreeRTOS-Kernel, STM32CubeF4 V1.28.3),
  фиксированные версии Python-зависимостей в `software/requirements.txt`.

### Текущее состояние одной диаграммой

```
       UART2 (USART2 PA2/PA3, 115200 8N1)
           ▲                ▲
           │ shell-CLI      │ телеметрия $M, $T18, $H, $P, $D
           │
   ┌────────────────────┐                ┌─────────────────────────┐
   │  STM32F407         │                │  Хост (PySide6)         │
   │                    │                │                         │
   │  task_protocol     │                │  SerialWorker (QThread) │
   │      │             │                │      ↓                  │
   │  shell.c (cmd_*)   │                │  parser.py              │
   │      │             │                │      ↓                  │
   │  motor/temp/hall/  │                │  DeviceModel (state)    │
   │  probe_service     │                │      ↓                  │
   │      │             │                │  views (panels, charts) │
   │  drivers + devices │                │                         │
   │  + ISR + FreeRTOS  │                │                         │
   └────────────────────┘                └─────────────────────────┘
```

Минимум, что должен помнить читатель перед PR:

- Транспорт — **только текстовый CLI** через USART2, см. [cli.md](cli.md).
- Бинарный TLV (`shared/protocol/protocol.yaml`, `middleware/protocol/`) —
  запланирован, **в сборку не подключён**, диспетчера кадров ещё нет.
- Семь FreeRTOS-задач, четыре стрима `$X` (motor/temp/hall/probe) +
  событийные `!STATE/!DONE/!FAULT` — раскладка в [tasks.md](tasks.md).
- USB CDC, I²C, CAN, внешний EEPROM/ADS1115/TJA1051 — **не реализованы**;
  соответствующие пины свободны (см. [pinout.md](pinout.md)).

## 2. Карта верхнего уровня

```
project-root/
├── docs/        ← документация и ADR
├── shared/      ← кросс-проектные артефакты (протокол)
├── firmware/    ← прошивка STM32F407
├── software/    ← десктопное GUI (PyQt6)
├── tools/       ← вспомогательные скрипты сборки/релиза/CI
└── tests/       ← сквозные тесты «прошивка ↔ хост»
```

Каждое поддерево самодостаточно: его можно собирать и тестировать независимо.
Связь между `firmware/` и `software/` идёт **только** через `shared/protocol/`.

---

## 3. `docs/` — документация

Хранит долгоживущие проектные документы. Всё, что неизбежно станет неактуальным
через две недели, документу здесь не место — такие заметки живут в issues/PR.

| Файл                        | Назначение |
|-----------------------------|------------|
| `architecture.md`           | этот файл — карта проекта |
| `protocol.md`               | человекочитаемое описание бинарного протокола (источник правды — YAML в `shared/`) |
| `cli.md`                    | текстовый shell-протокол поверх UART (грамматика команд, стрим телеметрии, шаблон парсера на PySide6); реализация — `middleware/shell/` |
| `tasks.md`                  | FreeRTOS-задачи прошивки: приоритеты, стеки, периоды, шаблон task ↔ service |
| `pinout.md`                 | таблица «функция → пин MCU», синхронна с `bsp_pins.h` |
| `memory_map.md`             | разбиение FLASH/RAM, синхронно с linker-скриптом |
| `user_manual.md`            | как пользоваться GUI |
| `developer_setup.md`        | установка тулчейна, Python, сборка, прошивка |
| `adr/`                      | Architecture Decision Records |

### `docs/adr/`
ADR (Architecture Decision Record) фиксирует **почему** принято то или иное
архитектурное решение. ADR не правят задним числом — если решение поменялось,
заводят новый ADR, а старый помечают `Superseded by NNNN`. Это страховка
от потери контекста через год.

Уже принятые:
- `0001-use-ll-not-hal.md` — почему LL вместо HAL.
- `0002-freertos-cmsis-v2.md` — выбор RTOS и обёртки.
- `0003-protocol-binary-tlv.md` — формат протокола.
- `0004-pyqt6-not-pyqt5.md` — почему Qt6.

---

## 4. `shared/` — общие артефакты

### `shared/protocol/`
**Единый источник правды по протоколу обмена.** Здесь определены все команды,
их коды, поля запроса/ответа, форматы стримов телеметрии.

| Файл              | Назначение |
|-------------------|------------|
| `protocol.yaml`   | декларативное описание протокола |
| `generate_c.py`   | кодогенерация `protocol_gen.h` для прошивки |
| `generate_py.py`  | кодогенерация `messages.py` для хоста |
| `README.md`       | как добавлять новые команды и регенерировать артефакты |

Любое изменение `protocol.yaml` обязано сопровождаться **перегенерацией обоих
артефактов в одном коммите**. Это инвариант репозитория, проверяется CI.

---

## 5. `firmware/` — прошивка STM32F407

### 5.1. Корень `firmware/`

| Файл                   | Назначение |
|------------------------|------------|
| `CMakeLists.txt`       | корневой CMake-проект прошивки |
| `CMakePresets.json`    | пресеты `firmware-debug` / `firmware-release` |

### 5.2. `firmware/toolchain/`
`arm-none-eabi.cmake` — toolchain-файл CMake. Описывает кросс-компилятор
ARM GCC, флаги MCU (`-mcpu=cortex-m4 -mfpu=fpv4-sp-d16 -mfloat-abi=hard`).
Ничего, кроме настройки кросс-сборки, здесь быть не должно.

### 5.3. `firmware/linker/`
`stm32f407xx_flash.ld` — карта памяти и размещение секций. Должна быть
синхронна с `docs/memory_map.md`.

### 5.4. `firmware/third_party/`
Внешние компоненты, **не редактируются в нашем репозитории**, добавляются
как git-submodule или копией с фиксированной версией.

| Подпапка                       | Назначение |
|--------------------------------|------------|
| `CMSIS/`                       | CMSIS-Core (ARM) — заголовки для Cortex-M4F |
| `STM32CubeF4/`                 | CMSIS-Device STM32F4xx + LL-драйверы из STM32CubeF4 V1.28.3 |
| `FreeRTOS-Kernel/`             | ядро FreeRTOS, порт `GCC/ARM_CM4F`, `heap_4`, CMSIS-RTOS v2 |
| `STM32_USB_Device_Library/`    | ST USB Device Library (Core + класс CDC). **Сейчас не подключена**: USB CDC-драйвер не реализован, транспорт идёт через UART2. Оставлена для будущей активации (PLL_Q=7 → 48 МГц уже настроен в `bsp_clock.c`). |

Принцип: «своих правок в third_party нет». Если нужна правка — она лежит в
`hal_port/` или в виде патча в этой же папке с `*.patch`.

### 5.5. `firmware/src/` — исходный код прошивки

Слоистая архитектура, нижние слои не знают о верхних:

```
app
 └── middleware ──── hal_port ──── bsp ──── drivers ──── (LL/CMSIS/CubeF4)
        │                          │
        └── devices ───────────────┘
```

#### `firmware/src/app/` — прикладной слой
Конечный автомат приложения, FreeRTOS-задачи, *_service-модули. Не знает
о регистрах и пинах.

**Корень и общее состояние:**
- `inc/app_main.h` — точка входа `app_init()` / `app_run()`.
- `inc/app_state.h` — конечный автомат (`BOOT / IDLE / MOVING / FAULT`).
- `inc/app_events.h` — общий enum событий между задачами.
- `src/app_main.c`, `src/app_state.c` — реализация.
- `src/freertos_hooks.c` — хуки FreeRTOS (`vApplicationStackOverflowHook` и т.п.).

**Сервисы — состояние подсистем + тонкие GPIO-обёртки:**
Каждая подсистема имеет парный `*_service` со стандартными методами
`init/start/stop/running/period_ms/publish/get_last`. CLI-команды дёргают
сервис как «мост», задачи читают `running()`/`period_ms()` и публикуют
свежее значение через `publish()`.

| Сервис             | Файлы                                          | Что хранит / делает |
|--------------------|------------------------------------------------|---------------------|
| `temp_service`     | `inc/temp_service.h`, `src/temp_service.c`     | last `c10` от DS18B20 + флаг valid + период |
| `hall_service`     | `inc/hall_service.h`, `src/hall_service.c`     | last `raw/centered` от AH49E + период |
| `probe_service`    | `inc/probe_service.h`, `src/probe_service.c`   | last `freq_hz/adc` от STEP self-probe + период |
| `motor_service`    | `inc/motor_service.h`, `src/motor_service.c`   | `pos/target/speed_sps`, EN/DIR GPIO, оркестрация `MOVE` через `step_pwm` |

**FreeRTOS-задачи** (`src/tasks/`) — по одной задаче на ответственность.
Полная таблица (приоритеты, стеки, периоды, шаблон task ↔ service) —
в [tasks.md](tasks.md).

- `task_protocol.c` — приём байт из UART, кормит shell-парсер.
- `task_motor.c` — событийная: ждёт ISR-уведомление от `step_pwm`
  о завершении движения, синхронизирует позицию, шлёт `$M` и `!DONE MOVE`.
- `task_temp.c` — периодический опрос DS18B20, эмиссия `$T18`.
- `task_hall.c` — периодический опрос AH49E через ADC1, эмиссия `$H`.
- `task_probe.c` — самодиагностика STEP через ADC2 + DMA, эмиссия `$P`.
- `task_diagnostic.c` — LED-маяк 1 Гц (признак, что планировщик жив).
- `task_watchdog.c` — поддержка IWDG: разовая инициализация (LSI/32, таймаут ~1 с) + reload каждые 200 мс.

#### `firmware/src/bsp/` — Board Support Package
Знает про **конкретную плату**: тактовая 168 МГц от HSE, конкретные пины,
конкретная схема прерываний. Заменяемый на другой BSP при смене платы.

- `inc/bsp.h` — `bsp_init()`.
- `inc/bsp_pins.h` — единственное место, где описаны GPIO-пины. См. `pinout.md`.
- `inc/bsp_clock.h` — публичные функции инициализации тактирования.
- `inc/bsp_version.h` — версия прошивки (FW_VERSION_MAJOR/MINOR/PATCH).
- `src/bsp.c`, `bsp_clock.c` — реализация.
- `src/stm32f4xx_it.c` — таблица обработчиков прерываний (системные + периферия).

#### `firmware/src/drivers/` — драйверы периферии MCU
Тонкие обёртки над LL для каждой периферии: открыть/закрыть, дать колбэк/
очередь данных, изолировать DMA. **Не знают о бизнес-смысле** передаваемых
байтов.

| Подпапка     | Назначение |
|--------------|------------|
| `uart/`      | USART2 для текстового shell-CLI (TX через DMA1 Stream 6, RX через RXNE-IRQ → SPSC ring 256) |
| `step_pwm/`  | TIM1_CH1 (AF1, advanced timer) — аппаратный PWM для STEP на PA8; UEV-ISR считает шаги, по достижении target шлёт `xTaskNotifyFromISR` в task_motor |
| `adc/`       | ADC1 + DMA2 Stream 0, channel 1 (PA1) — непрерывное чтение AH49E в circular ring sample-buffer |
| `adc_probe/` | ADC2 + DMA2 Stream 2, channel 0 (PA0) — STEP self-probe loopback PA8→PA0; раздельное ядро ADC чтобы не мешать AH49E |
| `onewire/`   | 1-Wire master через GPIO bit-bang + DWT-микросекунды (для DS18B20 на PB12) |

> **Удалены как не используемые** (`can/`, `i2c/`, `spi/`, `timer/`, `gpio/`,
> `flash/`, `usb_cdc/`). Если такая периферия понадобится — соответствующие
> подпапки добавляются заново. См. [pinout.md](pinout.md) → раздел
> «Зарезервированные / в коде не используются».

#### `firmware/src/devices/` — драйверы внешних чипов
Используют `drivers/`, но добавляют логику конкретного устройства.

| Подпапка   | Устройство |
|------------|------------|
| `ah49e/`   | линейный аналоговый Hall-датчик AH49E (через `drivers/adc/`); подробно — [ah49e.md](ah49e.md) |
| `ds18b20/` | 1-Wire термосенсор Maxim/Dallas DS18B20 (через `drivers/onewire/`); подробно — [ds18b20.md](ds18b20.md) |

> **Удалены как не используемые** (`ads1115/`, `eeprom_24lc/`, `stepper/`,
> `tja1051/`). См. [tasks.md](tasks.md) и историю репозитория.

#### `firmware/src/middleware/` — переиспользуемые компоненты
Платформо-нейтральные модули, тестируются юнит-тестами без прошивания.

**Реально используются:**

| Подпапка    | Ответственность |
|-------------|-----------------|
| `shell/`    | текстовый CLI поверх UART2 (см. [cli.md](cli.md)) — диспетчер команд `PING/VER/STATE/MOVE/STOP/EN/DIR/MOTOR/TEMP/HALL/PROBE/HOME/MOVETO/HELP/RESET` |
| `protocol/` | заглушка под бинарный TLV: `protocol_parser.{h,c}` (структуры frame'а, статусы) и `protocol_gen.h` (артефакт кодогенерации). **В сборку не подключён** — диспетчер кадров ещё не написан, транспорт идёт через текстовый shell. |

**Заглушки** (только `.gitkeep` или резерв под будущую разработку):
`crc/`, `logger/`, `motion/`, `ring_buffer/`, `settings/`, `uds/`. Перечислены
в архитектуре как «куда пойдут модули, когда будут писаться»: переиспользуемый
кольцевой буфер, CRC-16/CCITT-FALSE, профилировщик движения и т.д.

`middleware/shell/` — **узаконенное исключение** из правила «middleware зовёт
только hal_port». По смыслу shell — диспетчер команд приложения, и он
напрямую вызывает `app/app_state`, все четыре `app/*_service`,
`devices/{ah49e,ds18b20}`, `drivers/{uart,adc_probe}`. Источник правды
по этому протоколу — [shell.h](../firmware/src/middleware/shell/inc/shell.h)
+ [docs/cli.md](cli.md), а **не** `shared/protocol/protocol.yaml` (там описан
другой, бинарный TLV-канал, ещё не задействованный).

#### `firmware/src/hal_port/`
Тонкая прослойка между прикладным/middleware-кодом и `drivers/LL`.
Сейчас представлена **только заголовком-стабом** [hal_port.h](../firmware/src/hal_port/inc/hal_port.h)
с интерфейсами `hal_uart_*` и `hal_tick_ms` — реализации (`hal_port.c`) пока
нет. Фактически `middleware/shell` обращается к `drivers/uart` и `app/*_service`
напрямую (см. оговорку выше). Когда абстракция реально потребуется (порт
на другую MCU или хост-симуляция) — `hal_port.c` напишется здесь же.

#### `firmware/src/config/`
Конфигурационные заголовки, выбранные именно для этого проекта:

- `FreeRTOSConfig.h` — приоритеты, тики, размер кучи RTOS (см. [tasks.md](tasks.md)).
- `stm32f4xx_ll_conf.h` — какие LL-модули включены (отрезаем неиспользуемые).
- `usbd_conf.h` — параметры USB Device middleware. **Сейчас не используется**, но оставлен на случай активации USB CDC; см. оговорку в `third_party/STM32_USB_Device_Library`.
- `project_config.h` — наши собственные параметры (`PROJ_MOTOR_MAX_SPEED_SPS` и т.п.).

#### `firmware/src/startup/`
- `startup_stm32f407xx.s` — таблица векторов и `Reset_Handler` (из CMSIS-Device).
- `system_stm32f4xx.c` — `SystemInit`, `SystemCoreClock`.
- `syscalls.c` — заглушки newlib (`_write`, `_read`, …) для линковки с `nosys.specs`.

### 5.6. `firmware/tests/unit/`
Юнит-тесты прошивки, собираются под **хост-компилятор** (без MCU). По одному
подкаталогу на тестируемый модуль: `ring_buffer/`, `crc/`, `protocol_parser/`,
`motion/`.

**Сейчас все четыре — пустые `.gitkeep`-каталоги**: модули-кандидаты
(`middleware/{ring_buffer,crc,motion}` + `protocol_parser`) ещё не написаны,
писать тесты не на что. Заполняются по мере появления реальных модулей.

Покрытие железа сюда не входит — это уровень `tests/integration/` сверху.

---

## 6. `software/` — десктопное GUI

PySide6-приложение, общается с прошивкой по UART (текстовый CLI из
[cli.md](cli.md)). Архитектура — **классический MVC**, источник правды
по слоям — [`software/MVC.md`](../software/MVC.md).

### 6.1. Корень `software/`

| Файл / папка       | Назначение |
|--------------------|------------|
| `run.py`           | точка входа: `python run.py` запускает GUI |
| `requirements.txt` | runtime-зависимости (PySide6, pyserial, pyqtgraph, numpy) |
| `README.md`        | быстрый старт, что умеет на сегодня |
| `MVC.md`           | подробная раскладка слоёв и поток данных |
| `controller_app/`  | пакет приложения |

### 6.2. `software/controller_app/` — пакет приложения

```
controller_app/
├── __main__.py            # python -m controller_app, wiring M / V / C
├── models/                ─── M ────────────────────────────
├── controllers/           ─── C ────────────────────────────
├── views/                 ─── V ────────────────────────────
└── resource/              ← статические ассеты (логотип и т.п.)
```

**Правила MVC** (формализованы в `MVC.md`):
- `models/` хранит состояние и общается с железом (парсер строк, коллекторы,
  serial-worker). **Не знает про Qt-виджеты.**
- `views/` показывает состояние и эмитит сигналы пользовательских действий.
  **Не знает про serial и парсер.**
- `controllers/` связывает первое со вторым. Только он знает обе стороны.

#### `controller_app/models/`
- `device_model.py` — `DeviceModel`: состояние подключения, лог, последний DUMP. Эмитит Qt-сигналы.
- `parser.py` — построчный диспетчер CLI (`+OK / -ERR / ! / # / $T18 / $H / $M / $P / $D`).
- `probe_collector.py` — собирает 4096-сэмпловый `PROBE DUMP` из `$D`-строк.
- `dump_snapshot.py` — datacclass для одного снимка DUMP.
- `log_severity.py` — теги для цветного лога.
- `serial_worker.py` — `pyserial` в `QThread` с неблокирующим чтением.

#### `controller_app/controllers/`
- `device_controller.py` — клей: SerialWorker → parser → DeviceModel; команды от UI → SerialWorker.

#### `controller_app/views/`
- `main_window.py` — собирает панели в layout.
- `panel.py` — общий базовый класс панелей.
- `connection_panel.py` — выбор COM-порта, Connect/Disconnect.
- `command_panel.py` — поле ввода CLI-команды + Send.
- `cli_control_panel.py` — кнопки фиксированных команд (PING, VER, MOVE, …).
- `log_panel.py` — цветной лог.
- `dump_chart.py`, `scope_chart.py` — графики waveform на `pyqtgraph`.
- `digital_readout.py`, `led.py`, `rotor_view.py` — индикаторные виджеты.
- `theme.py` — стили.
- `tabs/` — вкладки главного окна.

#### `controller_app/resource/`
- `izto_logo.png` — логотип.

### 6.3. Чего нет (по сравнению с «классической» структурой)

`software/tests/`, `software/packaging/`, `pyproject.toml`, `mypy.ini`,
`pytest.ini`, `ruff.toml`, отдельные слои `transport/` / `protocol/` /
`device/` / `workers/`, генерированные `messages.py` — **в проекте этого
сейчас нет**. Хост-приложение пока маленькое, отдельный кодек/транспорт-слой
не нужен (текстовый CLI парсится одним `parser.py`). Если разрастётся
до бинарного TLV-канала — слои добавятся, и тогда обновить этот раздел.

---

## 7. `tools/` — вспомогательная автоматизация

| Файл / папка        | Назначение |
|---------------------|------------|
| `flash_release.sh`  | прошивка релизного `.elf` через OpenOCD/ST-Link |
| `make_release.py`   | сборка релизного артефакта (firmware + host) с чексуммами |
| `ci/`               | конфиги/скрипты CI. **Сейчас пустой `.gitkeep`-каталог** — CI ещё не настроен, заглушка под workflows GitHub Actions / Jenkins. |

Это **не** часть продукта — это поддержка процесса разработки.

---

## 8. `tests/integration/` — сквозные тесты

Уровень выше `software/tests/integration/`: здесь тесты, которые запускают
**и хост, и реальную прошивку**, проверяя их совместимость.

- `conftest.py` — фикстуры (порт, таймауты).
- `test_handshake.py` — PING, GET_VERSION.
- `test_motor_control.py` — отправка команды движения и приём телеметрии.

По умолчанию помечены `pytest.skip()`, активируются по переменной окружения
`SC_TEST_PORT` или присутствию платы. На CI — на отдельном «hardware-in-the-loop»
раннере.

---

## 9. Сквозные правила

1. **Зависимости только сверху вниз.** Прикладной код прошивки не должен
   подключать `stm32f4xx.h` напрямую — только через `hal_port`. (На сегодня
   `hal_port` ещё стаб; пока правило соблюдается «по дисциплине», а не
   компилятором — см. §5.5 о `middleware/shell` как узаконенном исключении.)
   На хосте: views ничего не знают о serial-порте напрямую — только
   через controller.
2. **Один источник правды.** Пины — `bsp_pins.h`. Версия прошивки —
   `bsp_version.h`. Бинарный протокол — `shared/protocol/protocol.yaml`.
   Текстовый shell-протокол — [shell.h](../firmware/src/middleware/shell/inc/shell.h)
   плюс [docs/cli.md](cli.md). Карта памяти — linker-скрипт. FreeRTOS-задачи
   и сервисы — [tasks.md](tasks.md). Документация ссылается на эти источники,
   не дублирует их.
3. **Сначала тест, потом фича — для middleware/protocol/CRC**, когда они
   будут реализованы. Сейчас этих модулей в коде нет, тесты в `firmware/tests/unit/`
   и в `software/` — заглушки. Это запланированное состояние, а не действующая
   практика.
4. **Ничего лишнего в `third_party/`.** Сторонний код не правим. Если нужна
   правка — обёртка живёт в `hal_port/` или `middleware/`, а не в чужих исходниках.
5. **Кодогенерируемые файлы помечаются комментарием «НЕ РЕДАКТИРОВАТЬ ВРУЧНУЮ»**
   и регенерируются при изменении `protocol.yaml` в одном коммите с правкой YAML.
   (Сейчас актуально только для `middleware/protocol/inc/protocol_gen.h`,
   как только бинарный TLV-канал будет подключён к диспетчеру.)

## 10. Куда добавлять новый код

| Хочу добавить…                                  | Куда |
|--------------------------------------------------|------|
| новую CLI-команду (текстовый канал)              | обработчик `cmd_<x>` в [shell.c](../firmware/src/middleware/shell/src/shell.c), регистрация в `s_cmds[]`; описание в [cli.md](cli.md) и в `cmd_help()` |
| новую команду бинарного протокола (план)         | `shared/protocol/protocol.yaml` → регенерация → диспетчер во `firmware/src/middleware/protocol/` (когда будет написан) |
| новую FreeRTOS-задачу                            | `firmware/src/app/src/tasks/`; зарегистрировать в `app_main.c::app_run()`, добавить парный `*_service`, обновить [tasks.md](tasks.md) |
| новый сенсор / актуатор                          | `firmware/src/devices/<chip>/` (драйвер) + `firmware/src/app/{inc,src}/<x>_service.{h,c}` (состояние + CLI-glue) + `task_<x>.c` |
| новую периферию MCU                              | `firmware/src/drivers/<peripheral>/` (если удалена ранее как заглушка — пересоздать) |
| новый виджет/панель GUI                          | `software/controller_app/views/`; controller связывает с моделью |
| новую модель данных GUI                          | `software/controller_app/models/`; controller подписывается на её сигналы |
| решение, которое стоит зафиксировать «навсегда»  | новый ADR в `docs/adr/NNNN-...md` |
