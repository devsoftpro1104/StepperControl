#ifndef BSP_PINS_H
#define BSP_PINS_H

#include "stm32f4xx_ll_gpio.h"

/* Источник правды по выводам. См. docs/pinout.md */

/* Шаговый драйвер целиком вынесен на GPIOA8..10:
   PA0/PA1 освобождены под аналоговый Hall-датчик AH49E (ADC1_IN1 на PA1).
   STEP=PA8 — для будущего PWM это TIM1_CH1 (advanced timer). */
#define PIN_STEP_PORT          GPIOA
#define PIN_STEP_PIN           LL_GPIO_PIN_8
#define PIN_DIR_PORT           GPIOA
#define PIN_DIR_PIN            LL_GPIO_PIN_9
#define PIN_EN_PORT            GPIOA
#define PIN_EN_PIN             LL_GPIO_PIN_10

/* AH49E (линейный Hall): аналоговый выход → ADC1_IN1. */
#define PIN_HALL_PORT          GPIOA
#define PIN_HALL_PIN           LL_GPIO_PIN_1
#define PIN_HALL_ADC_CHANNEL   1U

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