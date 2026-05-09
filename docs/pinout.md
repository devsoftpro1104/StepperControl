# Карта выводов STM32F407

Источник правды: [firmware/src/bsp/inc/bsp_pins.h](../firmware/src/bsp/inc/bsp_pins.h).

| Функция       | Пин     | Перифер.       | Прим.          |
|---------------|---------|----------------|----------------|
| STEP          | PA8     | TIM1_CH1       | PWM (пока GPIO out, PWM TBD) |
| DIR           | PA9     | GPIO           |                |
| EN            | PA10    | GPIO           | active-low     |
| Hall AH49E    | PA1     | ADC1_IN1       | аналог, линейный, Vout≈Vcc/2 при B=0 |
| UART2 TX/RX   | PA2/3   | USART2         | shell/log, AF7 |
| USB CDC D+/D- | PA12/11 | USB_OTG_FS     | host link      |
| I2C1 SCL/SDA  | PB6/7   | I2C1           | EEPROM/ADS     |
| CAN1 TX/RX    | PB9/8   | CAN1           | TJA1051        |
| LED status    | PD12    | GPIO           |                |
| DS18B20 1-Wire| PB12    | GPIO OD        | внешний 4.7к pull-up к 3.3 В |

> **Внимание (Discovery):** PA9 и PA10 на плате STM32F4 Discovery физически
> разведены на USB OTG FS (PA9 = VBUS sense, PA10 = ID). На кастомной плате
> без USB OTG конфликта нет; на Discovery — учитывать паразитное подтягивание
> с VBUS-делителя.