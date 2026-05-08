/* Задача: управление шаговым двигателем (профиль скорости/ускорения). */
#include "cmsis_os2.h"

void task_motor(void *argument) {
    (void)argument;
    for (;;) {
        /* TODO: исполнение профиля движения */
        osDelay(1);
    }
}