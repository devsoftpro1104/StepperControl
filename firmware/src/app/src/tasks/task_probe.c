/* Задача: самодиагностика STEP-сигнала через ADC2 + DMA2.
   На каждом тике (period — задаётся PROBE RATE) вычитываем ring-буфер
   adc_probe и считаем статистику: частоту по пересечениям порога, duty,
   vmin/vmax. Публикуем в probe_service и шлём строку $P в UART.

   Управление: PROBE ON/OFF/RATE/READ (см. shell.c::cmd_probe). */
#include "cmsis_os2.h"
#include "FreeRTOS.h"
#include "task.h"

#include "uart.h"
#include "adc_probe.h"
#include "probe_service.h"

#include <stdio.h>
#include <stdint.h>

#define IDLE_POLL_MS  200U

void task_probe(void *argument) {
    (void)argument;

    for (;;) {
        if (!probe_service_running()) {
            osDelay(pdMS_TO_TICKS(IDLE_POLL_MS));
            continue;
        }

        adc_probe_stats_t s;
        adc_probe_get_stats(&s);
        probe_service_publish(&s);

        char buf[64];
        int n = snprintf(buf, sizeof(buf),
                         "$P, %lu, %lu, %u\r\n",
                         (unsigned long)xTaskGetTickCount(),
                         (unsigned long)s.freq_hz,
                         (unsigned)s.adc);
        if (n > 0) {
            if (n >= (int)sizeof(buf)) n = (int)sizeof(buf) - 1;
            uart2_send((const uint8_t *)buf, (uint16_t)n);
        }

        osDelay(pdMS_TO_TICKS(probe_service_period_ms()));
    }
}
