#ifndef DRV_ONEWIRE_H
#define DRV_ONEWIRE_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

/* 1-Wire master через GPIO с программным bit-banging.
   Пин и порт задаются в bsp_pins.h (PIN_DS18B20_*).
   Требуется внешний pull-up 4.7к к VDD; внутренний WPU включён только как
   подстраховка и не вытащит шину достаточно быстро на длинных проводах.

   Тайминги — Maxim AN-126, Standard speed.
   Микросекундные задержки используют DWT->CYCCNT (включается в ow_init()).

   Все транзакции выполняются с глобально замаскированными прерываниями,
   чтобы ISR не съехали тайминги слотов. Один слот ≈ 70 мкс, байт ≈ 0.6 мс,
   reset ≈ 1 мс — это потолок latency других задач во время операции. */

void    ow_init(void);

/* true → устройство ответило presence-pulse. */
bool    ow_reset(void);

void    ow_write_byte(uint8_t b);
uint8_t ow_read_byte(void);
void    ow_read_bytes(uint8_t *out, size_t n);

#endif /* DRV_ONEWIRE_H */
