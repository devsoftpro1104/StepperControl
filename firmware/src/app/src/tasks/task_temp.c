/* Задача: периодический опрос DS18B20.
   Опрос управляется CLI-командами (см. shell.c::cmd_temp):
       TEMP ON                  — включить поток $T18,<ts>,<c10>
       TEMP OFF                 — выключить
       TEMP RATE <hz>           — задать частоту (для DS18B20 практически 1)
       TEMP READ                — синхронное разовое чтение (через shell)
   Свежее значение остаётся в temp_service для опроса хостом через CLI. */
#include "cmsis_os2.h"
#include "FreeRTOS.h"
#include "task.h"

#include "uart.h"
#include "ds18b20.h"
#include "temp_service.h"

#include <stdio.h>
#include <stdint.h>

/* DS18B20 12-битная конвертация — ≈760 мс. Период не может быть короче. */
#define READ_BLOCKING_BUDGET_MS  760U

/* Когда опрос выключен — спим короткими интервалами, чтобы быстро реагировать
   на TEMP START без лишнего лага. 200 мс — компромисс «не крутимся в холостую,
   но и не ждём секунду после команды». */
#define IDLE_POLL_MS             200U

void task_temp(void *argument) {
    (void)argument;

    for (;;) {
        if (!temp_service_running()) {
            osDelay(pdMS_TO_TICKS(IDLE_POLL_MS));
            continue;
        }

        int16_t c10;
        ds18b20_status_t st = ds18b20_read_blocking(&c10);
        if (st == DS18B20_OK) {
            temp_service_publish(c10);
            char tstr[8];
            temp_format_c10(tstr, sizeof(tstr), c10);
            char buf[48];
            int n = snprintf(buf, sizeof(buf),
                             "$T18, %lu, %s\r\n",
                             (unsigned long)xTaskGetTickCount(),
                             tstr);
            if (n > 0) {
                if (n >= (int)sizeof(buf)) n = (int)sizeof(buf) - 1;
                uart2_send((const uint8_t *)buf, (uint16_t)n);
            }
        } else {
            temp_service_invalidate();
            /* Молча: спам '!FAULT' раз в секунду перегружает канал.
               Хост сам видит «нет $T18» — этого достаточно для UI. */
        }

        uint32_t period_ms = temp_service_period_ms();
        if (period_ms > READ_BLOCKING_BUDGET_MS) {
            osDelay(pdMS_TO_TICKS(period_ms - READ_BLOCKING_BUDGET_MS));
        }
    }
}
