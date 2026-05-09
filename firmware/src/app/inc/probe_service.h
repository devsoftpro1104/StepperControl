#ifndef APP_PROBE_SERVICE_H
#define APP_PROBE_SERVICE_H

#include <stdint.h>
#include <stdbool.h>

#include "adc_probe.h"

/* Состояние периодической самодиагностики STEP-сигнала через ADC2/PA0.
   Управление — из CLI (PROBE ON/OFF/RATE/READ), сама работа — из task_probe. */

#define PROBE_PERIOD_MIN_MS    20U     /* 50 Hz хватит выше крыши: пересчёт ring всё равно дорогой */
#define PROBE_PERIOD_MAX_MS  60000U
#define PROBE_PERIOD_DEFAULT  500U     /* 2 Hz по умолчанию */

#define PROBE_RATE_MIN_HZ      1U
#define PROBE_RATE_MAX_HZ     50U

void     probe_service_init(void);

bool     probe_service_running(void);
void     probe_service_start(void);
void     probe_service_stop(void);

uint32_t probe_service_period_ms(void);
bool     probe_service_set_period_ms(uint32_t ms);
bool     probe_service_set_rate_hz(uint32_t hz);
uint32_t probe_service_rate_hz(void);

void     probe_service_publish(const adc_probe_stats_t *s);
bool     probe_service_get_last(adc_probe_stats_t *out, uint32_t *out_ts_ms);

#endif /* APP_PROBE_SERVICE_H */
