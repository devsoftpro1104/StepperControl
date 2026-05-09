/* Задача: управление шаговым двигателем + публикация $M-стрима телеметрии.
   Профилировщик движения (MOVE/MOVETO/HOME) пока не реализован — всё, что
   есть здесь, это публикация stub'ов из motor_service. После реализации
   профиля единственное изменение в этой задаче — заменить чтение
   motor_service_* на реальные значения, которые сам же профилировщик пишет. */
#include "cmsis_os2.h"
#include "FreeRTOS.h"
#include "task.h"

#include "uart.h"
#include "motor_service.h"

#include <stdio.h>
#include <stdint.h>

#define IDLE_POLL_MS  200U

void task_motor(void *argument) {
    (void)argument;

    for (;;) {
        if (!motor_service_running()) {
            osDelay(pdMS_TO_TICKS(IDLE_POLL_MS));
            continue;
        }

        char buf[80];
        int n = snprintf(buf, sizeof(buf),
                         "$M, %lu, %ld, %lu, %ld, %u, %u\r\n",
                         (unsigned long)xTaskGetTickCount(),
                         (long)motor_service_position(),
                         (unsigned long)motor_service_speed_sps(),
                         (long)motor_service_target(),
                         (unsigned)(motor_service_en() ? 1 : 0),
                         (unsigned)motor_service_dir());
        if (n > 0) {
            if (n >= (int)sizeof(buf)) n = (int)sizeof(buf) - 1;
            uart2_send((const uint8_t *)buf, (uint16_t)n);
        }

        osDelay(pdMS_TO_TICKS(motor_service_period_ms()));
    }
}
