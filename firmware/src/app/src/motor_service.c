#include "motor_service.h"
#include "bsp_pins.h"
#include "step_pwm.h"

#include "FreeRTOS.h"
#include "task.h"

#include "stm32f4xx_ll_gpio.h"

/* Stub-сервис для мотора. Реальные pos/speed/target подставит task_motor,
   когда будет реализован профилировщик движения. EN/DIR — это просто GPIO
   и работают по-настоящему уже сейчас (нужно для bring-up'а драйвера). */

static volatile bool     s_running    = false;
static volatile uint32_t s_period_ms  = MOTOR_PERIOD_DEFAULT;

/* Заглушки под будущие реальные значения. Объявлены volatile, чтобы будущий
   writer (task_motor) не упёрся в гонку — на 32-bit M4 одиночный store/load
   atomic, мьютекс не нужен. */
static volatile int32_t  s_position   = 0;
static volatile int32_t  s_target     = 0;
static volatile uint32_t s_speed_sps  = 0;

static volatile bool        s_en      = false;
static volatile motor_dir_t s_dir     = MOTOR_DIR_CW;

/* Оркестрация движения. Все эти поля пишутся ТОЛЬКО из контекста, который
   уже эксклюзивно владеет motor_service (либо task_motor, либо команда CLI
   при step_pwm не busy). volatile достаточно. */
static          TaskHandle_t s_owner_task         = NULL;
static volatile int8_t       s_move_dir_sign      = +1;     /* +1 / -1 */
static volatile uint32_t     s_last_emitted_seen  = 0;

void motor_service_init(void) {
    s_running   = false;
    s_period_ms = MOTOR_PERIOD_DEFAULT;
    /* GPIO PA9/PA10 уже инициализированы как PUSH-PULL outputs в bsp.c.
       Сразу выставим логические дефолты: EN=OFF (driver disabled), DIR=CW. */
    motor_service_set_en (false);
    motor_service_set_dir(MOTOR_DIR_CW);
}

bool     motor_service_running(void)    { return s_running; }
void     motor_service_start(void)      { s_running = true; }
void     motor_service_stop(void)       { s_running = false; }
uint32_t motor_service_period_ms(void)  { return s_period_ms; }

bool motor_service_set_period_ms(uint32_t ms) {
    if (ms < MOTOR_PERIOD_MIN_MS || ms > MOTOR_PERIOD_MAX_MS) return false;
    s_period_ms = ms;
    return true;
}

bool motor_service_set_rate_hz(uint32_t hz) {
    if (hz < MOTOR_RATE_MIN_HZ || hz > MOTOR_RATE_MAX_HZ) return false;
    return motor_service_set_period_ms(1000U / hz);
}

uint32_t motor_service_rate_hz(void) {
    return (1000U + s_period_ms / 2U) / s_period_ms;
}

int32_t  motor_service_position (void) { return s_position;  }
int32_t  motor_service_target   (void) { return s_target;    }
uint32_t motor_service_speed_sps(void) { return s_speed_sps; }

bool motor_service_en(void) { return s_en; }

void motor_service_set_en(bool on) {
    s_en = on;
    /* EN на типовых драйверах (A4988/DRV8825) active-LOW. ON = pin LOW. */
    if (on) LL_GPIO_ResetOutputPin(PIN_EN_PORT, PIN_EN_PIN);
    else    LL_GPIO_SetOutputPin  (PIN_EN_PORT, PIN_EN_PIN);
}

motor_dir_t motor_service_dir(void) { return s_dir; }

void motor_service_set_dir(motor_dir_t d) {
    s_dir = d;
    if (d == MOTOR_DIR_CW) LL_GPIO_ResetOutputPin(PIN_DIR_PORT, PIN_DIR_PIN);
    else                   LL_GPIO_SetOutputPin  (PIN_DIR_PORT, PIN_DIR_PIN);
}

void motor_service_register_owner(void *task_handle) {
    s_owner_task = (TaskHandle_t)task_handle;
}

motor_result_t motor_service_move(int32_t steps, uint32_t speed_sps) {
    if (s_owner_task == NULL)               return MOTOR_ERR_NOT_READY;
    if (step_pwm_busy())                    return MOTOR_ERR_BUSY;
    if (steps == 0)                         return MOTOR_ERR_BAD_STEPS;
    if (!step_pwm_set_speed_sps(speed_sps)) return MOTOR_ERR_BAD_SPEED;

    motor_dir_t  d = (steps > 0) ? MOTOR_DIR_CW : MOTOR_DIR_CCW;
    motor_service_set_dir(d);
    motor_service_set_en(true);

    uint32_t abs_steps = (uint32_t)((steps > 0) ? steps : -steps);

    s_speed_sps         = speed_sps;
    s_target            = s_position + steps;
    s_move_dir_sign     = (steps > 0) ? +1 : -1;
    s_last_emitted_seen = 0;

    if (!step_pwm_start(abs_steps, s_owner_task)) return MOTOR_ERR_BUSY;
    return MOTOR_OK;
}

void motor_service_sync_position_from_pwm(void) {
    /* Дельта от прошлой синхронизации, с учётом направления. Один writer
       (task_motor) → лишних блокировок не нужно. */
    uint32_t e = step_pwm_emitted();
    uint32_t delta_unsigned = e - s_last_emitted_seen;
    s_last_emitted_seen = e;
    s_position += (int32_t)delta_unsigned * s_move_dir_sign;
    s_speed_sps = step_pwm_busy() ? s_speed_sps : 0;
}

void motor_service_abort(void) {
    step_pwm_stop();
    motor_service_sync_position_from_pwm();   /* учесть всё, что успело выйти */
    s_target    = s_position;                  /* мы там, где остановились */
    s_speed_sps = 0;
}
