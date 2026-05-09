#include "temp_service.h"

#include "FreeRTOS.h"
#include "task.h"

#include <stdio.h>

static volatile bool     s_running     = false;
static volatile uint32_t s_period_ms   = TEMP_PERIOD_DEFAULT;
static volatile int16_t  s_last_c10    = 0;
static volatile uint32_t s_last_ts_ms  = 0;
static volatile bool     s_have_value  = false;

void temp_service_init(void) {
    /* статика уже в .bss; явный init — для симметрии и будущих расширений */
    s_running    = false;
    s_period_ms  = TEMP_PERIOD_DEFAULT;
    s_have_value = false;
}

bool     temp_service_running(void)    { return s_running; }
void     temp_service_start(void)      { s_running = true; }
void     temp_service_stop(void)       { s_running = false; }
uint32_t temp_service_period_ms(void)  { return s_period_ms; }

bool temp_service_set_period_ms(uint32_t ms) {
    if (ms < TEMP_PERIOD_MIN_MS || ms > TEMP_PERIOD_MAX_MS) return false;
    s_period_ms = ms;
    return true;
}

bool temp_service_set_rate_hz(uint32_t hz) {
    if (hz < TEMP_RATE_MIN_HZ || hz > TEMP_RATE_MAX_HZ) return false;
    return temp_service_set_period_ms(1000U / hz);
}

uint32_t temp_service_rate_hz(void) {
    /* округление вверх — чтобы 1500 мс не показывался как «0 Гц» */
    return (1000U + s_period_ms / 2U) / s_period_ms;
}

void temp_service_publish(int16_t c10) {
    s_last_c10   = c10;
    s_last_ts_ms = (uint32_t)xTaskGetTickCount();
    s_have_value = true;
}

void temp_service_invalidate(void) {
    s_have_value = false;
}

bool temp_service_get_last(int16_t *out_c10, uint32_t *out_ts_ms) {
    if (!s_have_value) return false;
    if (out_c10)   *out_c10   = s_last_c10;
    if (out_ts_ms) *out_ts_ms = s_last_ts_ms;
    return true;
}

int temp_format_c10(char *buf, size_t buf_size, int16_t c10) {
    int neg = (c10 < 0);
    int32_t abs_c10  = neg ? -(int32_t)c10 : (int32_t)c10;
    int     int_part = (int)(abs_c10 / 10);
    int     frac     = (int)(abs_c10 % 10);
    return snprintf(buf, buf_size, "%s%d.%d", neg ? "-" : "", int_part, frac);
}
