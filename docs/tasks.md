# FreeRTOS-задачи прошивки

Документ описывает FreeRTOS-задачи приложения: где они создаются, их приоритеты,
размеры стеков, периоды, способ взаимодействия с сервисами и shell.

Источник правды по коду:
- создание задач — [`firmware/src/app/src/app_main.c`](../firmware/src/app/src/app_main.c)
- сами задачи — [`firmware/src/app/src/tasks/`](../firmware/src/app/src/tasks/)
- параметры RTOS — [`firmware/src/config/FreeRTOSConfig.h`](../firmware/src/config/FreeRTOSConfig.h)

Контекст выбора RTOS — в [`adr/0002-freertos-cmsis-v2.md`](adr/0002-freertos-cmsis-v2.md).

---

## 1. Параметры планировщика

Из [`FreeRTOSConfig.h`](../firmware/src/config/FreeRTOSConfig.h):

| Параметр                              | Значение         |
|---------------------------------------|------------------|
| `configCPU_CLOCK_HZ`                  | 168 МГц          |
| `configTICK_RATE_HZ`                  | 1000 Гц (тик 1 мс) |
| `configMAX_PRIORITIES`                | 56 (mapping CMSIS-RTOS v2) |
| `configTOTAL_HEAP_SIZE`               | 24 КБ, аллокатор `heap_4` |
| `configUSE_PREEMPTION`                | 1                |
| `configUSE_TIME_SLICING`              | 1                |
| `configCHECK_FOR_STACK_OVERFLOW`      | 2 (метод сравнения «канарейки») |
| `configUSE_MALLOC_FAILED_HOOK`        | 1                |
| `configTIMER_TASK_PRIORITY`           | 2                |
| `configSUPPORT_DYNAMIC_ALLOCATION`    | 1                |
| `configSUPPORT_STATIC_ALLOCATION`     | 0                |

CMSIS-v2 mapping приоритетов (то, что мы реально используем):

| `osPriority…`        | Числовое значение |
|----------------------|-------------------|
| `osPriorityIdle`     | 1                 |
| `osPriorityNormal`   | 24                |
| `osPriorityAboveNormal` | 32             |
| `osPriorityISR`      | 56                |

Скрытые задачи, которые стартуют автоматически и в `task_*` не описаны:
- **Idle** (приоритет 0) — встроена в FreeRTOS.
- **Timer Service** — `configTIMER_TASK_PRIORITY = 2`. Сейчас не используется
  (все периодические задачи реализованы вручную через `osDelay`).

---

## 2. Где создаются задачи

В [`app_main.c`](../firmware/src/app/src/app_main.c), функция `app_run()`:

1. `osKernelInitialize()` — инициализация ядра.
2. `osThreadNew(task_*, NULL, &attr)` для каждой задачи (см. таблицу ниже).
3. `app_state_set(APP_STATE_IDLE)` — переход в рабочее состояние.
4. `osKernelStart()` — точка, после которой управление в `main()` не возвращается.

Каждый `osThreadNew` принимает `osThreadAttr_t` со своим именем, приоритетом
и размером стека. Базовый шаблон:

```c
static const osThreadAttr_t s_attr_default = {
    .name       = "default",
    .stack_size = 512,
    .priority   = osPriorityNormal,
};
```

Под каждую задачу копия `s_attr_default` патчится `name`/`stack_size`/`priority`.

---

## 3. Таблица задач

| Задача      | Файл                                                                       | Приоритет     | Стек, байт | Триггер цикла                          |
|-------------|----------------------------------------------------------------------------|---------------|-----------:|----------------------------------------|
| `protocol`  | [`task_protocol.c`](../firmware/src/app/src/tasks/task_protocol.c)         | Normal        |       2048 | `osDelay(2 ms)` если RX пуст           |
| `motor`     | [`task_motor.c`](../firmware/src/app/src/tasks/task_motor.c)               | **AboveNormal** |     1024 | `ulTaskNotifyTake()` (ISR `step_pwm`)  |
| `temp`      | [`task_temp.c`](../firmware/src/app/src/tasks/task_temp.c)                 | Normal        |       1024 | `period_ms` сервиса (мин ~760 мс)      |
| `hall`      | [`task_hall.c`](../firmware/src/app/src/tasks/task_hall.c)                 | Normal        |       1024 | `period_ms` сервиса (10..60000 мс)     |
| `probe`     | [`task_probe.c`](../firmware/src/app/src/tasks/task_probe.c)               | Normal        |       1024 | `period_ms` сервиса (через `PROBE RATE`) |
| `diag`      | [`task_diagnostic.c`](../firmware/src/app/src/tasks/task_diagnostic.c)     | Normal        |        256 | `osDelay(500 ms)`                      |
| `wdg`       | [`task_watchdog.c`](../firmware/src/app/src/tasks/task_watchdog.c)         | Normal        |        256 | `osDelay(200 ms)` + `LL_IWDG_ReloadCounter` |

### 3.1. Чем заняты задачи

#### `protocol` — текстовый shell поверх UART2
- Опустошает RX-кольцо `uart2_rx_get()` и кормит байты `shell_feed()`.
- Если RX пуст — `osDelay(2 мс)`. При 115200 baud за 2 мс прилетает ≤24 байт,
  256-байтовое кольцо переполниться не успевает.
- Стек 2048 — запас под `vsnprintf` (newlib-nano ≈ 400 байт) при выводе
  длинных команд (например, `PROBE DUMP`).
- Бинарный TLV-фрейм-протокол (см. [`protocol.md`](protocol.md)) пока не
  реализован — будет добавлен поверх того же транспорта.

#### `motor` — оркестрация шагового двигателя
- Регистрирует себя как «owner» в `motor_service` (`motor_service_register_owner(...)`).
  ISR `step_pwm` шлёт `xTaskNotifyFromISR(...)`, когда счётчик шагов достиг target.
- В цикле `ulTaskNotifyTake()` с таймаутом = периодом телеметрии
  (`motor_service_period_ms()`), либо `IDLE_POLL_MS = 200 мс`, если телеметрия выключена.
- На каждом тике подтягивает позицию из счётчика PWM
  (`motor_service_sync_position_from_pwm()`).
- При нотификации от ISR — финализирует движение: `APP_STATE_MOVING → IDLE`,
  эмиссия `STATE IDLE` и `DONE MOVE`.
- Если телеметрия активна — шлёт строку `$M, <ts>, <pos>, <sps>, <target>, <en>, <dir>`.
- **Почему AboveNormal**: гарантирует, что финализация движения и `!DONE MOVE`
  не запаздывают за конкурирующими `temp/hall/probe`-стримами.
- Профиль скорости (трапеция/S-curve) — TBD. Сейчас движение на постоянной скорости,
  аргумент `accel` в `MOVE` принимается, но игнорируется (см. [`motor.md`](motor.md)).

#### `temp` — опрос DS18B20
- Управление через CLI: `TEMP ON | TEMP OFF | TEMP RATE <hz> | TEMP READ`
  (см. [`shell.h`](../firmware/src/middleware/shell/inc/shell.h),
  [`cli.md`](cli.md), [`ds18b20.md`](ds18b20.md)).
- Если опрос выключен — `osDelay(IDLE_POLL_MS = 200 мс)` для быстрой реакции на `TEMP ON`.
- Если включён — `ds18b20_read_blocking()` блокируется на ~760 мс
  (12-битная конвертация DS18B20). Это нижняя граница периода.
- При успехе — публикация в `temp_service`, эмиссия `$T18, <ts>, <c10>`.
- При ошибке — `temp_service_invalidate()` без спама `!FAULT` в UART
  (хост видит «нет $T18» — этого достаточно).

#### `hall` — опрос AH49E через ADC1 + DMA-circular
- Управление через CLI: `HALL START | HALL STOP | HALL PERIOD <ms> | HALL READ | HALL ZERO`
  (см. [`ah49e.md`](ah49e.md)).
- Чтение ADC мгновенное (значение всегда в DMA-кольце). Задача в основном спит.
- Эмиссия `$H, <ts>, <raw>, <centered>`.

#### `probe` — самодиагностика STEP через ADC2 + DMA2
- Управление через CLI: `PROBE ON | PROBE OFF | PROBE RATE <ms> | PROBE READ`
  (см. [`probe.md`](probe.md)).
- На каждом тике вычитывает ring-буфер `adc_probe`, считает статистику:
  частоту по пересечениям порога, duty, vmin/vmax (~5 мс CPU на проход 4096 сэмплов).
- Эмиссия `$P, <ts>, <freq_hz>, <adc>`.

#### `diag` — индикация «жив-не жив»
- `LL_GPIO_TogglePin(PIN_LED_STATUS_*, ...)` каждые 500 мс → blink 1 Гц.
- Никаких блокирующих вызовов, `snprintf` нет → стек 256 байт.

#### `wdg` — поддержка IWDG
- При старте: `LL_IWDG_Enable` → write access → prescaler `/32`, reload `1000`
  (LSI ≈ 32 кГц → тик 1 мс, таймаут ~1 с) → ждём `LL_IWDG_IsReady` → первый reload.
- В цикле: `LL_IWDG_ReloadCounter(IWDG)` каждые 200 мс — пятикратный запас по
  таймауту. Если RTOS зависнет / `wdg`-задача не получит CPU дольше ~1 с —
  IWDG ресетнёт МК.

---

## 4. Шаблон «task ↔ service ↔ shell»

Для всех периодических задач (`temp`, `hall`, `probe`) шаблон одинаковый:

```
   CLI команда             flag            железо               UART
  ──────────────►  *_service ─────►  task_*  ─────►  *_service  ─────►  $X-стрим
   (HALL START)    (running=1)       (poll)         (publish)          ($H,...)
```

1. Команда CLI (`HALL START`, `TEMP ON`, …) дёргает `*_service_start()` —
   это просто установка флага и/или периода.
2. Задача в `for(;;)`:
   - если `*_service_running()` — читает железо, публикует значение в сервис,
     шлёт строку `$X` в UART;
   - иначе — `osDelay(IDLE_POLL_MS = 200 мс)`.
3. Сервис хранит последнее значение и период. Хост может опросить разово
   через CLI (`TEMP READ`, `HALL READ`, …) без рестарта потока.

`task_motor` живёт по другой схеме — **событийная**, через `xTaskNotify`
от ISR `step_pwm`, а не периодическая.

Конкуренция за UART2 решается тем, что `uart2_send()` ставит байты
в TX-кольцо без блокировок (lock-free).

---

## 5. Что менять при добавлении новой задачи

1. Создать `firmware/src/app/src/tasks/task_<name>.c`.
   Объявить `void task_<name>(void *argument);`.
2. В [`app_main.c`](../firmware/src/app/src/app_main.c):
   - добавить `extern void task_<name>(void *argument);`;
   - в `app_run()` — `osThreadNew(task_<name>, NULL, &a)` с подобранным
     приоритетом и стеком.
3. Если задача периодическая — завести парный `<name>_service` в
   `firmware/src/app/{inc,src}/` со стандартными
   `<name>_service_init/start/stop/running/period_ms/publish`.
4. Если ей нужна команда CLI — добавить обработчик в
   [`middleware/shell/`](../firmware/src/middleware/shell/) и обновить
   [`cli.md`](cli.md).
5. Обновить таблицу в этом файле и краткое описание в
   [`architecture.md`](architecture.md).

### Подбор приоритета

- `Normal` — почти всегда. Все равноправные периодические задачи живут здесь.
- `AboveNormal` — только если задача обрабатывает ISR-уведомления и опоздание
  по ним ломает state-machine приложения (как в `task_motor`).
- Выше `AboveNormal` — пока не использовалось; перед подъёмом приоритета
  убедись, что не получится starvation для `protocol` и `diag`.

### Подбор стека

Грубые ориентиры (newlib-nano, `snprintf`):

| Что в задаче                                 | Минимум |
|----------------------------------------------|--------:|
| Только `osDelay` + `LL_GPIO_*`               |     256 |
| `snprintf` + 1–2 локальных буфера ≤64 байт   |    1024 |
| `snprintf` в цикле + длинные форматы (DUMP)  |    2048 |

Контроль переполнения включён (`configCHECK_FOR_STACK_OVERFLOW = 2`) — при
переполнении сработает `vApplicationStackOverflowHook()`. Хук определён в
[`freertos_hooks.c`](../firmware/src/app/src/freertos_hooks.c).
