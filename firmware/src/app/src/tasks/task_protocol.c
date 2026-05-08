/* Задача: разбор входящих кадров протокола, диспетчеризация команд.
   Сейчас работает текстовый shell (см. middleware/shell/inc/shell.h
   и docs/cli.md). Бинарный фрейм-протокол по SOF/CRC будет добавлен
   поверх этого же транспорта. */
#include "cmsis_os2.h"
#include "uart.h"
#include "shell.h"

void task_protocol(void *argument) {
    (void)argument;
    shell_init();

    for (;;) {
        uint8_t b;
        int drained = 0;
        /* Опустошаем RX-кольцо: при 115200 baud за 2 мс прилетает ≤24 байт,
           буфер 256 байт переполниться не успеет. */
        while (uart2_rx_get(&b)) {
            shell_feed(b);
            drained = 1;
        }
        if (!drained) osDelay(2);
    }
}
