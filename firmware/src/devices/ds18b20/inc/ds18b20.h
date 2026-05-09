#ifndef DEV_DS18B20_H
#define DEV_DS18B20_H

#include <stdint.h>

typedef enum {
    DS18B20_OK = 0,
    DS18B20_NO_DEVICE,    /* нет presence-pulse — не подключён или обрыв */
    DS18B20_BAD_CRC,      /* CRC8 scratchpad'а не сошёлся */
    DS18B20_BAD_VALUE,    /* scratchpad весь 0xFF (питание, проводка) */
} ds18b20_status_t;

/* Configuration Register (scratchpad[4]) — биты R1:R0 задают разрешение.
   Остальные биты по datasheet'у должны быть 1 (read-as-1). */
typedef enum {
    DS18B20_RES_9BIT  = 0x1Fu,   /* tCONV ≈ 94 мс,  шаг 0.5    °C */
    DS18B20_RES_10BIT = 0x3Fu,   /* tCONV ≈ 188 мс, шаг 0.25   °C */
    DS18B20_RES_11BIT = 0x5Fu,   /* tCONV ≈ 375 мс, шаг 0.125  °C */
    DS18B20_RES_12BIT = 0x7Fu,   /* tCONV ≈ 750 мс, шаг 0.0625 °C — заводское */
} ds18b20_resolution_t;

void ds18b20_init(void);

/* Полный цикл «Convert T → подождать 760 мс → Read Scratchpad». Блокирует
   вызывающую задачу на ≈770 мс. Сериализуется внутренним мьютексом, поэтому
   безопасно вызывать из нескольких задач. Возвращает температуру × 10 °C
   (диапазон сенсора −55.0 … +125.0 °C → −550 … +1250). */
ds18b20_status_t ds18b20_read_blocking(int16_t *out_c10);

/* Прошить в EEPROM датчика заданное разрешение. Сценарий: чип ранее стоял в
   другом проекте и был переведён, например, в 9-bit (0.5 °C шаг) — заводская
   гарантия 12 бит уже не действует, конфиг лежит в EEPROM сенсора и переживает
   power cycle. Функция:
     1. читает текущий scratchpad, проверяет CRC;
     2. если scratchpad[4] уже совпадает с res — EEPROM не трогается;
     3. иначе Write Scratchpad (TH=+127, TL=−128, CONFIG=res) + Copy Scratchpad;
     4. перечитывает scratchpad и сверяет CRC + scratchpad[4] == res.
   TH/TL ставим за пределы рабочего диапазона DS18B20 (±127 °C), чтобы alarm
   search никогда не срабатывал — alarm-функцией мы не пользуемся.
   Расходуется одна запись EEPROM (ресурс ≥50000 циклов по datasheet'у), поэтому
   вызывать редко — не на каждом ребуте. Сериализуется тем же s_bus_mutex. */
ds18b20_status_t ds18b20_configure_resolution(ds18b20_resolution_t res);

#endif /* DEV_DS18B20_H */
