#include "adc.h"
#include "bsp_pins.h"

#include "stm32f4xx.h"
#include "stm32f4xx_ll_bus.h"
#include "stm32f4xx_ll_gpio.h"
#include "stm32f4xx_ll_adc.h"
#include "stm32f4xx_ll_dma.h"

/* --- Соответствие периферии (RM0090):
   ADC1 — APB2, тактируется через ADC_CCR/ADCPRE (PCLK2 / 4 = 84/4 = 21 МГц).
   ADC1 → DMA2 Stream 0 Channel 0  (есть ещё Stream 4 Ch 0 — резерв).
   Канал 1 = PA1 (см. bsp_pins.h: PIN_HALL_*).

   Sample time 480 циклов — избыточно безопасно для низкоомного выхода
   AH49E (≤ ~1 кΩ), но даёт «бесплатное» подавление наводок. Один сэмпл
   ≈ (480 + 12) / 21 МГц ≈ 23.4 мкс. Ring 16 сэмплов → ≈ 375 мкс на цикл. */

#define ADC_BUF_LEN          16U                 /* должно быть степенью двойки */
#define ADC_DMA              DMA2
#define ADC_DMA_STREAM       LL_DMA_STREAM_0
#define ADC_DMA_CHANNEL      LL_DMA_CHANNEL_0

/* DMA пишет сюда без участия CPU. volatile — чтобы компилятор не закешировал
   значения в регистрах между чтениями. */
static volatile uint16_t s_adc_buf[ADC_BUF_LEN];

static void adc_gpio_init(void) {
    /* GPIOA уже включён в bsp_gpio_init(); повторный enable — no-op. */
    LL_AHB1_GRP1_EnableClock(LL_AHB1_GRP1_PERIPH_GPIOA);

    LL_GPIO_InitTypeDef g = {0};
    g.Pin  = PIN_HALL_PIN;
    g.Mode = LL_GPIO_MODE_ANALOG;       /* MODER = 11; OSPEEDR/OTYPER/PUPDR игнорируются */
    g.Pull = LL_GPIO_PULL_NO;           /* любая подтяжка испортит измерение */
    LL_GPIO_Init(PIN_HALL_PORT, &g);
}

static void adc_dma_init(void) {
    LL_AHB1_GRP1_EnableClock(LL_AHB1_GRP1_PERIPH_DMA2);

    LL_DMA_InitTypeDef d = {0};
    d.Channel                = ADC_DMA_CHANNEL;
    d.Direction              = LL_DMA_DIRECTION_PERIPH_TO_MEMORY;
    d.Mode                   = LL_DMA_MODE_CIRCULAR;     /* сам разворачивается с нуля */
    d.PeriphOrM2MSrcIncMode  = LL_DMA_PERIPH_NOINCREMENT;
    d.MemoryOrM2MDstIncMode  = LL_DMA_MEMORY_INCREMENT;
    d.PeriphOrM2MSrcDataSize = LL_DMA_PDATAALIGN_HALFWORD;
    d.MemoryOrM2MDstDataSize = LL_DMA_MDATAALIGN_HALFWORD;
    d.NbData                 = ADC_BUF_LEN;
    d.Priority               = LL_DMA_PRIORITY_LOW;       /* ниже UART_TX */
    d.FIFOMode               = LL_DMA_FIFOMODE_DISABLE;   /* direct mode */
    d.PeriphOrM2MSrcAddress  = (uint32_t)&ADC1->DR;
    d.MemoryOrM2MDstAddress  = (uint32_t)&s_adc_buf[0];
    LL_DMA_Init(ADC_DMA, ADC_DMA_STREAM, &d);

    /* Прерывания не нужны: ring заполняется автоматически, ошибка DMA
       при continuous-конверсии означает только зависший hardware — это
       видно через NDTR, ловить не нужно. */
    LL_DMA_EnableStream(ADC_DMA, ADC_DMA_STREAM);
}

void adc_init(void) {
    adc_gpio_init();
    adc_dma_init();

    LL_APB2_GRP1_EnableClock(LL_APB2_GRP1_PERIPH_ADC1);

    /* Общий блок CCR — делитель тактов всех ADC. /4 → 21 МГц при PCLK2=84. */
    LL_ADC_SetCommonClock(__LL_ADC_COMMON_INSTANCE(ADC1), LL_ADC_CLOCK_SYNC_PCLK_DIV4);

    LL_ADC_InitTypeDef a = {0};
    a.Resolution    = LL_ADC_RESOLUTION_12B;
    a.DataAlignment = LL_ADC_DATA_ALIGN_RIGHT;
    a.SequencersScanMode = LL_ADC_SEQ_SCAN_DISABLE;   /* ровно один rank = 1 канал */
    LL_ADC_Init(ADC1, &a);

    LL_ADC_REG_InitTypeDef r = {0};
    r.TriggerSource    = LL_ADC_REG_TRIG_SOFTWARE;
    r.SequencerLength  = LL_ADC_REG_SEQ_SCAN_DISABLE;
    r.SequencerDiscont = LL_ADC_REG_SEQ_DISCONT_DISABLE;
    r.ContinuousMode   = LL_ADC_REG_CONV_CONTINUOUS;  /* безостановочно после первого start */
    r.DMATransfer      = LL_ADC_REG_DMA_TRANSFER_UNLIMITED; /* DMA-запрос на каждый EOC, не сбрасывается */
    LL_ADC_REG_Init(ADC1, &r);

    LL_ADC_REG_SetSequencerRanks(ADC1, LL_ADC_REG_RANK_1,
                                 __LL_ADC_DECIMAL_NB_TO_CHANNEL(PIN_HALL_ADC_CHANNEL));
    LL_ADC_SetChannelSamplingTime(ADC1,
                                  __LL_ADC_DECIMAL_NB_TO_CHANNEL(PIN_HALL_ADC_CHANNEL),
                                  LL_ADC_SAMPLINGTIME_480CYCLES);

    LL_ADC_Enable(ADC1);

    /* По datasheet ADC требуется ≥ tSTAB = 3 мкс после Enable перед SWSTART.
       На 168 МГц это ≈ 500 циклов; даём с запасом. */
    for (volatile uint32_t i = 0; i < 1000; ++i) { __NOP(); }

    LL_ADC_REG_StartConversionSWStart(ADC1);
    /* С этого момента DMA крутит ring sample-buffer самостоятельно. */
}

uint16_t adc_hall_raw_avg(void) {
    uint32_t sum = 0;
    for (uint32_t i = 0; i < ADC_BUF_LEN; ++i) sum += s_adc_buf[i];
    return (uint16_t)(sum / ADC_BUF_LEN);   /* ADC_BUF_LEN — степень двойки → компилятор сам сделает >>4 */
}

uint16_t adc_hall_raw_latest(void) {
    /* DMA пишет в slot = ADC_BUF_LEN - NDTR. Декремент идёт каждый EOC,
       при достижении нуля перезагружается. Свежая запись — в позицию,
       КУДА ТОЛЬКО ЧТО ЗАПИСАЛИ → это (ADC_BUF_LEN - NDTR - 1) по модулю. */
    uint32_t ndtr = LL_DMA_GetDataLength(ADC_DMA, ADC_DMA_STREAM);
    uint32_t pos  = (ADC_BUF_LEN - ndtr - 1U) & (ADC_BUF_LEN - 1U);
    return s_adc_buf[pos];
}
