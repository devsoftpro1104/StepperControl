#include "probe_service.h"

#include "FreeRTOS.h"
#include "task.h"

static volatile bool     s_running     = false;
static volatile uint32_t s_period_ms   = PROBE_PERIOD_DEFAULT;

/* Структура мала и пишется одной задачей (task_probe), читается shell'ом —
   поля volatile не дают компилятору закешировать в регистрах. */
static volatile adc_probe_stats_t s_last;
static volatile uint32_t          s_last_ts_ms;
static volatile bool              s_have_value;

void probe_service_init(void) {
    s_running    = false;
    s_period_ms  = PROBE_PERIOD_DEFAULT;
    s_have_value = false;
}

bool     probe_service_running(void)    { return s_running; }
void     probe_service_start(void)      { s_running = true; }
void     probe_service_stop(void)       { s_running = false; }
uint32_t probe_service_period_ms(void)  { return s_period_ms; }

bool probe_service_set_period_ms(uint32_t ms) {
    if (ms < PROBE_PERIOD_MIN_MS || ms > PROBE_PERIOD_MAX_MS) return false;
    s_period_ms = ms;
    return true;
}

bool probe_service_set_rate_hz(uint32_t hz) {
    if (hz < PROBE_RATE_MIN_HZ || hz > PROBE_RATE_MAX_HZ) return false;
    return probe_service_set_period_ms(1000U / hz);
}

uint32_t probe_service_rate_hz(void) {
    return (1000U + s_period_ms / 2U) / s_period_ms;
}

void probe_service_publish(const adc_probe_stats_t *s) {
    s_last.freq_hz = s->freq_hz;
    s_last.adc     = s->adc;
    s_last_ts_ms   = (uint32_t)xTaskGetTickCount();
    s_have_value   = true;
}

bool probe_service_get_last(adc_probe_stats_t *out, uint32_t *out_ts_ms) {
    if (!s_have_value) return false;
    if (out) {
        out->freq_hz = s_last.freq_hz;
        out->adc     = s_last.adc;
    }
    if (out_ts_ms) *out_ts_ms = s_last_ts_ms;
    return true;
}
