/* Задача: периодическая отправка телеметрии хосту. */
#include "cmsis_os2.h"

void task_telemetry(void *argument) {
    (void)argument;
    for (;;) {
        /* TODO: сэмплирование положения/тока/температуры, отправка стрима */
        osDelay(100);
    }
}