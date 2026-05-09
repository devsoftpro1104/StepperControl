#include "ah49e.h"
#include "adc.h"

/* VREF+ платы STM32F4 Discovery подключён к 3.3 В через паяную перемычку SB12.
   На кастомной плате — измеренное VDDA. Если потребуется уйти с 3.3 В —
   переменная VREF_MV должна жить в калибровке EEPROM. */
#define VREF_MV       3300U
#define ADC_FULL      4095U
#define ADC_MID       2048U   /* теоретический ноль при отсутствии калибровки */

static volatile uint16_t s_zero_offset = ADC_MID;
static volatile bool     s_zero_set    = false;

void ah49e_init(void) {
    adc_init();
}

uint16_t ah49e_read_raw(void) {
    return adc_hall_raw_avg();
}

uint16_t ah49e_read_mv(void) {
    /* (raw * VREF_MV) до 4095 * 3300 = 13'513'725 — влезает в uint32. */
    uint32_t raw = adc_hall_raw_avg();
    return (uint16_t)((raw * VREF_MV) / ADC_FULL);
}

int16_t ah49e_read_centered(void) {
    int32_t raw  = adc_hall_raw_avg();
    int32_t zero = s_zero_offset;
    int32_t d    = raw - zero;
    if (d >  2047) d =  2047;        /* clamp в int16 диапазон с запасом */
    if (d < -2048) d = -2048;
    return (int16_t)d;
}

uint16_t ah49e_calibrate_zero(void) {
    uint16_t z = adc_hall_raw_avg();
    s_zero_offset = z;
    s_zero_set    = true;
    return z;
}

void ah49e_clear_zero(void) {
    s_zero_offset = ADC_MID;
    s_zero_set    = false;
}

bool     ah49e_zero_is_set(void) { return s_zero_set; }
uint16_t ah49e_zero_get   (void) { return s_zero_offset; }
