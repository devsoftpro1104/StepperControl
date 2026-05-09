/* Задача: диагностический LED-маяк.
   Просто моргает PIN_LED_STATUS с периодом 1 Гц — визуальный признак того,
   что планировщик жив. Опрос DS18B20 вынесен в task_temp. */
#include "bsp_pins.h"
#include "stm32f4xx_ll_gpio.h"

#include "cmsis_os2.h"
#include "FreeRTOS.h"
#include "task.h"

void task_diagnostic(void *argument) {
    (void)argument;

    for (;;) {
        LL_GPIO_TogglePin(PIN_LED_STATUS_PORT, PIN_LED_STATUS_PIN);
        osDelay(pdMS_TO_TICKS(500));    /* toggle 2× в сек → 1 Гц blink */
    }
}
