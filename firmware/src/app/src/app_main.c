#include "app_main.h"
#include "app_state.h"
#include "bsp.h"
#include "temp_service.h"

#include "FreeRTOS.h"
#include "task.h"
#include "cmsis_os2.h"

extern void task_protocol  (void *argument);
extern void task_motor     (void *argument);
extern void task_telemetry (void *argument);
extern void task_diagnostic(void *argument);
extern void task_watchdog  (void *argument);

static const osThreadAttr_t s_attr_default = {
    .name       = "default",
    .stack_size = 512,
    .priority   = osPriorityNormal,
};

void app_init(void) {
    app_state_set(APP_STATE_BOOT);
    bsp_init();
    temp_service_init();
}

void app_run(void) {
    osKernelInitialize();

    osThreadAttr_t a;

    /* protocol/telem делают snprintf — стек 512 для newlib-nano мал, поднимаем до 1024. */
    a = s_attr_default; a.name = "protocol"; a.stack_size = 1024;
    osThreadNew(task_protocol,   NULL, &a);

    a = s_attr_default; a.name = "motor"; a.priority = osPriorityAboveNormal;
    osThreadNew(task_motor,      NULL, &a);

    a = s_attr_default; a.name = "telem"; a.stack_size = 1024;
    osThreadNew(task_telemetry,  NULL, &a);

    /* diag делает snprintf и блокирует на ~760 мс — даём 1024 байт стека. */
    a = s_attr_default; a.name = "diag"; a.stack_size = 1024;
    osThreadNew(task_diagnostic, NULL, &a);

    a = s_attr_default; a.name = "wdg"; a.stack_size = 256;
    osThreadNew(task_watchdog,   NULL, &a);

    app_state_set(APP_STATE_IDLE);
    osKernelStart();

    /* Сюда не возвращаемся. */
    for (;;) {}
}

int main(void) {
    app_init();
    app_run();
    return 0;
}
