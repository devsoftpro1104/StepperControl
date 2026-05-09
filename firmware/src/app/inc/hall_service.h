#ifndef APP_HALL_SERVICE_H
#define APP_HALL_SERVICE_H

#include <stdint.h>
#include <stdbool.h>

/* Состояние периодического опроса AH49E и последнее опубликованное измерение.
   Управление флагами — из CLI (task_protocol), сам опрос — из task_hall.
   В отличие от temp_service здесь нет «valid»-флага: ADC всегда что-то
   возвращает, ошибка АЦП в нашей конфигурации (continuous + DMA circular)
   физически означает только сорванный init — на это смотрим через таймаут. */

#define HALL_PERIOD_MIN_MS    10U      /* быстрее не имеет смысла — UART затопится  */
#define HALL_PERIOD_MAX_MS  60000U
#define HALL_PERIOD_DEFAULT  100U      /* 10 Hz по умолчанию */

#define HALL_RATE_MIN_HZ      1U
#define HALL_RATE_MAX_HZ    100U       /* period_min 10 мс → 100 Hz */

void     hall_service_init(void);

bool     hall_service_running(void);
void     hall_service_start(void);
void     hall_service_stop(void);

uint32_t hall_service_period_ms(void);
bool     hall_service_set_period_ms(uint32_t ms);
bool     hall_service_set_rate_hz(uint32_t hz);
uint32_t hall_service_rate_hz(void);

void     hall_service_publish(uint16_t raw, int16_t centered);
bool     hall_service_get_last(uint16_t *out_raw, int16_t *out_centered, uint32_t *out_ts_ms);

#endif /* APP_HALL_SERVICE_H */
