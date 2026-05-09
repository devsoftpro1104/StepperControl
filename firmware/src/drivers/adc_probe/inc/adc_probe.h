#ifndef DRV_ADC_PROBE_H
#define DRV_ADC_PROBE_H

#include <stdint.h>

/* Самодиагностика STEP-сигнала через ADC2.
   Вход: PA0 (ADC2_IN0); пользователь паяет проволочную перемычку PA8→PA0.
   ADC2 в continuous-режиме непрерывно крутит ring через DMA2 Stream 2 Ch 1.

   Используется отдельно от ADC1 (AH49E) — взаимного влияния нет:
     • ADC1 — Stream 0 Ch 0
     • ADC2 — Stream 2 Ch 1     ← здесь
     • Один общий CCR (clock divider /4) одинаков для обоих, idempotent.

   См. docs/probe.md. */

/* Буфер 4096 × half-word = 8 КБ в .bss. Разумный компромисс «окно vs RAM».
   При sample time 28 циклов и ADC_CLK=21 МГц — окно ≈ 7.8 мс, что покрывает
   STEP частоты от ~64 Hz до 200 kHz с приемлемой точностью оценки. */
#define ADC_PROBE_BUF_LEN      4096U

/* Реальная частота сэмплирования. (28 sample + 12 conv) циклов / 21 МГц. */
#define ADC_PROBE_SAMPLE_HZ    525000U

void adc_probe_init(void);

typedef struct {
    uint32_t freq_hz;        /* оценка по числу пересечений порога 2048 */
    uint16_t adc;            /* среднее значение по ring-буферу, 0..4095.
                                Для PWM/STEP — DC-компонента (≈ duty × 4095). */
} adc_probe_stats_t;

/* Однопроходный анализ ring-буфера. Поток-агностично: один writer (DMA),
   несколько reader'ов; для статистики мгновенный «снимок» сходится, даже
   если DMA успел дописать пару сэмплов во время прохода. */
void adc_probe_get_stats(adc_probe_stats_t *out);

/* --- Сырой дамп ring'а (PROBE DUMP) ------------------------------------ */
/* Останавливает DMA, замораживает текущее состояние ring'а в хронологическом
   порядке. После этого вызывать adc_probe_dump_get(0..BUF_LEN-1) — где 0
   это «самый старый» сэмпл, BUF_LEN-1 — «самый свежий». Когда дамп закончен,
   обязательно вызвать adc_probe_dump_end(), иначе $P-стрим больше не пойдёт. */
void     adc_probe_dump_begin(void);
uint16_t adc_probe_dump_get(uint32_t chronological_idx);
void     adc_probe_dump_end(void);

#endif /* DRV_ADC_PROBE_H */
