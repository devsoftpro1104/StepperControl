/* Задача: диагностика, перегрев, перегрузка по току, флаги ошибок. */
#include "bsp_pins.h"
#include "uart.h"
#include "stm32f4xx_ll_gpio.h"
#include "cmsis_os2.h"

void task_diagnostic(void *argument) {
    (void)argument;
    for (;;) {
        LL_GPIO_TogglePin(PIN_LED_STATUS_PORT, PIN_LED_STATUS_PIN);
        uart2_send_string("Hello from STM32F407\r\n");
        osDelay(1000);
        /* TODO: чтение ADC, проверка порогов, выставление APP_STATE_FAULT */
    }
}
