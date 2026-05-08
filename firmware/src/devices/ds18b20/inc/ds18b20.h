#ifndef DEV_DS18B20_H
#define DEV_DS18B20_H

#include <stdint.h>

typedef enum {
    DS18B20_OK = 0,
    DS18B20_NO_DEVICE,    /* нет presence-pulse — не подключён или обрыв */
    DS18B20_BAD_CRC,      /* CRC8 scratchpad'а не сошёлся */
    DS18B20_BAD_VALUE,    /* scratchpad весь 0xFF (питание, проводка) */
} ds18b20_status_t;

void ds18b20_init(void);

/* Полный цикл «Convert T → подождать 760 мс → Read Scratchpad». Блокирует
   вызывающую задачу на ≈770 мс. Сериализуется внутренним мьютексом, поэтому
   безопасно вызывать из нескольких задач. Возвращает температуру × 10 °C
   (диапазон сенсора −55.0 … +125.0 °C → −550 … +1250). */
ds18b20_status_t ds18b20_read_blocking(int16_t *out_c10);

#endif /* DEV_DS18B20_H */
