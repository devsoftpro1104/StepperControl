#ifndef DRV_ADC_H
#define DRV_ADC_H

#include <stdint.h>

/* ADC1 на STM32F407: один канал в continuous-режиме, DMA2 Stream 0 Channel 0
   в circular-режиме крутит ring-buffer на N сэмплов. Чтение из ring'а —
   мгновенное, без блокировок. См. docs/ah49e.md → секция «АЦП».

   Сейчас драйвер заточен под единственного пользователя — AH49E на канале 1.
   Если потребуется добавить ещё каналов — переходить на scan-mode + ranks. */

void     adc_init(void);

/* Усреднённое 12-битное значение по всему ring-buffer'у. 0..4095. */
uint16_t adc_hall_raw_avg(void);

/* Самый свежий сэмпл (последняя позиция, куда писал DMA). 0..4095.
   Полезно для фронтов/триггеров, где «глаз» среднего размывает ступеньку. */
uint16_t adc_hall_raw_latest(void);

#endif /* DRV_ADC_H */
