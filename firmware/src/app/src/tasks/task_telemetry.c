/* Задача: периодическая отправка телеметрии хосту.
   Включается командой `TELEM ON`, частота — `TELEM RATE <hz>`.
   Формат строки: $T,<ts_ms>,<position>,<current>,<temp_c10>\r\n */
#include "cmsis_os2.h"
#include "FreeRTOS.h"
#include "task.h"

#include "uart.h"
#include "cli.h"

#include <stdio.h>
#include <stdint.h>

void task_telemetry(void *argument) {
    (void)argument;
    TickType_t last = xTaskGetTickCount();

    for (;;) {
        uint16_t hz = cli_telem_rate_hz();
        TickType_t period = (hz == 0U) ? pdMS_TO_TICKS(20)
                                       : pdMS_TO_TICKS(1000U / hz);
        if (period == 0U) period = 1U;

        if (cli_telem_enabled()) {
            uint32_t ts  = (uint32_t)xTaskGetTickCount();
            int32_t  pos = 0;        /* TODO: реальная позиция от драйвера мотора */
            uint16_t cur = 0U;       /* TODO: ADC ток */
            int16_t  t10 = 0;        /* TODO: датчик температуры × 10 */

            char buf[48];
            int n = snprintf(buf, sizeof(buf),
                             "$T,%lu,%ld,%u,%d\r\n",
                             (unsigned long)ts,
                             (long)pos,
                             (unsigned)cur,
                             (int)t10);
            if (n > 0) {
                if (n >= (int)sizeof(buf)) n = (int)sizeof(buf) - 1;
                uart2_send((const uint8_t *)buf, (uint16_t)n);
            }
        }

        vTaskDelayUntil(&last, period);
    }
}
