#ifndef DRV_STEP_PWM_H
#define DRV_STEP_PWM_H

#include <stdint.h>
#include <stdbool.h>

#include "FreeRTOS.h"
#include "task.h"

/* PWM-драйвер шагового мотора: TIM1_CH1 на PA8.
   Каждый период PWM = один шаг (передний фронт). Скорость задаётся через
   ARR. Когда задано фиксированное число шагов — UEV-ISR считает их и по
   достижении цели останавливает таймер + будит задачу через task notification.

   Профиль скорости (трапеция/S-curve) пока не реализован — движение идёт
   на постоянной скорости. См. docs/motor.md → секция «Что нужно реализовать
   дальше». */

/* Минимум/максимум — продиктованы PSC=167 (тик 1 МГц) и 16-бит ARR. */
#define STEP_PWM_MIN_SPS       16U          /* 1_000_000 / 65536 ≈ 15.3 → 16 с запасом */
#define STEP_PWM_MAX_SPS       200000U      /* 1_000_000 / 5,    совпадает с PROJ_MOTOR_MAX_SPEED_SPS */

void step_pwm_init(void);

/* Установить частоту шагов. Можно менять «на лету» — новое значение ARR
   подхватится при следующем UEV. false → sps вне диапазона. */
bool step_pwm_set_speed_sps(uint32_t sps);

/* Запустить выпуск ровно `steps` шагов на текущей скорости.
   notify_task — будем уведомлять её через xTaskNotify когда выпустим всё.
   Если уже идёт движение — false (ERR busy). */
bool step_pwm_start(uint32_t steps, TaskHandle_t notify_task);

/* Немедленный обрыв. Безопасно вызывать из любой задачи и из ISR. */
void step_pwm_stop(void);

/* true если в данный момент таймер активно выпускает шаги. */
bool step_pwm_busy(void);

/* Сколько шагов было фактически выпущено в текущем (или последнем) движении.
   Сбрасывается в 0 в начале step_pwm_start(). */
uint32_t step_pwm_emitted(void);

/* Сколько шагов осталось до конца текущего движения (или 0). */
uint32_t step_pwm_remaining(void);

#endif /* DRV_STEP_PWM_H */
