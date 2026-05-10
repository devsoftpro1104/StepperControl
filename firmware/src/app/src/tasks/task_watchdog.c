/* Задача: периодическое поглаживание IWDG.
 * LSI ≈ 32 кГц / prescaler 32 → 1 тик = 1 мс. Reload = 1000 → таймаут ~1 с.
 * Reload в цикле каждые 200 мс — пятикратный запас. */
#include "cmsis_os2.h"
#include "stm32f4xx_ll_iwdg.h"

#define WATCHDOG_RELOAD_PERIOD_MS  200U
#define WATCHDOG_TIMEOUT_TICKS     1000U

static void watchdog_init(void) {
    LL_IWDG_Enable(IWDG);
    LL_IWDG_EnableWriteAccess(IWDG);
    LL_IWDG_SetPrescaler(IWDG, LL_IWDG_PRESCALER_32);
    LL_IWDG_SetReloadCounter(IWDG, WATCHDOG_TIMEOUT_TICKS);
    while (LL_IWDG_IsReady(IWDG) == 0U) { }
    LL_IWDG_ReloadCounter(IWDG);
}

void task_watchdog(void *argument) {
    (void)argument;
    watchdog_init();
    for (;;) {
        LL_IWDG_ReloadCounter(IWDG);
        osDelay(WATCHDOG_RELOAD_PERIOD_MS);
    }
}
