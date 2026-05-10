# Мотор — шаговый драйвер

Сводка по прошивочной интеграции шагового двигателя через внешний драйвер
(A4988/DRV8825/TMC22xx-style): пины, аппаратный PWM, асинхронная схема
«CLI → ISR → задача», текущее состояние и место под будущий профилировщик.

## Аппаратное подключение

| Сигнал   | Пин MCU | Режим                                                  | Полярность     |
|----------|---------|--------------------------------------------------------|----------------|
| STEP     | **PA8** | Alt-function **AF1 (TIM1_CH1)**, push-pull, PWM        | передний фронт = 1 шаг |
| DIR      | **PA9** | GPIO out, push-pull                                    | 0 = FRW (по часовой), 1 = BCK (против) |
| EN       | **PA10**| GPIO out, push-pull                                    | **active-LOW**: pin LOW = драйвер включён |

Источник правды — [`bsp_pins.h`](../firmware/src/bsp/inc/bsp_pins.h).

> **Внимание (Discovery):** PA9/PA10 на плате STM32F4 Discovery физически
> разведены на USB OTG FS (PA9 = VBUS sense, PA10 = ID). На кастомной плате
> без USB OTG конфликта нет. Если используешь Discovery с USB — DIR/EN могут
> подтягиваться через USB-делитель.

## Слой абстракции

```
   shell  CLI                      ISR  TIM1 UEV
       │                                 │
       │ motor_service_move()            │ ulTaskNotifyGiveFromISR
       ▼                                 ▼
   ┌──────────────────────────────────────────────────┐
   │ motor_service:                                   │
   │   move/abort/sync_position/register_owner        │
   │   pos, target, speed_sps, position_zero          │
   │   en, dir                  → реальные GPIO       │
   └──────────────────────────────────────────────────┘
        │                                 ▲
        │ step_pwm_start(steps, task)     │ step_pwm_emitted()
        ▼                                 │
   ┌──────────────────────────────────────────────────┐
   │ step_pwm:                                        │
   │   TIM1 PWM mode 1, CH1 → PA8 AF1                 │
   │   ARR = 1_000_000 / sps - 1   (PSC=167, 1 МГц)   │
   │   UEV ISR: ++emitted, --remaining,               │
   │            при remaining=0 → stop + notify       │
   └──────────────────────────────────────────────────┘
                        │
                        ▼
                  PA8 (TIM1_CH1)
```

## Аппаратный PWM на TIM1

[`firmware/src/drivers/step_pwm/`](../firmware/src/drivers/step_pwm/).

| Параметр                | Значение                              | Почему                      |
|-------------------------|---------------------------------------|-----------------------------|
| Таймер                  | **TIM1** (advanced)                   | Только advanced даёт CH1 на PA8 + RCR на будущее |
| Источник тактов         | APB2 timer clock = **168 МГц**        | PCLK2 ×2 (prescaler != 1)   |
| PSC                     | 167 → счётчик **1 МГц** (1 µs/тик)    | Удобный масштаб для расчёта sps |
| ARR                     | `1_000_000 / sps - 1`                 | Прямой пересчёт в частоту шагов |
| CCR1                    | `ARR / 2` (50 % duty)                 | Pulse ≥ 2 µs даже на 200 кГц — выше требований A4988/DRV8825 |
| Mode CH1                | PWM mode 1, OCREF active high         | Стандарт                    |
| ARR/CCR preload         | **enabled**                           | Смена скорости синхронно на UEV → без stutter |
| Repetition counter (RCR)| **0** (UEV каждый шаг)                | Просто. На будущее — chunked-режим |
| MOE (BDTR)              | **0 в init, 1 в `step_pwm_start()`**  | До первого movement выходы Hi-Z, драйвер не получает мусор |
| UEV-ISR приоритет       | 6 (≥ FreeRTOS-`MAX_SYSCALL_PRIO`/16=5)| `vTaskNotifyGiveFromISR` иначе assert'нет |

### Диапазон скоростей

```
  STEP_PWM_MIN_SPS   16   sps   (ARR=62499  ≈ 62.5 ms на шаг)
  STEP_PWM_MAX_SPS  200000 sps  (ARR=4)
```

Нижняя граница — 16-битное ARR; ниже 16 sps надо менять PSC. Верхняя
совпадает с `PROJ_MOTOR_MAX_SPEED_SPS` и нагрузкой ISR ≈ 200 кГц × ~60 циклов
= 7 % CPU @168 МГц. Для гарантии можно поднять предел через RCR-чанки —
TBD.

## Асинхронная схема исполнения MOVE

```
 [task_protocol]              [task_motor]                [TIM1 ISR]
       │                            │                          │
       │  MOVE 1000 5000            │                          │
       │  (CLI string)              │                          │
       │                            │                          │
       │  motor_service_move()      │                          │
       │   ├─ step_pwm_set_speed_sps│                          │
       │   ├─ set_dir по знаку steps│                          │
       │   ├─ set_en(true)          │                          │
       │   ├─ s_target = pos+steps  │                          │
       │   └─ step_pwm_start(N, h)  │                          │
       │                            │                          │
       │  app_state_set(MOVING)     │                          │
       │  !STATE MOVING ───────────►│                          │
       │  +OK MOVE …  ────────────► │                          │
       │  (отвечает мгновенно)      │                          │
       │                            │ ulTaskNotifyTake(period) │
       │                            │   timeout — обычное      │
       │                            │   пробуждение для $M     │
       │                            │   notif — финал движения │
       │                            │                          │
       │                            │ ◄───────────────── UEV × N
       │                            │   ISR на каждый шаг:     │
       │                            │     ++s_emitted          │
       │                            │     --s_remaining        │
       │                            │     при 0 → stop + notify│
       │                            │                          │
       │                            │ notif=1 → state IDLE,    │
       │                            │ !DONE MOVE               │
```

Ключевые свойства:

- `cmd_move` **не блокирует** CLI — отвечает `+OK MOVE` сразу, движение
  идёт асинхронно в TIM1.
- `task_motor` периодически просыпается по таймауту = `MOTOR RATE`.
  На каждом просыпе:
  - вычитывает `step_pwm_emitted()`, обновляет `motor_service.position`
    с учётом знака направления;
  - если `MOTOR ON` — публикует `$M`.
- ISR **не делает snprintf и не работает с UART** — только инкремент
  счётчиков и `vTaskNotifyGiveFromISR`. Минимальная латентность.
- `STOP` / `motor_service_abort()` синхронно глушат TIM1 и обновляют
  позицию финальным `sync_position`-ом. Безопасно вызывать в любой момент.

## CLI

### Управление движением

| Команда                              | Ответ при успехе                         | Возможные `-ERR`                         |
|--------------------------------------|------------------------------------------|------------------------------------------|
| `MOVE <steps> <speed_sps>`           | `!STATE MOVING` + `+OK MOVE steps=… speed=…`, по завершении `!DONE MOVE` + `!STATE IDLE` | `bad-number`, `bad-speed`, `bad-steps`, `busy`, `not-ready`, `fault` |
| `STOP`                               | `+OK STOP` + `!STATE IDLE` (если был MOVING) | —                                    |
| `MOVETO <pos>`                       | (не реализовано)                         | `not-implemented` (TBD)                  |
| `HOME`                               | (не реализовано)                         | `not-implemented` (TBD)                  |

> **Знак `steps` задаёт направление.** `MOVE -1000 5000` → `motor_service_move`
> сам выставит `DIR BCK` и `EN ON` — ручная команда `DIR ...` перед `MOVE`
> перезапишется. Это сделано чтобы хосту не нужно было думать, что переключать
> первым; см. [motor_service.c:88-107](../firmware/src/app/src/motor_service.c).

> Профиль скорости (трапеция / S-curve) пока не реализован — движение идёт
> на постоянной скорости. Когда заведём, **ускорение появится отдельной
> командой `MOTOR ACCEL <sps2>`** (глобальная настройка), а не возвращается
> третьим аргументом `MOVE`. См. секцию «Что ещё нужно реализовать».

### Bring-up GPIO (без запуска движения)

| Команда       | Действие                                  | Ответ |
|---------------|-------------------------------------------|-------|
| `EN ON`       | Установить EN=LOW (драйвер включён)       | `+OK EN ON`  |
| `EN OFF`      | Установить EN=HIGH (driver disabled)      | `+OK EN OFF` |
| `DIR FRW`     | Установить DIR=LOW (по часовой)           | `+OK DIR FRW` |
| `DIR BCK`     | Установить DIR=HIGH (против часовой)      | `+OK DIR BCK` |

`EN`/`DIR` дёргают GPIO напрямую. `motor_service_move()` в начале своего
исполнения сам выставит `EN ON` и нужное направление, так что эти команды
нужны только для «потыкать» драйвер вручную при первой проверке.

### Телеметрия

| Команда             | Действие                                | Ответ |
|---------------------|-----------------------------------------|-------|
| `MOTOR READ`        | Синхронный «снимок» состояния           | `+OK MOTOR pos=… speed=… target=… en=… dir=…` |
| `MOTOR ON`          | Включить поток `$M`                     | `+OK MOTOR ON` |
| `MOTOR OFF`         | Выключить поток                         | `+OK MOTOR OFF` |
| `MOTOR RATE <hz>`   | Частота публикации (1..50 Hz, дефолт 10)| `+OK MOTOR RATE <hz>` / `-ERR MOTOR bad-rate min=1 max=50` |
| `MOTOR ZERO`        | Прервать движение (если идёт) и обнулить `pos`/`target`. Новая «нулевая» точка — текущая физическая позиция. | `+OK MOTOR ZERO pos=0` |

Поток `$M`:
```
$M, <ts>, <pos>, <speed_sps>, <target>, <en>, <dir>\r\n
```

## Состояния и события

| Переход                                     | Когда                                |
|---------------------------------------------|--------------------------------------|
| `IDLE → MOVING`                              | Успешный `MOVE`                      |
| `MOVING → IDLE` + `!DONE MOVE`              | ISR насчитал все шаги                |
| `MOVING → IDLE` (без `!DONE`)               | `STOP` пришёл до завершения          |
| `* → FAULT` (сейчас не выставляется мотором)| резерв для перегрузки/отвалившегося драйвера |

`!STATE IDLE` эмитится в `task_motor` сразу после транзиции — хост видит
финал не позже 1 тика OS после физического конца движения.

## FreeRTOS-задача `task_motor`

| Параметр       | Значение                | Почему |
|----------------|-------------------------|--------|
| Имя            | `"motor"`               | — |
| Стек           | 1024 байт               | snprintf(`%lu`,`%ld`...) — самый прожорливый кадр |
| Приоритет      | `osPriorityAboveNormal` | На случай будущего профилировщика с жёсткими таймингами; сейчас не критично |
| Блокировка     | `ulTaskNotifyTake(timeout=motor_period)` | Ловит ISR-уведомление и таймер телеметрии в одной точке |

Состояния:
- `BLOCKED` (notify-wait) — почти всё время, либо до таймаута, либо до
  завершения движения.
- `RUNNING` — короткие миллисекунды на `sync_position` + `snprintf` + `uart_send`.

## Что ещё нужно реализовать (TBD)

1. **Трапециевидный (или S-curve) профиль скорости.** План:
   - Добавить глобальную настройку через CLI: `MOTOR ACCEL <sps2>` →
     пишется в `motor_service` (`s_accel_sps2`). По умолчанию 0 = без
     рампы (текущее поведение).
   - В `task_motor` на каждом просыпе считать новое `speed_sps` по функции
     рампы (по `s_accel`, текущей `step_pwm_emitted`, `s_remaining`) и
     вызывать `step_pwm_set_speed_sps()`. ARR с preload подхватится без
     stutter.
   - `MOVE` остаётся двух-аргументным: `MOVE <steps> <speed_sps>`.
2. **`MOVETO <pos>`** — абсолютная цель: `delta = pos - motor_service_position()`,
   далее как обычный `MOVE`.
3. **`HOME`** — последовательность: ехать на малой скорости в одну сторону
   до триггера (концевик / пересечение Hall-порога через `hall_service`),
   `motor_service.position = 0`, отъехать на ~10 шагов, найти триггер
   повторно для повышения точности.
4. **Chunked UEV-ISR через RCR.** Снизит CPU-нагрузку на высоких скоростях.
   Сейчас не нужно (запас огромный), но архитектурно `step_pwm.c` уже
   готов: достаточно добавить логику переноса `RCR` на «последний кусок».
5. **FAULT-детект:** сторожевой таймер на отсутствие движения, сравнение
   ожидаемой и реальной позиции (нужен encoder feedback).

## Связанные файлы

- [firmware/src/drivers/step_pwm/inc/step_pwm.h](../firmware/src/drivers/step_pwm/inc/step_pwm.h)
- [firmware/src/drivers/step_pwm/src/step_pwm.c](../firmware/src/drivers/step_pwm/src/step_pwm.c)
- [firmware/src/app/inc/motor_service.h](../firmware/src/app/inc/motor_service.h)
- [firmware/src/app/src/motor_service.c](../firmware/src/app/src/motor_service.c)
- [firmware/src/app/src/tasks/task_motor.c](../firmware/src/app/src/tasks/task_motor.c)
- [firmware/src/middleware/shell/src/shell.c](../firmware/src/middleware/shell/src/shell.c) (`cmd_motor`, `cmd_move`, `cmd_stop`, `cmd_en`, `cmd_dir`, `cmd_moveto`, `cmd_home`)
- [firmware/src/bsp/inc/bsp_pins.h](../firmware/src/bsp/inc/bsp_pins.h) (`PIN_STEP_*` + `PIN_STEP_AF`, `PIN_DIR_*`, `PIN_EN_*`)
- [firmware/src/bsp/src/bsp.c](../firmware/src/bsp/src/bsp.c) — `step_pwm_init()` вызывается отсюда
- [docs/cli.md](cli.md) — общий формат CLI и стримов
