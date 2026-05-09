#include "bsp.h"
#include "bsp_clock.h"
#include "bsp_pins.h"
#include "uart.h"
#include "ds18b20.h"
#include "ah49e.h"
#include "stm32f4xx_ll_bus.h"
#include "stm32f4xx_ll_gpio.h"

static void bsp_gpio_init(void) {
    LL_AHB1_GRP1_EnableClock(LL_AHB1_GRP1_PERIPH_GPIOA);
    LL_AHB1_GRP1_EnableClock(LL_AHB1_GRP1_PERIPH_GPIOD);

    LL_GPIO_InitTypeDef gpio = {0};
    gpio.Mode       = LL_GPIO_MODE_OUTPUT;
    gpio.Speed      = LL_GPIO_SPEED_FREQ_LOW;
    gpio.OutputType = LL_GPIO_OUTPUT_PUSHPULL;
    gpio.Pull       = LL_GPIO_PULL_NO;

    /* LED статус */
    gpio.Pin = PIN_LED_STATUS_PIN;
    LL_GPIO_Init(PIN_LED_STATUS_PORT, &gpio);

    /* Шаговый драйвер: DIR, EN — обычные GPIO. STEP пока тоже GPIO; PWM заведём в драйвере timer. */
    gpio.Pin = PIN_DIR_PIN;
    LL_GPIO_Init(PIN_DIR_PORT, &gpio);
    gpio.Pin = PIN_EN_PIN;
    LL_GPIO_Init(PIN_EN_PORT, &gpio);
    gpio.Pin = PIN_STEP_PIN;
    LL_GPIO_Init(PIN_STEP_PORT, &gpio);
}

void bsp_init(void) {
    bsp_clock_init_168mhz_hse();
    bsp_gpio_init();
    uart2_init();
    ds18b20_init();    /* DWT + GPIOB12 open-drain; реальное чтение — из task_temp */
    ah49e_init();      /* ADC1 + DMA2 Stream0 непрерывно крутят PA1; чтение — из task_hall */
}
