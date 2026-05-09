# Мотор — шаговый драйвер

Сводка по прошивочной интеграции шагового двигателя через внешний драйвер
(A4988/DRV8825/TMC22xx-style): какие пины задействованы, какая CLI, как
устроен `motor_service`. **Профилировщик движения (MOVE/MOVETO/HOME) ещё не
реализован** — этот документ описывает текущий каркас и место под будущую
реализацию.

## Аппаратное подключение

| Сигнал   | Пин MCU | Режим          | Полярность     |
|----------|---------|----------------|----------------|
| STEP     | **PA8** | GPIO out (TIM1_CH1, AF1 — для будущего PWM) | передний фронт = 1 шаг |
| DIR      | **PA9** | GPIO out       | 0 = CW, 1 = CCW |
| EN       | **PA10**| GPIO out       | **active-LOW**: pin LOW = драйвер включён |

Источник правды — [`bsp_pins.h`](../firmware/src/bsp/inc/bsp_pins.h).

> **Внимание (Discovery):** PA9/PA10 на плате STM32F4 Discovery физически
> разведены на USB OTG FS (PA9 = VBUS sense, PA10 = ID). На кастомной плате
> без USB OTG конфликта нет. Если используешь Discovery с USB — DIR/EN могут
> подтягиваться через USB-делитель.

## Слой абстракции

```
   shell  CLI        task_motor (TBD: профилировщик)
       │                │
       └──┬─────────────┘
          ▼
   ┌──────────────────────────────────────────────────┐
   │ motor_service:                                   │
   │   running, period_ms                             │
   │   pos, target, speed_sps  ← TBD (profile writes) │
   │   en, dir                  ← реальные GPIO       │
   └──────────────────────────────────────────────────┘
                    │
                    ▼
              GPIO PA9/PA10
              (PA8 для STEP — пока bare GPIO out, PWM через TIM1_CH1 — TBD)
```

## Текущее состояние FreeRTOS-задачи

[`firmware/src/app/src/tasks/task_motor.c`](../firmware/src/app/src/tasks/task_motor.c) —
выполняет **только публикацию `$M`-стрима** на основе `motor_service`. Когда
`MOTOR ON` — каждые `period_ms` шлёт строку:

```
$M, <ts>, <pos>, <speed_sps>, <target>, <en>, <dir>\r\n
```

Сейчас `pos`/`speed_sps`/`target` всегда `0` (нет источника). После
реализации профилировщика этот же поток покажет реальные значения без
изменений в `task_motor.c` — профиль будет писать через `motor_service_*`,
которые я заложил с volatile-полями специально под это.

| Параметр потока | Значение            |
|-----------------|---------------------|
| Имя             | `"motor"`           |
| Стек            | 1024 байт           |
| Приоритет       | `osPriorityAboveNormal` (специально выше остальных — у профилировщика будут жёсткие тайминги) |

## CLI

### Телеметрия (`MOTOR`)

| Команда             | Действие                                | Ответ |
|---------------------|-----------------------------------------|-------|
| `MOTOR READ`        | Синхронный «снимок» состояния           | `+OK MOTOR pos=0 speed=0 target=0 en=off dir=cw` |
| `MOTOR ON`          | Включить поток `$M`                     | `+OK MOTOR ON` |
| `MOTOR OFF`         | Выключить поток                         | `+OK MOTOR OFF` |
| `MOTOR RATE <hz>`   | Частота публикации (1..50 Hz, дефолт 10)| `+OK MOTOR RATE <hz>` / `-ERR MOTOR bad-rate min=1 max=50` |

### Bring-up GPIO

Полезно при первой проверке драйвера, без запуска профиля:

| Команда       | Действие                                  | Ответ |
|---------------|-------------------------------------------|-------|
| `EN ON`       | Установить EN=LOW (драйвер включён)       | `+OK EN ON`  |
| `EN OFF`      | Установить EN=HIGH (driver disabled)      | `+OK EN OFF` |
| `DIR CW`      | Установить DIR=LOW                        | `+OK DIR CW` |
| `DIR CCW`     | Установить DIR=HIGH                       | `+OK DIR CCW`|

Эти команды **реальные**, не stub'ы — напрямую дёргают GPIO PA10/PA9.

### Управление движением (TBD)

| Команда                              | Состояние           | Ответ                              |
|--------------------------------------|---------------------|------------------------------------|
| `MOVE <steps> <speed_sps> <accel>`   | Stub (стейт переходит в MOVING, реального движения нет) | `+OK MOVE steps=… speed=… accel=…` |
| `MOVETO <pos>`                       | **Не реализовано**  | `-ERR MOVETO not-implemented`      |
| `STOP`                               | Stub (стейт → IDLE) | `+OK STOP`                         |
| `HOME`                               | **Не реализовано**  | `-ERR HOME not-implemented`        |

## Что нужно реализовать дальше

1. **STEP PWM на TIM1_CH1.** Поднять TIM1 в PWM-mode, AF1 на PA8, ARR
   управляется частотой шагов, переключение DIR — через `motor_service_set_dir`.
2. **Профилировщик движения** в `task_motor`: trapezoidal/S-curve,
   преобразование `(steps, speed, accel)` → серию изменений ARR во времени.
3. **Подсчёт пройденных шагов** через DMA/UEV-счётчик TIM1, чтобы
   `motor_service_set_position` обновлялся без CPU-нагрузки.
4. **`MOVETO <pos>`** — абсолютная цель относительно `motor_service_position`
   на момент команды.
5. **`HOME`** — последовательность: задать малую скорость, ехать в одну
   сторону до триггера (концевик / пересечение Hall-порога), сбросить
   `motor_service_set_position(0)`, отъехать на запас, найти триггер
   повторно для повышения точности.

## Связанные файлы

- [firmware/src/app/inc/motor_service.h](../firmware/src/app/inc/motor_service.h)
- [firmware/src/app/src/motor_service.c](../firmware/src/app/src/motor_service.c)
- [firmware/src/app/src/tasks/task_motor.c](../firmware/src/app/src/tasks/task_motor.c)
- [firmware/src/middleware/shell/src/shell.c](../firmware/src/middleware/shell/src/shell.c) (`cmd_motor`, `cmd_en`, `cmd_dir`, `cmd_move`, `cmd_moveto`, `cmd_home`, `cmd_stop`)
- [firmware/src/bsp/inc/bsp_pins.h](../firmware/src/bsp/inc/bsp_pins.h) (`PIN_STEP_*`, `PIN_DIR_*`, `PIN_EN_*`)
- [docs/cli.md](cli.md) — общий формат CLI и стримов
