#ifndef STM32F4XX_LL_CONF_H
#define STM32F4XX_LL_CONF_H

#define LL_RCC_MODULE_ENABLED
#define LL_GPIO_MODULE_ENABLED
#define LL_USART_MODULE_ENABLED
#define LL_I2C_MODULE_ENABLED
#define LL_SPI_MODULE_ENABLED
#define LL_TIM_MODULE_ENABLED
#define LL_ADC_MODULE_ENABLED
#define LL_DMA_MODULE_ENABLED
#define LL_EXTI_MODULE_ENABLED
#define LL_PWR_MODULE_ENABLED
#define LL_CORTEX_MODULE_ENABLED
#define LL_UTILS_MODULE_ENABLED

#define HSE_VALUE                ((uint32_t)8000000U)
#define HSI_VALUE                ((uint32_t)16000000U)
#define LSE_VALUE                ((uint32_t)32768U)
#define LSI_VALUE                ((uint32_t)32000U)

#include "stm32f4xx_ll_rcc.h"
#include "stm32f4xx_ll_bus.h"
#include "stm32f4xx_ll_system.h"
#include "stm32f4xx_ll_gpio.h"
#include "stm32f4xx_ll_usart.h"
#include "stm32f4xx_ll_tim.h"
#include "stm32f4xx_ll_dma.h"
#include "stm32f4xx_ll_pwr.h"
#include "stm32f4xx_ll_cortex.h"
#include "stm32f4xx_ll_utils.h"

#endif /* STM32F4XX_LL_CONF_H */