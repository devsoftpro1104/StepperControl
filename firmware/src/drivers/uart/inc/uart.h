#ifndef DRV_UART_H
#define DRV_UART_H

#include <stdint.h>

/* USART2: 115200 8N1, PA2/PA3 AF7, PCLK1 = 42 МГц.
   TX через DMA1 Stream 6 Channel 4. Если FreeRTOS ещё не запущен —
   автоматический fallback на polling (для panic/early-boot логирования). */
void uart2_init(void);
void uart2_send_byte  (uint8_t b);                      /* polling, всегда синхронный */
void uart2_send       (const uint8_t *data, uint16_t len); /* блокирует задачу до конца TX */
void uart2_send_string(const char *s);                  /* обёртка над uart2_send */

#endif /* DRV_UART_H */
