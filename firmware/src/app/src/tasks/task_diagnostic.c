/* Задача: диагностика. LED-маяк + поллинг DS18B20.
   Поллинг управляется CLI-командами:
       TEMP START               — включить поток $T18,<ts>,<c10>
       TEMP STOP                — выключить
       TEMP PERIOD <ms>         — задать период (≥800 мс)
       TEMP READ                — синхронное разовое чтение (см. cli.c)
   Опубликованное здесь значение temp_c10 одновременно подмешивается в
   основной телеметрический стрим $T,... в task_telemetry. */
#include "bsp_pins.h"
#include "stm32f4xx_ll_gpio.h"

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

void task_diagnostic(void *argument) {
    (void)argument;

    for (;;) {
        LL_GPIO_TogglePin(PIN_LED_STATUS_PORT, PIN_LED_STATUS_PIN);

        if (temp_service_running()) {
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
        } else {
            osDelay(pdMS_TO_TICKS(500));    /* LED-«живой» с периодом 1 Гц */
        }
    }
}
