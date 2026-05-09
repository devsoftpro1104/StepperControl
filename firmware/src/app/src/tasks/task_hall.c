/* Задача: периодический опрос AH49E.
   Опрос управляется CLI-командами (см. shell.c::cmd_hall):
       HALL START               — включить поток $H,<ts>,<raw>,<centered>
       HALL STOP                — выключить
       HALL PERIOD <ms>         — задать период (10..60000)
       HALL READ                — синхронное разовое чтение (через shell)
       HALL ZERO                — записать текущее значение как ноль
   Чтение АЦП мгновенное (DMA-circular), задача в основном спит. */
#include "cmsis_os2.h"
#include "FreeRTOS.h"
#include "task.h"

#include "uart.h"
#include "ah49e.h"
#include "hall_service.h"

#include <stdio.h>
#include <stdint.h>

#define IDLE_POLL_MS  200U

void task_hall(void *argument) {
    (void)argument;

    for (;;) {
        if (!hall_service_running()) {
            osDelay(pdMS_TO_TICKS(IDLE_POLL_MS));
            continue;
        }

        uint16_t raw = ah49e_read_raw();
        int16_t  c   = ah49e_read_centered();
        hall_service_publish(raw, c);

        char buf[48];
        int n = snprintf(buf, sizeof(buf),
                         "$H, %lu, %u, %d\r\n",
                         (unsigned long)xTaskGetTickCount(),
                         (unsigned)raw, (int)c);
        if (n > 0) {
            if (n >= (int)sizeof(buf)) n = (int)sizeof(buf) - 1;
            uart2_send((const uint8_t *)buf, (uint16_t)n);
        }

        osDelay(pdMS_TO_TICKS(hall_service_period_ms()));
    }
}
