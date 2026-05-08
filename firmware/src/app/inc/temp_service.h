#ifndef APP_TEMP_SERVICE_H
#define APP_TEMP_SERVICE_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

/* Состояние периодического опроса DS18B20 и последнее валидное измерение.
   Установка/сброс флагов происходит из CLI (task_protocol), периодический
   опрос — из task_diagnostic. Поля volatile — этого достаточно для одного
   writer'а на каждое поле. */

#define TEMP_PERIOD_MIN_MS  800U      /* tCONV_max = 750 мс + запас */
#define TEMP_PERIOD_MAX_MS  60000U
#define TEMP_PERIOD_DEFAULT 1000U     /* «один раз в секунду» */

void     temp_service_init(void);

bool     temp_service_running(void);
void     temp_service_start(void);
void     temp_service_stop(void);

uint32_t temp_service_period_ms(void);
bool     temp_service_set_period_ms(uint32_t ms);   /* false → вне диапазона */

void     temp_service_publish(int16_t c10);
void     temp_service_invalidate(void);
/* true → есть валидное последнее измерение, поля out_c10 и out_ts_ms заполнены. */
bool     temp_service_get_last(int16_t *out_c10, uint32_t *out_ts_ms);

/* Форматирует значение × 10 °C в человекочитаемое "<sign><int>.<frac>",
   например 266 → "26.6", -125 → "-12.5". Без float-printf — чтобы не тащить
   newlib-nano с поддержкой %f. Возвращает число записанных символов
   (без '\0'). buf_size ≥ 8 — достаточно для всего диапазона DS18B20. */
int      temp_format_c10(char *buf, size_t buf_size, int16_t c10);

#endif /* APP_TEMP_SERVICE_H */
