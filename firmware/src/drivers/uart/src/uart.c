#include "uart.h"
#include "bsp_pins.h"
#include "stm32f4xx_ll_bus.h"
#include "stm32f4xx_ll_gpio.h"
#include "stm32f4xx_ll_usart.h"
#include "stm32f4xx_ll_dma.h"

#include "cmsis_os2.h"
#include <string.h>

/* USART2 на APB1 (PCLK1 = SYSCLK / 4 = 168 / 4 = 42 МГц).
   Множитель ×2 на APB1 — это только для таймеров, для USART его нет. */
#define UART2_PCLK_HZ        42000000U
#define UART2_BAUDRATE       115200U

/* USART2_TX → DMA1, Stream 6, Channel 4 (см. RM0090 Table 42). */
#define UART2_TX_DMA         DMA1
#define UART2_TX_DMA_STREAM  LL_DMA_STREAM_6
#define UART2_TX_DMA_CHANNEL LL_DMA_CHANNEL_4
#define UART2_TX_DMA_IRQ     DMA1_Stream6_IRQn
/* Приоритет ISR: число должно быть ≥ configMAX_SYSCALL_INTERRUPT_PRIORITY/16 = 5,
   иначе FreeRTOS-«FromISR» API даст assert. */
#define UART2_TX_DMA_PRIO    6U

static osSemaphoreId_t s_tx_done;   /* TC от DMA → разбудить отправителя */
static osMutexId_t     s_tx_mutex;  /* сериализуем вызовы send() из разных задач */

/* Диагностика пути отправки. Читать в отладчике через watch:
     g_uart2_dbg.dma_tc      — растёт = DMA реально завершает трансферы
     g_uart2_dbg.dma_te      — должно оставаться 0
     g_uart2_dbg.polling_tx  — растёт = код ушёл в fallback-ветку */
typedef struct {
    uint32_t dma_tc;
    uint32_t dma_te;
    uint32_t polling_tx;
} uart2_dbg_t;
volatile uart2_dbg_t g_uart2_dbg;

static void uart2_dma_init(void) {
    LL_AHB1_GRP1_EnableClock(LL_AHB1_GRP1_PERIPH_DMA1);

    LL_DMA_InitTypeDef d = {0};
    d.Channel                = UART2_TX_DMA_CHANNEL;
    d.Direction              = LL_DMA_DIRECTION_MEMORY_TO_PERIPH;
    d.Mode                   = LL_DMA_MODE_NORMAL;
    d.PeriphOrM2MSrcIncMode  = LL_DMA_PERIPH_NOINCREMENT;
    d.MemoryOrM2MDstIncMode  = LL_DMA_MEMORY_INCREMENT;
    d.PeriphOrM2MSrcDataSize = LL_DMA_PDATAALIGN_BYTE;
    d.MemoryOrM2MDstDataSize = LL_DMA_MDATAALIGN_BYTE;
    d.NbData                 = 0;       /* реальная длина — в uart2_send() */
    d.Priority               = LL_DMA_PRIORITY_MEDIUM;
    d.FIFOMode               = LL_DMA_FIFOMODE_DISABLE;  /* direct mode */
    d.PeriphOrM2MSrcAddress  = (uint32_t)&USART2->DR;
    d.MemoryOrM2MDstAddress  = 0;       /* реальный адрес — в uart2_send() */
    LL_DMA_Init(UART2_TX_DMA, UART2_TX_DMA_STREAM, &d);

    LL_DMA_EnableIT_TC(UART2_TX_DMA, UART2_TX_DMA_STREAM);
    LL_DMA_EnableIT_TE(UART2_TX_DMA, UART2_TX_DMA_STREAM);

    NVIC_SetPriority(UART2_TX_DMA_IRQ, UART2_TX_DMA_PRIO);
    NVIC_EnableIRQ(UART2_TX_DMA_IRQ);
}

void uart2_init(void) {
    LL_AHB1_GRP1_EnableClock(LL_AHB1_GRP1_PERIPH_GPIOA);
    LL_APB1_GRP1_EnableClock(LL_APB1_GRP1_PERIPH_USART2);

    LL_GPIO_InitTypeDef g = {0};
    g.Pin        = PIN_USART2_TX_PIN | PIN_USART2_RX_PIN;
    g.Mode       = LL_GPIO_MODE_ALTERNATE;
    g.Speed      = LL_GPIO_SPEED_FREQ_HIGH;
    g.OutputType = LL_GPIO_OUTPUT_PUSHPULL;
    g.Pull       = LL_GPIO_PULL_UP;
    g.Alternate  = PIN_USART2_AF;
    LL_GPIO_Init(PIN_USART2_TX_PORT, &g);

    LL_USART_InitTypeDef u = {0};
    u.BaudRate            = UART2_BAUDRATE;
    u.DataWidth           = LL_USART_DATAWIDTH_8B;
    u.StopBits            = LL_USART_STOPBITS_1;
    u.Parity              = LL_USART_PARITY_NONE;
    u.TransferDirection   = LL_USART_DIRECTION_TX_RX;
    u.HardwareFlowControl = LL_USART_HWCONTROL_NONE;
    u.OverSampling        = LL_USART_OVERSAMPLING_16;
    LL_USART_Init(USART2, &u);

    /* Явный пересчёт BRR от фактического PCLK1 — на случай, если RCC-дерево
       разойдётся с тем, что прочитает LL_USART_Init из регистров. */
    LL_USART_SetBaudRate(USART2, UART2_PCLK_HZ, LL_USART_OVERSAMPLING_16, UART2_BAUDRATE);

    LL_USART_ConfigAsyncMode(USART2);
    LL_USART_EnableDMAReq_TX(USART2);   /* DMAT=1: TXE-события генерируют DMA-запросы */
    LL_USART_Enable(USART2);

    uart2_dma_init();

    /* RTOS-примитивы существуют сразу, но реально используются только после
       старта kernel; до этого uart2_send() уходит в polling-ветку. */
    s_tx_done  = osSemaphoreNew(1, 0, NULL);
    s_tx_mutex = osMutexNew(NULL);
}

void uart2_send_byte(uint8_t b) {
    while (!LL_USART_IsActiveFlag_TXE(USART2)) { }
    LL_USART_TransmitData8(USART2, b);
}

static void uart2_send_polling(const uint8_t *data, uint16_t len) {
    g_uart2_dbg.polling_tx++;
    for (uint16_t i = 0; i < len; ++i) {
        uart2_send_byte(data[i]);
    }
    while (!LL_USART_IsActiveFlag_TC(USART2)) { }
}

void uart2_send(const uint8_t *data, uint16_t len) {
    if (data == NULL || len == 0) return;

    /* До старта FreeRTOS — DMA-путь использовать нельзя (нет шедулера, чтобы блокировать).
       Это нужно для ранней диагностики/panic-логирования. */
    if (osKernelGetState() != osKernelRunning) {
        uart2_send_polling(data, len);
        return;
    }

    osMutexAcquire(s_tx_mutex, osWaitForever);

    /* Очистка флагов потока 6 (HIFCR) — без этого новый трансфер не стартует. */
    LL_DMA_ClearFlag_TC6 (UART2_TX_DMA);
    LL_DMA_ClearFlag_HT6 (UART2_TX_DMA);
    LL_DMA_ClearFlag_TE6 (UART2_TX_DMA);
    LL_DMA_ClearFlag_DME6(UART2_TX_DMA);
    LL_DMA_ClearFlag_FE6 (UART2_TX_DMA);

    LL_DMA_DisableStream    (UART2_TX_DMA, UART2_TX_DMA_STREAM);
    LL_DMA_SetMemoryAddress (UART2_TX_DMA, UART2_TX_DMA_STREAM, (uint32_t)data);
    LL_DMA_SetDataLength    (UART2_TX_DMA, UART2_TX_DMA_STREAM, len);
    LL_USART_ClearFlag_TC   (USART2);
    LL_DMA_EnableStream     (UART2_TX_DMA, UART2_TX_DMA_STREAM);

    osSemaphoreAcquire(s_tx_done, osWaitForever);
    /* TC от DMA приходит, когда последний байт уехал в DR. Ещё ждём, пока он
       выйдет из shift-регистра в линию — иначе тут же повторный send «съест» хвост. */
    while (!LL_USART_IsActiveFlag_TC(USART2)) { }

    osMutexRelease(s_tx_mutex);
}

void uart2_send_string(const char *s) {
    if (s == NULL) return;
    uart2_send((const uint8_t *)s, (uint16_t)strlen(s));
}

void DMA1_Stream6_IRQHandler(void) {
    if (LL_DMA_IsActiveFlag_TC6(UART2_TX_DMA)) {
        LL_DMA_ClearFlag_TC6(UART2_TX_DMA);
        LL_DMA_DisableStream(UART2_TX_DMA, UART2_TX_DMA_STREAM);
        g_uart2_dbg.dma_tc++;
        if (s_tx_done) osSemaphoreRelease(s_tx_done);
    }
    if (LL_DMA_IsActiveFlag_TE6(UART2_TX_DMA)) {
        LL_DMA_ClearFlag_TE6(UART2_TX_DMA);
        LL_DMA_DisableStream(UART2_TX_DMA, UART2_TX_DMA_STREAM);
        g_uart2_dbg.dma_te++;
        /* Разбудить отправителя, чтобы он не висел вечно. */
        if (s_tx_done) osSemaphoreRelease(s_tx_done);
        /* TODO: пометить APP_STATE_FAULT через app_state_set() */
    }
}
