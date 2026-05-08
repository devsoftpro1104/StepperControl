#include "bsp_clock.h"
#include "stm32f4xx_ll_rcc.h"
#include "stm32f4xx_ll_pwr.h"
#include "stm32f4xx_ll_bus.h"
#include "stm32f4xx_ll_system.h"
#include "stm32f4xx_ll_utils.h"

void bsp_clock_init_168mhz_hse(void) {
    /* FLASH latency = 5 WS (для 168 МГц @ 3.3 V). */
    LL_FLASH_SetLatency(LL_FLASH_LATENCY_5);
    while (LL_FLASH_GetLatency() != LL_FLASH_LATENCY_5) { }

    /* VOS = scale 1 (нужно для 168 МГц). */
    LL_APB1_GRP1_EnableClock(LL_APB1_GRP1_PERIPH_PWR);
    LL_PWR_SetRegulVoltageScaling(LL_PWR_REGU_VOLTAGE_SCALE1);

    /* Запуск HSE 8 MHz. */
    LL_RCC_HSE_Enable();
    while (LL_RCC_HSE_IsReady() != 1) { }

    /* PLL: HSE/M=8 → 1 MHz, N=336 → 336 MHz, P=2 → SYSCLK 168 MHz, Q=7 → 48 MHz (USB). */
    LL_RCC_PLL_ConfigDomain_SYS(LL_RCC_PLLSOURCE_HSE,
                                LL_RCC_PLLM_DIV_8,
                                336,
                                LL_RCC_PLLP_DIV_2);
    LL_RCC_PLL_ConfigDomain_48M(LL_RCC_PLLSOURCE_HSE,
                                LL_RCC_PLLM_DIV_8,
                                336,
                                LL_RCC_PLLQ_DIV_7);
    LL_RCC_PLL_Enable();
    while (LL_RCC_PLL_IsReady() != 1) { }

    /* Делители шин: AHB=1 (168), APB1=4 (42), APB2=2 (84). */
    LL_RCC_SetAHBPrescaler(LL_RCC_SYSCLK_DIV_1);
    LL_RCC_SetAPB1Prescaler(LL_RCC_APB1_DIV_4);
    LL_RCC_SetAPB2Prescaler(LL_RCC_APB2_DIV_2);

    /* SYSCLK ← PLL. */
    LL_RCC_SetSysClkSource(LL_RCC_SYS_CLKSOURCE_PLL);
    while (LL_RCC_GetSysClkSource() != LL_RCC_SYS_CLKSOURCE_STATUS_PLL) { }

    LL_SetSystemCoreClock(168000000);
    LL_Init1msTick(168000000);
}
