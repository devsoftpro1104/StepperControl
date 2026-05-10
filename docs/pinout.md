# Карта выводов STM32F407

Источник правды — [firmware/src/bsp/inc/bsp_pins.h](../firmware/src/bsp/inc/bsp_pins.h).
Этот документ только синхронизирует «функция → пин» в одном месте.

## Используемые пины

| Функция            | Пин     | Перифер.   | Где инициализируется                                                                 |
|--------------------|---------|------------|--------------------------------------------------------------------------------------|
| STEP               | **PA8** | TIM1_CH1, AF1 (PWM) | [step_pwm.c](../firmware/src/drivers/step_pwm/src/step_pwm.c) — `step_pwm_init()` |
| DIR                | **PA9** | GPIO out, push-pull | [bsp.c](../firmware/src/bsp/src/bsp.c) — `bsp_gpio_init()`; полярность 0=FRW, 1=BCK |
| EN                 | **PA10**| GPIO out, push-pull | [bsp.c](../firmware/src/bsp/src/bsp.c) — **active-LOW** (LOW = драйвер включён)   |
| STEP self-probe    | **PA0** | ADC2_IN0   | [adc_probe.c](../firmware/src/drivers/adc_probe/src/adc_probe.c) — `adc_probe_init()`; перемычка PA8→PA0 |
| Hall AH49E         | **PA1** | ADC1_IN1   | [adc.c](../firmware/src/drivers/adc/src/adc.c) — `adc_init()`; аналог, Vout≈Vcc/2 при B=0 |
| UART2 TX           | **PA2** | USART2 AF7 | [uart.c](../firmware/src/drivers/uart/src/uart.c) — `uart2_init()`; 115200 8N1   |
| UART2 RX           | **PA3** | USART2 AF7 | то же                                                                                 |
| LED status         | **PD12**| GPIO out   | [bsp.c](../firmware/src/bsp/src/bsp.c); blink 1 Hz из `task_diagnostic`              |
| DS18B20 1-Wire     | **PB12**| GPIO open-drain | [onewire.c](../firmware/src/drivers/onewire/src/onewire.c) — `ow_init()`; внешний 4.7к pull-up к 3.3 В обязателен |

## Зарезервированные / в коде не используются

Эти пины ничего не делают в текущей сборке — соответствующие драйверы из проекта
удалены (см. CHANGELOG / историю в архитектурных доках). Перечислены, чтобы
любой, кто будет добавлять USB-CDC / I²C / CAN, сразу видел свободные функции
на тех пинах, на которых они исторически ожидались.

| Функция (план)     | Пин      | Что нужно для активации                                |
|--------------------|----------|--------------------------------------------------------|
| USB CDC D+ / D-    | PA12 / PA11 | Реализовать драйвер USB OTG FS. Клок 48 МГц от PLL_Q уже настроен в `bsp_clock_init_168mhz_hse()`. |
| I²C1 SCL / SDA     | PB6 / PB7   | Завести `drivers/i2c` + `devices/eeprom_24lc` (или ADS1115). |
| CAN1 TX / RX       | PB9 / PB8   | Завести `drivers/can` + `devices/tja1051`.               |

## Замечания

- **STM32F4 Discovery:** PA9 / PA10 на этой плате физически разведены на USB OTG FS
  (PA9 = VBUS sense, PA10 = ID). На кастомной плате без USB OTG конфликта нет;
  на Discovery — учитывать паразитное подтягивание с VBUS-делителя при отладке
  DIR/EN. См. [docs/motor.md](motor.md).
- **PA8 ↔ PA0 перемычка** для самодиагностики STEP-сигнала — единственное,
  что физически нужно соединить вне платы для PROBE. Без неё команда `PROBE`
  будет читать наводку. См. [docs/probe.md](probe.md).
