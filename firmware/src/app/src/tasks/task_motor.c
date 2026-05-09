/* Задача: оркестрация мотора + публикация $M-стрима телеметрии.

   Реализовано:
     - на старте регистрируем себя как «owner task» в motor_service: ISR из
       step_pwm присылает нам уведомление, когда движение завершилось;
     - в цикле блокируемся на ulTaskNotifyTake() с таймаутом = периодом
       телеметрии. Каждый «тик» — синхронизируем motor_service.position
       со счётчиком step_pwm и при включённом MOTOR ON шлём $M;
     - при получении уведомления от ISR — финализируем позицию,
       переводим стейт в IDLE и эмитим !DONE MOVE.

   НЕ реализовано (TBD): профиль скорости (трапеция/S-curve). Сейчас движение
   всегда на постоянной скорости — задаётся как `speed_sps` в MOVE,
   аргумент `accel` принимается, но игнорируется. См. docs/motor.md. */
#include "cmsis_os2.h"
#include "FreeRTOS.h"
#include "task.h"

#include "uart.h"
#include "shell.h"
#include "app_state.h"
#include "motor_service.h"
#include "step_pwm.h"

#include <stdio.h>
#include <stdint.h>

#define IDLE_POLL_MS  200U

void task_motor(void *argument) {
    (void)argument;

    /* Регистрируем себя как получателя ISR-уведомлений из step_pwm.
       До этой строки CLI-команда MOVE вернёт MOTOR_ERR_NOT_READY. */
    motor_service_register_owner(xTaskGetCurrentTaskHandle());

    for (;;) {
        /* Если телеметрия выключена — спим длинно, но всё равно реагируем
           на notify от ISR (он разбудит ulTaskNotifyTake до истечения). */
        TickType_t timeout = motor_service_running()
                                ? pdMS_TO_TICKS(motor_service_period_ms())
                                : pdMS_TO_TICKS(IDLE_POLL_MS);

        uint32_t notif = ulTaskNotifyTake(pdTRUE, timeout);

        /* В любом случае подтянем позицию из счётчика — даже если просто
           публикуем телеметрию без движения, эта операция дешёвая. */
        motor_service_sync_position_from_pwm();

        if (notif != 0) {
            /* Движение завершилось штатно. Позиция уже синхронизирована
               выше, target должен совпасть с position — это хорошее
               место под assert/sanity-check в Debug. */
            if (app_state_get() == APP_STATE_MOVING) {
                app_state_set(APP_STATE_IDLE);
                shell_event("STATE IDLE");
            }
            shell_event("DONE MOVE");
        }

        if (motor_service_running()) {
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
        }
    }
}
