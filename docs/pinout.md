# Карта выводов STM32F407

Источник правды: [firmware/src/bsp/inc/bsp_pins.h](../firmware/src/bsp/inc/bsp_pins.h).

| Функция       | Пин     | Перифер.   | Прим.          |
|---------------|---------|------------|----------------|
| STEP          | PA0     | TIM2_CH1   | PWM            |
| DIR           | PA1     | GPIO       |                |
| EN            | PC4     | GPIO       | active-low     |
| UART2 TX/RX   | PA2/3   | USART2     | shell/log, AF7 |
| USB CDC D+/D- | PA12/11 | USB_OTG_FS | host link      |
| I2C1 SCL/SDA  | PB6/7   | I2C1       | EEPROM/ADS     |
| CAN1 TX/RX    | PB9/8   | CAN1       | TJA1051        |
| LED status    | PD12    | GPIO       |                |
| DS18B20 1-Wire| PB12    | GPIO OD    | внешний 4.7к pull-up к 3.3 В |