#include "adc_probe.h"
#include "bsp_pins.h"

#include "stm32f4xx.h"
#include "stm32f4xx_ll_bus.h"
#include "stm32f4xx_ll_gpio.h"
#include "stm32f4xx_ll_adc.h"
#include "stm32f4xx_ll_dma.h"

/* --- Соответствие периферии (RM0090):
   ADC2 — APB2, общий тактовый блок ADC.
   ADC2 → DMA2 Stream 2 Channel 1  (резерв: Stream 3 Ch 1).
   Канал 0 = PA0.

   Sample time 28 циклов — компромисс. На бинарном сигнале шум не критичен,
   но и слишком быстро сэмплировать не нужно (узкое окно по времени).
   28 + 12 = 40 циклов / 21 МГц = 1.9 мкс / сэмпл = 525 kSPS. */

#define PROBE_ADC                  ADC2
#define PROBE_ADC_CHANNEL          0U
#define PROBE_DMA                  DMA2
#define PROBE_DMA_STREAM           LL_DMA_STREAM_2
#define PROBE_DMA_CHANNEL          LL_DMA_CHANNEL_1

/* Порог логического «1». Для CMOS-сигнала 0..VDDA любое значение около
   середины (2048) валидно. Возможен phantom-transition если сэмпл попал
   точно на фронт — но при 525 kSPS и фронте ≤ 100 нс таких сэмплов на
   окно ≈ 0–1, статистике не мешают. */
#define PROBE_THRESHOLD            2048U

static volatile uint16_t s_buf[ADC_PROBE_BUF_LEN];

static void adc_probe_gpio_init(void) {
    LL_AHB1_GRP1_EnableClock(LL_AHB1_GRP1_PERIPH_GPIOA);

    LL_GPIO_InitTypeDef g = {0};
    g.Pin  = LL_GPIO_PIN_0;          /* PA0 = ADC2_IN0 */
    g.Mode = LL_GPIO_MODE_ANALOG;
    g.Pull = LL_GPIO_PULL_NO;        /* не подтягиваем — это испортит измерение фронтов */
    LL_GPIO_Init(GPIOA, &g);
}

static void adc_probe_dma_init(void) {
    LL_AHB1_GRP1_EnableClock(LL_AHB1_GRP1_PERIPH_DMA2);

    LL_DMA_InitTypeDef d = {0};
    d.Channel                = PROBE_DMA_CHANNEL;
    d.Direction              = LL_DMA_DIRECTION_PERIPH_TO_MEMORY;
    d.Mode                   = LL_DMA_MODE_CIRCULAR;
    d.PeriphOrM2MSrcIncMode  = LL_DMA_PERIPH_NOINCREMENT;
    d.MemoryOrM2MDstIncMode  = LL_DMA_MEMORY_INCREMENT;
    d.PeriphOrM2MSrcDataSize = LL_DMA_PDATAALIGN_HALFWORD;
    d.MemoryOrM2MDstDataSize = LL_DMA_MDATAALIGN_HALFWORD;
    d.NbData                 = ADC_PROBE_BUF_LEN;
    d.Priority               = LL_DMA_PRIORITY_LOW;
    d.FIFOMode               = LL_DMA_FIFOMODE_DISABLE;
    d.PeriphOrM2MSrcAddress  = (uint32_t)&PROBE_ADC->DR;
    d.MemoryOrM2MDstAddress  = (uint32_t)&s_buf[0];
    LL_DMA_Init(PROBE_DMA, PROBE_DMA_STREAM, &d);

    LL_DMA_EnableStream(PROBE_DMA, PROBE_DMA_STREAM);
}

void adc_probe_init(void) {
    adc_probe_gpio_init();
    adc_probe_dma_init();

    LL_APB2_GRP1_EnableClock(LL_APB2_GRP1_PERIPH_ADC2);

    /* Общий CCR делитель тактов — тот же /4 что и у ADC1. Запись idempotent. */
    LL_ADC_SetCommonClock(__LL_ADC_COMMON_INSTANCE(PROBE_ADC),
                          LL_ADC_CLOCK_SYNC_PCLK_DIV4);

    LL_ADC_InitTypeDef a = {0};
    a.Resolution         = LL_ADC_RESOLUTION_12B;
    a.DataAlignment      = LL_ADC_DATA_ALIGN_RIGHT;
    a.SequencersScanMode = LL_ADC_SEQ_SCAN_DISABLE;
    LL_ADC_Init(PROBE_ADC, &a);

    LL_ADC_REG_InitTypeDef r = {0};
    r.TriggerSource    = LL_ADC_REG_TRIG_SOFTWARE;
    r.SequencerLength  = LL_ADC_REG_SEQ_SCAN_DISABLE;
    r.SequencerDiscont = LL_ADC_REG_SEQ_DISCONT_DISABLE;
    r.ContinuousMode   = LL_ADC_REG_CONV_CONTINUOUS;
    r.DMATransfer      = LL_ADC_REG_DMA_TRANSFER_UNLIMITED;
    LL_ADC_REG_Init(PROBE_ADC, &r);

    LL_ADC_REG_SetSequencerRanks(PROBE_ADC, LL_ADC_REG_RANK_1,
                                 __LL_ADC_DECIMAL_NB_TO_CHANNEL(PROBE_ADC_CHANNEL));
    LL_ADC_SetChannelSamplingTime(PROBE_ADC,
                                  __LL_ADC_DECIMAL_NB_TO_CHANNEL(PROBE_ADC_CHANNEL),
                                  LL_ADC_SAMPLINGTIME_28CYCLES);

    LL_ADC_Enable(PROBE_ADC);
    for (volatile uint32_t i = 0; i < 1000; ++i) { __NOP(); }   /* tSTAB ≥ 3 µs */

    LL_ADC_REG_StartConversionSWStart(PROBE_ADC);
}

/* --- Сырой дамп ring'а ------------------------------------------------- */
/* На время дампа DMA остановлен → s_buf замораживается. ADC продолжает
   конвертировать (continuous), новые сэмплы пишутся в DR, без DMA уходят
   в OVR — после adc_probe_dump_end() флаг чистим, DMA снова начинает с
   текущей позиции счётчика. */

static uint32_t s_dump_start;

void adc_probe_dump_begin(void) {
    LL_DMA_DisableStream(PROBE_DMA, PROBE_DMA_STREAM);
    /* NDTR замораживается на значении «осталось трансферов до конца цикла».
       Position next-to-write = (LEN - NDTR) mod LEN — это и есть «самый
       старый» сэмпл (тот, что DMA сейчас был готов перезаписать). */
    uint32_t ndtr = LL_DMA_GetDataLength(PROBE_DMA, PROBE_DMA_STREAM);
    s_dump_start  = (ADC_PROBE_BUF_LEN - ndtr) & (ADC_PROBE_BUF_LEN - 1U);
}

uint16_t adc_probe_dump_get(uint32_t chronological_idx) {
    uint32_t i = (s_dump_start + chronological_idx) & (ADC_PROBE_BUF_LEN - 1U);
    return s_buf[i];
}

void adc_probe_dump_end(void) {
    /* За время дампа DMA был disabled. ADC в continuous + OVRMOD=0 после
       1–2 не-вычитанных EOC поднимает OVR и **останавливает регулярный
       секвенсор** (RM0090 §13.8.1). Чтобы $P / READ после DUMP работали,
       нужно: (1) почистить OVR, (2) включить DMA, (3) ре-стартануть SW-trigger. */
    LL_ADC_ClearFlag_OVR(PROBE_ADC);
    LL_DMA_EnableStream(PROBE_DMA, PROBE_DMA_STREAM);
    LL_ADC_REG_StartConversionSWStart(PROBE_ADC);
}

void adc_probe_get_stats(adc_probe_stats_t *out) {
    uint32_t sum         = 0;
    uint32_t transitions = 0;

    /* «Снимок» текущего ring'а. Один writer (DMA) — race не катастрофа,
       стрим всё равно усреднит за несколько окон. */
    uint8_t prev_high = (s_buf[0] >= PROBE_THRESHOLD) ? 1U : 0U;
    for (uint32_t i = 0; i < ADC_PROBE_BUF_LEN; ++i) {
        uint16_t v = s_buf[i];
        sum += v;
        uint8_t h = (v >= PROBE_THRESHOLD) ? 1U : 0U;
        if (h != prev_high) transitions++;
        prev_high = h;
    }

    /* freq = transitions / 2 / window_s
       = transitions * SAMPLE_HZ / (2 * BUF_LEN)
       Промежуточное произведение до 4096 × 525000 = 2.15e9 — выходит за uint32,
       поэтому считаем в uint64_t. */
    uint64_t f = ((uint64_t)transitions * (uint64_t)ADC_PROBE_SAMPLE_HZ)
                 / (2ULL * (uint64_t)ADC_PROBE_BUF_LEN);

    out->freq_hz = (uint32_t)f;
    out->adc     = (uint16_t)(sum / ADC_PROBE_BUF_LEN);
}
