#include "step_pwm.h"
#include "bsp_pins.h"

#include "stm32f4xx.h"
#include "stm32f4xx_ll_bus.h"
#include "stm32f4xx_ll_gpio.h"
#include "stm32f4xx_ll_tim.h"

/* TIM1 на STM32F407: тактирование от APB2 timer clock = 168 МГц
   (PCLK2=84 МГц × 2, потому что APB2 prescaler != 1). PSC=167 → счётчик
   1 МГц (1 µs/тик). ARR — длительность одного шага в µs минус 1.

   sps = 1_000_000 / (ARR + 1)  ⇔  ARR = 1_000_000 / sps - 1

   CCR1 = ARR/2 для скважности 50 %; для типовых драйверов A4988/DRV8825
   достаточно min pulse width 1–2 µs, что соблюдается всегда (CCR1 ≥ 2 при
   максимальном sps=200000).

   Профиль скорости: пока не реализован. Скорость можно менять на лету
   step_pwm_set_speed_sps(); ARR с preload-битом подхватывается на UEV.

   Один UEV = один шаг (RCR=0). На максимальной скорости 200 кГц это
   до 7 % CPU из-за частых прерываний — приемлемо для V1. Когда понадобится
   снизить нагрузку — включить chunked-режим через RCR (RM0090 §17.3.18). */

#define STEP_TIMER_CLK_HZ      168000000U
#define STEP_TIMER_TICK_HZ     1000000U     /* PSC=167 → счётчик 1 МГц */
#define STEP_PSC_VALUE         (STEP_TIMER_CLK_HZ / STEP_TIMER_TICK_HZ - 1U)

/* Приоритет UEV-ISR: должен быть ≥ configMAX_SYSCALL_INTERRUPT_PRIORITY/16 = 5,
   иначе vTaskNotifyGiveFromISR упадёт в configASSERT. */
#define STEP_TIM1_IRQ_PRIO     6U

static volatile uint32_t      s_remaining;     /* шагов осталось в текущем движении */
static volatile uint32_t      s_emitted;       /* шагов уже выпущено (этого движения) */
static volatile bool          s_busy;
static          TaskHandle_t  s_notify_task;   /* кого будить на завершении */

static uint32_t sps_to_arr(uint32_t sps) {
    /* sps уже валидирован в set_speed_sps; здесь только арифметика. */
    return (STEP_TIMER_TICK_HZ / sps) - 1U;
}

void step_pwm_init(void) {
    LL_AHB1_GRP1_EnableClock(LL_AHB1_GRP1_PERIPH_GPIOA);
    LL_APB2_GRP1_EnableClock(LL_APB2_GRP1_PERIPH_TIM1);

    /* DIR/EN — обычные GPIO push-pull. Cold-state ODR=0:
       EN active-low → драйвер сразу enabled; DIR=0 → MOTOR_DIR_FRW.
       Семантика дёргается из motor_service (см. motor_service.c). */
    LL_GPIO_InitTypeDef g = {0};
    g.Mode       = LL_GPIO_MODE_OUTPUT;
    g.Speed      = LL_GPIO_SPEED_FREQ_LOW;
    g.OutputType = LL_GPIO_OUTPUT_PUSHPULL;
    g.Pull       = LL_GPIO_PULL_NO;
    g.Pin        = PIN_DIR_PIN;
    LL_GPIO_Init(PIN_DIR_PORT, &g);
    g.Pin        = PIN_EN_PIN;
    LL_GPIO_Init(PIN_EN_PORT, &g);

    /* STEP=PA8 → AF1 (TIM1_CH1). До step_pwm_start() MOE=0 — линия в Hi-Z. */
    g = (LL_GPIO_InitTypeDef){0};
    g.Pin        = PIN_STEP_PIN;
    g.Mode       = LL_GPIO_MODE_ALTERNATE;
    g.Speed      = LL_GPIO_SPEED_FREQ_HIGH;
    g.OutputType = LL_GPIO_OUTPUT_PUSHPULL;
    g.Pull       = LL_GPIO_PULL_NO;
    g.Alternate  = PIN_STEP_AF;
    LL_GPIO_Init(PIN_STEP_PORT, &g);

    /* Таймер: edge-aligned up-counting, ARR с preload (чтобы изменения скорости
       вступали в силу синхронно на UEV, без stutter в линии STEP). */
    LL_TIM_InitTypeDef t = {0};
    t.Prescaler         = STEP_PSC_VALUE;
    t.CounterMode       = LL_TIM_COUNTERMODE_UP;
    t.Autoreload        = sps_to_arr(1000U);    /* безопасный дефолт 1 кГц */
    t.ClockDivision     = LL_TIM_CLOCKDIVISION_DIV1;
    t.RepetitionCounter = 0;
    LL_TIM_Init(TIM1, &t);
    LL_TIM_EnableARRPreload(TIM1);

    /* CH1: PWM mode 1, OC active high, preload включен. */
    LL_TIM_OC_InitTypeDef oc = {0};
    oc.OCMode       = LL_TIM_OCMODE_PWM1;
    oc.OCState      = LL_TIM_OCSTATE_DISABLE;   /* включим вместе с MOE в start() */
    oc.OCNState     = LL_TIM_OCSTATE_DISABLE;
    oc.CompareValue = sps_to_arr(1000U) / 2U;   /* 50 % duty при дефолтных 1 кГц */
    oc.OCPolarity   = LL_TIM_OCPOLARITY_HIGH;
    LL_TIM_OC_Init(TIM1, LL_TIM_CHANNEL_CH1, &oc);
    LL_TIM_OC_EnablePreload(TIM1, LL_TIM_CHANNEL_CH1);

    /* UEV-прерывание для подсчёта шагов. */
    LL_TIM_EnableIT_UPDATE(TIM1);
    NVIC_SetPriority(TIM1_UP_TIM10_IRQn, STEP_TIM1_IRQ_PRIO);
    NVIC_EnableIRQ(TIM1_UP_TIM10_IRQn);

    /* Advanced timer: до того как реально пойдёт сигнал, нужно MOE=1 (BDTR).
       Включим только в start(); пока выходы Hi-Z, драйвер не получает «мусор». */
    LL_TIM_DisableAllOutputs(TIM1);
}

bool step_pwm_set_speed_sps(uint32_t sps) {
    if (sps < STEP_PWM_MIN_SPS || sps > STEP_PWM_MAX_SPS) return false;
    uint32_t arr = sps_to_arr(sps);
    /* preload: новые ARR/CCR подхватятся на следующий UEV → плавная смена. */
    LL_TIM_SetAutoReload(TIM1, arr);
    LL_TIM_OC_SetCompareCH1(TIM1, arr / 2U);
    return true;
}

bool step_pwm_start(uint32_t steps, TaskHandle_t notify_task) {
    if (steps == 0) return false;
    if (s_busy)     return false;

    s_remaining   = steps;
    s_emitted     = 0;
    s_notify_task = notify_task;
    s_busy        = true;

    /* Сбрасываем счётчик и фантомные UIF, иначе первый ISR прилетит сразу. */
    LL_TIM_SetCounter   (TIM1, 0);
    LL_TIM_GenerateEvent_UPDATE(TIM1);          /* перенести preload в shadow */
    LL_TIM_ClearFlag_UPDATE(TIM1);

    LL_TIM_CC_EnableChannel(TIM1, LL_TIM_CHANNEL_CH1);
    LL_TIM_EnableAllOutputs(TIM1);              /* MOE=1 — STEP оживает */
    LL_TIM_EnableCounter   (TIM1);
    return true;
}

void step_pwm_stop(void) {
    /* Порядок важен: сначала глушим выходы, потом счётчик — иначе можно
       поймать «полу-высокий» STEP, что у некоторых драйверов считается
       шагом. */
    LL_TIM_DisableAllOutputs(TIM1);
    LL_TIM_DisableCounter   (TIM1);
    LL_TIM_CC_DisableChannel(TIM1, LL_TIM_CHANNEL_CH1);
    s_remaining = 0;
    s_busy      = false;
}

bool     step_pwm_busy     (void) { return s_busy; }
uint32_t step_pwm_emitted  (void) { return s_emitted; }
uint32_t step_pwm_remaining(void) { return s_remaining; }

void TIM1_UP_TIM10_IRQHandler(void) {
    /* TIM10 шарит вектор, но мы его не используем — флаг проверяем только TIM1. */
    if (!LL_TIM_IsActiveFlag_UPDATE(TIM1)) return;
    LL_TIM_ClearFlag_UPDATE(TIM1);

    /* Один UEV = один полный цикл PWM = один передний фронт STEP в драйвере. */
    s_emitted++;
    if (s_remaining > 0) s_remaining--;

    if (s_remaining == 0) {
        /* Глушим прямо здесь — никаких лишних шагов после цели. */
        LL_TIM_DisableAllOutputs(TIM1);
        LL_TIM_DisableCounter   (TIM1);
        LL_TIM_CC_DisableChannel(TIM1, LL_TIM_CHANNEL_CH1);
        s_busy = false;

        if (s_notify_task != NULL) {
            BaseType_t hpw = pdFALSE;
            vTaskNotifyGiveFromISR(s_notify_task, &hpw);
            portYIELD_FROM_ISR(hpw);
        }
    }
}
