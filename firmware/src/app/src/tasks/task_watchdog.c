/* Задача: периодическое поглаживание IWDG/WWDG. */
#include "cmsis_os2.h"

void task_watchdog(void *argument) {
    (void)argument;
    for (;;) {
        /* TODO: LL_IWDG_ReloadCounter(IWDG) */
        osDelay(200);
    }
}