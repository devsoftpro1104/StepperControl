# Тактирование и шины STM32F407

Источник правды: [firmware/src/bsp/src/bsp_clock.c](../firmware/src/bsp/src/bsp_clock.c), функция `bsp_clock_init_168mhz_hse()`. Документ описывает состояние **после** её выполнения.

## Дерево тактирования

```
HSE 8 MHz ──► /M=8 ──► PLL ──► VCO=336 MHz ──► /P=2 ──► SYSCLK = 168 MHz
                                            └─► /Q=7 ──► 48 MHz (USB OTG FS)

SYSCLK (168 MHz)
  │
  ├─► /AHB=1 ──► HCLK = 168 MHz ──► Cortex-M4, AHB1/AHB2/AHB3, SysTick
  │
  ├─► /APB1=4 ─► PCLK1 = 42 MHz ──► APB1 периферия (USART2/3, UART4/5, I2C1..3, CAN1/2, SPI2/3)
  │              │
  │              └─► ×2 ─────────► 84 MHz ──► APB1 таймеры (TIM2..7, TIM12..14)
  │
  └─► /APB2=2 ─► PCLK2 = 84 MHz ──► APB2 периферия (USART1/6, ADC1..3, SPI1/4..6, SDIO, SYSCFG)
                 │
                 └─► ×2 ─────────► 168 MHz ─► APB2 таймеры (TIM1, TIM8..11)
```

> Множитель ×2 на таймерных входах APB включается автоматически, когда делитель шины ≠ 1. Это не PCLK — baud-rate USART, тайминги I2C и CAN считаются от **PCLK**, а не от таймерной частоты.

## Параметры PLL

| Поле   | Значение | Назначение                              |
|--------|----------|-----------------------------------------|
| Source | HSE      | Внешний кварц 8 МГц (Discovery: MCO ST-Link) |
| M      | 8        | HSE / M = 1 МГц на вход VCO             |
| N      | 336      | VCO = M-out × N = 336 МГц               |
| P      | 2        | SYSCLK = VCO / P = 168 МГц              |
| Q      | 7        | USB48 = VCO / Q = 48 МГц (точно)        |

## Частоты шин

| Шина    | Делитель / множитель | Частота   | Кому отдаётся                              |
|---------|----------------------|-----------|--------------------------------------------|
| HCLK    | SYSCLK / 1           | 168 МГц   | Cortex-M4, AHB1, AHB2, AHB3, SysTick       |
| PCLK1   | HCLK / 4             | 42 МГц    | APB1-периферия                             |
| TIMCLK1 | PCLK1 × 2            | 84 МГц    | таймеры на APB1                            |
| PCLK2   | HCLK / 2             | 84 МГц    | APB2-периферия                             |
| TIMCLK2 | PCLK2 × 2            | 168 МГц   | таймеры на APB2                            |

## Карта периферии (что используется в проекте)

| Периферия         | Шина | Тактовая          | Где включается клок |
|-------------------|------|-------------------|----------------------|
| PWR               | APB1 | PCLK1 = 42 МГц    | [bsp_clock.c](../firmware/src/bsp/src/bsp_clock.c) — нужен до записи `PWR->CR` (VOS) |
| GPIOA             | AHB1 | HCLK = 168 МГц    | [bsp.c](../firmware/src/bsp/src/bsp.c) — `bsp_gpio_init()`; повторно re-enable в `uart2_init`, `step_pwm_init`, `adc_init`, `adc_probe_init` (idempotent) |
| GPIOB             | AHB1 | HCLK = 168 МГц    | [onewire.c](../firmware/src/drivers/onewire/src/onewire.c) — `ow_init()`, нужен для PB12 (DS18B20 1-Wire) |
| GPIOD             | AHB1 | HCLK = 168 МГц    | [bsp.c](../firmware/src/bsp/src/bsp.c) — `bsp_gpio_init()` (LED статус) |
| USART2 (shell)    | APB1 | PCLK1 = 42 МГц    | [uart.c](../firmware/src/drivers/uart/src/uart.c) — `uart2_init()`, baud 115200 |
| DMA1 (USART2 TX)  | AHB1 | HCLK = 168 МГц    | [uart.c](../firmware/src/drivers/uart/src/uart.c) — `uart2_dma_init()`, Stream 6 / Ch 4 |
| TIM1 (STEP PWM)   | APB2 | TIMCLK2 = 168 МГц | [step_pwm.c](../firmware/src/drivers/step_pwm/src/step_pwm.c) — `step_pwm_init()`, PA8 (AF1), PSC=167 → счётчик 1 МГц |
| ADC1 (AH49E hall) | APB2 | PCLK2 / 4 = 21 МГц | [adc.c](../firmware/src/drivers/adc/src/adc.c) — `adc_init()`, PA1 (channel 1), continuous + DMA |
| ADC2 (STEP probe) | APB2 | PCLK2 / 4 = 21 МГц | [adc_probe.c](../firmware/src/drivers/adc_probe/src/adc_probe.c) — `adc_probe_init()`, PA0 (channel 0), continuous + DMA |
| DMA2 (ADC1 ring)  | AHB1 | HCLK = 168 МГц    | [adc.c](../firmware/src/drivers/adc/src/adc.c) — `adc_dma_init()`, Stream 0 / Ch 0, circular |
| DMA2 (ADC2 ring)  | AHB1 | HCLK = 168 МГц    | [adc_probe.c](../firmware/src/drivers/adc_probe/src/adc_probe.c) — `adc_probe_dma_init()`, Stream 2 / Ch 1, circular |
| 1-Wire bit-bang   | core | DWT CYCCNT @ 168 МГц | [onewire.c](../firmware/src/drivers/onewire/src/onewire.c) — `dwt_enable()`, микросекундные тайминги через `SystemCoreClock/1_000_000` |
| SysTick           | core | HCLK = 168 МГц    | [bsp_clock.c](../firmware/src/bsp/src/bsp_clock.c) — `LL_Init1msTick(168000000)` |
| FreeRTOS tick     | —    | 1 кГц от SysTick  | [FreeRTOSConfig.h](../firmware/src/config/FreeRTOSConfig.h) — `configTICK_RATE_HZ` |

> PLL_Q = 7 (USB48) сконфигурирован в [bsp_clock.c](../firmware/src/bsp/src/bsp_clock.c), но USB OTG FS пока не используется (CDC-драйвера в проекте нет, транспорт — UART2). Если USB будет добавлен — клок 48 МГц уже готов.

## Сопутствующая настройка (без неё PLL не запустится)

| Что              | Значение      | Зачем                                                     |
|------------------|---------------|-----------------------------------------------------------|
| FLASH latency    | 5 wait states | требуется при HCLK > 150 МГц при VDD ≥ 2.7 В              |
| Voltage scaling  | VOS = scale 1 | разрешает работу до 168 МГц (иначе потолок 144/120)       |
| PWR enable       | APB1 PWR-clock| необходим до записи в `PWR->CR`                           |

## Регистры после инициализации

| Регистр        | Поле                          | Значение                |
|----------------|-------------------------------|-------------------------|
| `FLASH->ACR`   | LATENCY                       | 5                       |
| `PWR->CR`      | VOS[15:14]                    | `0b11` — Scale 1        |
| `RCC->CR`      | HSEON / HSERDY                | 1 / 1                   |
| `RCC->CR`      | PLLON / PLLRDY                | 1 / 1                   |
| `RCC->PLLCFGR` | PLLM / PLLN / PLLP / PLLQ     | 8 / 336 / 2 / 7         |
| `RCC->PLLCFGR` | PLLSRC                        | HSE                     |
| `RCC->CFGR`    | HPRE                          | `/1`                    |
| `RCC->CFGR`    | PPRE1                         | `/4`                    |
| `RCC->CFGR`    | PPRE2                         | `/2`                    |
| `RCC->CFGR`    | SW / SWS                      | PLL / PLL               |
| `SystemCoreClock` (CMSIS) | —                  | 168 000 000             |

## Подводные камни

- **Baud-rate USART2.** USART2 на APB1 → BRR считается **от PCLK1 = 42 МГц**. Если по ошибке указать 84 МГц — реальный baud окажется вдвое ниже (115200 → 57600), в терминале будет мусор. Множитель ×2 относится только к таймерам.
- **TIM-PSC.** Таймеры на APB1 тикают **84 МГц**, не 42. Это и есть тот самый ×2 при APB1 ≠ 1. Аналогично TIM1/TIM8 на APB2 = 168 МГц — это и есть `STEP_TIMER_CLK_HZ` в [step_pwm.c](../firmware/src/drivers/step_pwm/src/step_pwm.c).
- **USB CDC требует ровно 48 МГц** на USB-фабрике. Обеспечивается PLLQ = 7 (336 / 7 = 48). Сейчас USB-драйвер не используется, но клок настроен — изменение PLLN/PLLM в будущем потребует пересчёта PLLQ.
- **`HSE_VALUE`.** Макрос `HSE_VALUE=8000000U` задан в [firmware/CMakeLists.txt](../firmware/CMakeLists.txt). Без него `system_stm32f4xx.c` берёт значение по умолчанию 25 МГц (для Eval-платы), и `SystemCoreClockUpdate()` даёт некорректную частоту. На Discovery — именно 8 МГц.
- **Порядок вызова.** `bsp_clock_init_168mhz_hse()` обязан отработать **до** любого `*_Init()` периферии. LL-инициализаторы (`LL_USART_Init`, `LL_I2C_Init` и т.п.) читают делители из `RCC` и считают от них собственные регистры — если шины ещё не настроены, числа поедут.
- **VOS до PLL.** Voltage scaling 1 устанавливается до включения PLL. На STM32F407 ошибка не критична (PLL запустится), но для F427/429 это обязательно.
- **Включение GPIO-клоков.** Каждый порт (GPIOA, GPIOB, …) должен быть включён через `LL_AHB1_GRP1_EnableClock(LL_AHB1_GRP1_PERIPH_GPIOx)` до `LL_GPIO_Init`. Чтение/запись регистров GPIO без включенного клока проходит молча и не даёт эффекта — частая причина «не работает пин».

## Где менять

- Частоту/PLL/делители — только [firmware/src/bsp/src/bsp_clock.c](../firmware/src/bsp/src/bsp_clock.c).
- Источник тактирования (HSE/HSI/PLL) — там же, в `LL_RCC_*` вызовах.
- Включение клока новой периферии — внутри её собственного `*_init()`, а не в BSP. Шаблон: `LL_APBn_GRPx_EnableClock(...)` первой строкой.
- Период FreeRTOS-тика — [firmware/src/config/FreeRTOSConfig.h](../firmware/src/config/FreeRTOSConfig.h), `configTICK_RATE_HZ`.

## Смежные документы

- [pinout.md](pinout.md) — какие функции на каких пинах
- [architecture.md](architecture.md) — общая структура прошивки
- [memory_map.md](memory_map.md) — карта памяти (FLASH/SRAM/секции)
