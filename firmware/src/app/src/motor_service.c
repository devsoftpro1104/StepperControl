#include "motor_service.h"
#include "bsp_pins.h"

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
