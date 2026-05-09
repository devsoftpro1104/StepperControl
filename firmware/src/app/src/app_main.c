#include "app_main.h"
#include "app_state.h"
#include "bsp.h"
#include "temp_service.h"
#include "hall_service.h"
#include "motor_service.h"
#include "probe_service.h"

#include "FreeRTOS.h"
#include "task.h"
#include "cmsis_os2.h"

extern void task_protocol  (void *argument);
extern void task_motor     (void *argument);
extern void task_diagnostic(void *argument);
extern void task_temp      (void *argument);
extern void task_hall      (void *argument);
extern void task_probe     (void *argument);
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
    hall_service_init();
    motor_service_init();
    probe_service_init();
}

void app_run(void) {
    osKernelInitialize();

    osThreadAttr_t a;

    /* protocol гоняет shell + длинные команды (PROBE DUMP — вложенные snprintf
       внутри 32-итерационного цикла). На newlib-nano запас на vsnprintf
       ≈ 400 байт. 2048 даёт комфортный потолок под все будущие команды. */
    a = s_attr_default; a.name = "protocol"; a.stack_size = 2048;
    osThreadNew(task_protocol,   NULL, &a);

    /* motor — будет рулить шаговиком (профиль движения TBD) и публиковать $M. */
    a = s_attr_default; a.name = "motor"; a.priority = osPriorityAboveNormal; a.stack_size = 1024;
    osThreadNew(task_motor,      NULL, &a);

    /* diag — только LED-маяк, ни snprintf, ни блокирующих чтений → 256 хватает. */
    a = s_attr_default; a.name = "diag"; a.stack_size = 256;
    osThreadNew(task_diagnostic, NULL, &a);

    /* temp — опрос DS18B20: snprintf + блок на ~760 мс на ds18b20_read_blocking. */
    a = s_attr_default; a.name = "temp"; a.stack_size = 1024;
    osThreadNew(task_temp,       NULL, &a);

    /* hall — опрос AH49E через ADC: snprintf, не блокирующих вызовов нет. */
    a = s_attr_default; a.name = "hall"; a.stack_size = 1024;
    osThreadNew(task_hall,       NULL, &a);

    /* probe — самодиагностика STEP через ADC2: pass по 4096-сэмплам ring-буфера
       раз в 500 мс — ~5 мс CPU на проход, дальше snprintf + UART. */
    a = s_attr_default; a.name = "probe"; a.stack_size = 1024;
    osThreadNew(task_probe,      NULL, &a);

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
