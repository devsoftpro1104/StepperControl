/* Задача: разбор входящих кадров протокола, диспетчеризация команд. */
#include "cmsis_os2.h"

void task_protocol(void *argument) {
    (void)argument;
    for (;;) {
        /* TODO: чтение из транспорта, парсинг, обработка */
        osDelay(10);
    }
}