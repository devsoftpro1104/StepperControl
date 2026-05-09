#ifndef DEV_AH49E_H
#define DEV_AH49E_H

#include <stdint.h>
#include <stdbool.h>

/* Линейный аналоговый Hall-датчик AH49E.
   Подключение: VCC=3.3 В (можно 5 В при 5В-tolerant делителе на входе АЦП),
   GND, OUT → PA1 → ADC1_IN1. На холостом ходу OUT ≈ Vcc/2. Полярное поле
   N сдвигает выход вверх, S — вниз; чувствительность ≈ 1.4 мВ/Гс @ 5 В,
   ≈ 0.92 мВ/Гс @ 3.3 В. См. docs/ah49e.md.

   Драйвер не блокирующий: ADC крутится в DMA-circular, чтение — это просто
   взять текущий «снимок» из ring-buffer'а. */

void     ah49e_init(void);

/* Сырое 12-битное значение АЦП, усреднённое по ring-буферу. 0..4095. */
uint16_t ah49e_read_raw(void);

/* Перевод в милливольты при VREF+ = 3.3 В.  raw * 3300 / 4095. */
uint16_t ah49e_read_mv(void);

/* «Центрированное» отклонение от калиброванного нуля, в counts (signed).
   Если калибровка не выполнена — возвращает raw - 2048 (теоретический mid). */
int16_t  ah49e_read_centered(void);

/* Записать текущий усреднённый raw как новый «ноль» (HALL ZERO).
   Возвращает зафиксированный offset. Делать при отсутствии магнита у датчика. */
uint16_t ah49e_calibrate_zero(void);

/* Сбросить калибровку → центр снова считается как 2048. */
void     ah49e_clear_zero(void);

/* true → калибровка была выполнена (ah49e_calibrate_zero вызывался). */
bool     ah49e_zero_is_set(void);
uint16_t ah49e_zero_get(void);

#endif /* DEV_AH49E_H */
