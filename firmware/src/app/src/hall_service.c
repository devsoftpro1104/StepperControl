#include "hall_service.h"

#include "FreeRTOS.h"
#include "task.h"

static volatile bool     s_running       = false;
static volatile uint32_t s_period_ms     = HALL_PERIOD_DEFAULT;
static volatile uint16_t s_last_raw      = 0;
static volatile int16_t  s_last_centered = 0;
static volatile uint32_t s_last_ts_ms    = 0;
static volatile bool     s_have_value    = false;

void hall_service_init(void) {
    s_running    = false;
    s_period_ms  = HALL_PERIOD_DEFAULT;
    s_have_value = false;
}

bool     hall_service_running(void)    { return s_running; }
void     hall_service_start(void)      { s_running = true; }
void     hall_service_stop(void)       { s_running = false; }
uint32_t hall_service_period_ms(void)  { return s_period_ms; }

bool hall_service_set_period_ms(uint32_t ms) {
    if (ms < HALL_PERIOD_MIN_MS || ms > HALL_PERIOD_MAX_MS) return false;
    s_period_ms = ms;
    return true;
}

bool hall_service_set_rate_hz(uint32_t hz) {
    if (hz < HALL_RATE_MIN_HZ || hz > HALL_RATE_MAX_HZ) return false;
    return hall_service_set_period_ms(1000U / hz);
}

uint32_t hall_service_rate_hz(void) {
    return (1000U + s_period_ms / 2U) / s_period_ms;
}

void hall_service_publish(uint16_t raw, int16_t centered) {
    s_last_raw      = raw;
    s_last_centered = centered;
    s_last_ts_ms    = (uint32_t)xTaskGetTickCount();
    s_have_value    = true;
}

bool hall_service_get_last(uint16_t *out_raw, int16_t *out_centered, uint32_t *out_ts_ms) {
    if (!s_have_value) return false;
    if (out_raw)      *out_raw      = s_last_raw;
    if (out_centered) *out_centered = s_last_centered;
    if (out_ts_ms)    *out_ts_ms    = s_last_ts_ms;
    return true;
}
