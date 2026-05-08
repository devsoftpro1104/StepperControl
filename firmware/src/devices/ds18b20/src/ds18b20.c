#include "ds18b20.h"
#include "onewire.h"

#include "cmsis_os2.h"
#include <stdbool.h>
#include <stddef.h>

#define CMD_SKIP_ROM         0xCCu
#define CMD_CONVERT_T        0x44u
#define CMD_READ_SCRATCHPAD  0xBEu

#define CONVERT_T_DELAY_MS   760U   /* 12-bit: tCONV_max = 750 мс */

static osMutexId_t s_bus_mutex;     /* шина 1-Wire — одна, делим между задачами */

/* CRC-8 Dallas/Maxim, polynomial 0x31 (reflected = 0x8C). Используется для
   проверки 9-байтного scratchpad'а (последний байт — CRC). */
static uint8_t crc8_dallas(const uint8_t *data, size_t n) {
    uint8_t crc = 0;
    for (size_t i = 0; i < n; ++i) {
        uint8_t b = data[i];
        for (int j = 0; j < 8; ++j) {
            uint8_t mix = (uint8_t)((crc ^ b) & 0x01u);
            crc = (uint8_t)(crc >> 1);
            if (mix) crc ^= 0x8Cu;
            b = (uint8_t)(b >> 1);
        }
    }
    return crc;
}

void ds18b20_init(void) {
    ow_init();
    if (s_bus_mutex == NULL) s_bus_mutex = osMutexNew(NULL);
}

ds18b20_status_t ds18b20_read_blocking(int16_t *out_c10) {
    if (out_c10 == NULL) return DS18B20_BAD_VALUE;

    /* osKernelGetState — до старта планировщика мьютекс не работает.
       На этом этапе DS18B20 никто читать не должен; защищаемся. */
    if (osKernelGetState() == osKernelRunning && s_bus_mutex != NULL) {
        osMutexAcquire(s_bus_mutex, osWaitForever);
    }

    ds18b20_status_t st = DS18B20_OK;

    /* --- 1) Convert T --- */
    if (!ow_reset()) { st = DS18B20_NO_DEVICE; goto out; }
    ow_write_byte(CMD_SKIP_ROM);
    ow_write_byte(CMD_CONVERT_T);
    osDelay(CONVERT_T_DELAY_MS);

    /* --- 2) Read Scratchpad --- */
    if (!ow_reset()) { st = DS18B20_NO_DEVICE; goto out; }
    ow_write_byte(CMD_SKIP_ROM);
    ow_write_byte(CMD_READ_SCRATCHPAD);

    uint8_t scratch[9];
    ow_read_bytes(scratch, sizeof(scratch));

    bool all_ff = true;
    for (size_t i = 0; i < sizeof(scratch); ++i) {
        if (scratch[i] != 0xFFu) { all_ff = false; break; }
    }
    if (all_ff)                                  { st = DS18B20_BAD_VALUE; goto out; }
    if (crc8_dallas(scratch, 8) != scratch[8])   { st = DS18B20_BAD_CRC;   goto out; }

    /* Регистр температуры — fixed-point /16 °C, знаковый.
       temp_c10 = raw * 10 / 16 = raw * 5 / 8.  В int32 чтобы не переполнить
       при крайних значениях (−550..+2000 в десятых °C на промежутке). */
    int16_t raw  = (int16_t)((uint16_t)scratch[0] | ((uint16_t)scratch[1] << 8));
    int32_t c10  = ((int32_t)raw * 10) / 16;
    if (c10 >  1250) c10 =  1250;     /* clamp по datasheet'у */
    if (c10 <  -550) c10 =  -550;
    *out_c10 = (int16_t)c10;

out:
    if (osKernelGetState() == osKernelRunning && s_bus_mutex != NULL) {
        osMutexRelease(s_bus_mutex);
    }
    return st;
}
