#ifndef HAL_PORT_H
#define HAL_PORT_H

/* Тонкая прослойка между прикладным кодом и LL/HAL/BSP.
   Цель — сделать app/middleware легко тестируемыми и переносимыми
   между MCU без правок выше уровня bsp/. */

#include <stdint.h>
#include <stddef.h>

typedef struct hal_uart_s hal_uart_t;

int  hal_uart_write(hal_uart_t *u, const uint8_t *data, size_t n);
int  hal_uart_read (hal_uart_t *u,       uint8_t *data, size_t n);

uint32_t hal_tick_ms(void);

#endif /* HAL_PORT_H */