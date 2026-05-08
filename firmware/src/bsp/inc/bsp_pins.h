#ifndef BSP_PINS_H
#define BSP_PINS_H

#include "stm32f4xx_ll_gpio.h"

/* Источник правды по выводам. См. docs/pinout.md */

#define PIN_STEP_PORT          GPIOA
#define PIN_STEP_PIN           LL_GPIO_PIN_0
#define PIN_DIR_PORT           GPIOA
#define PIN_DIR_PIN            LL_GPIO_PIN_1
/* PA2 отдан USART2_TX → EN перенесён на PC4 (свободен на Discovery). */
#define PIN_EN_PORT            GPIOC
#define PIN_EN_PIN             LL_GPIO_PIN_4

#define PIN_LED_STATUS_PORT    GPIOD
#define PIN_LED_STATUS_PIN     LL_GPIO_PIN_12

#define PIN_USART2_TX_PORT     GPIOA
#define PIN_USART2_TX_PIN      LL_GPIO_PIN_2
#define PIN_USART2_RX_PORT     GPIOA
#define PIN_USART2_RX_PIN      LL_GPIO_PIN_3
#define PIN_USART2_AF          LL_GPIO_AF_7

/* DS18B20 (1-Wire). Open-drain + внешний 4.7к pull-up к 3.3 В обязателен. */
#define PIN_DS18B20_PORT       GPIOB
#define PIN_DS18B20_PIN        LL_GPIO_PIN_12

#endif /* BSP_PINS_H */