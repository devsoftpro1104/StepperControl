#ifndef APP_MOTOR_SERVICE_H
#define APP_MOTOR_SERVICE_H

#include <stdint.h>
#include <stdbool.h>

/* Состояние мотора + управление потоком телеметрии $M.
   Telemetry-часть полностью реализована; управляющая (pos/speed/target/en/dir)
   пока stub — заполняется placeholder'ами до момента реализации task_motor.

   После запуска профиля движения task_motor должен будет вызывать
   motor_service_publish() с реальными значениями. */

#define MOTOR_PERIOD_MIN_MS    20U      /* 50 Hz — хватит для UI */
#define MOTOR_PERIOD_MAX_MS  60000U
#define MOTOR_PERIOD_DEFAULT  100U      /* 10 Hz по умолчанию */

#define MOTOR_RATE_MIN_HZ      1U
#define MOTOR_RATE_MAX_HZ     50U

/* FRW (forward)  = вращение по часовой стрелке (PIN_DIR LOW)
   BCK (backward) = против часовой                (PIN_DIR HIGH).
   Раньше эти направления назывались CW/CCW; перешли на FRW/BCK,
   потому что для пользователя «вперёд/назад» однозначнее, чем «по/против
   часовой» (зависит от того, с какого торца смотришь на мотор). Полярность
   GPIO не менялась — только имена. */
typedef enum {
    MOTOR_DIR_FRW = 0,
    MOTOR_DIR_BCK = 1,
} motor_dir_t;

void        motor_service_init(void);

bool        motor_service_running(void);
void        motor_service_start(void);
void        motor_service_stop(void);

uint32_t    motor_service_period_ms(void);
bool        motor_service_set_period_ms(uint32_t ms);
bool        motor_service_set_rate_hz(uint32_t hz);
uint32_t    motor_service_rate_hz(void);

/* Состояние двигателя. Обновляется задачей task_motor, читается всеми. */
int32_t     motor_service_position(void);        /* шагов от старта */
int32_t     motor_service_target(void);          /* шагов до цели  */
uint32_t    motor_service_speed_sps(void);       /* текущая заданная скорость */

bool        motor_service_en(void);
void        motor_service_set_en(bool on);       /* физически дёргает PIN_EN */

motor_dir_t motor_service_dir(void);
void        motor_service_set_dir(motor_dir_t d); /* физически дёргает PIN_DIR */

/* --- Оркестрация движения ---------------------------------------------- */
/* Вызывается из task_motor один раз: запоминается TaskHandle для уведомлений
   от ISR step_pwm. До этого motor_service_move() будет возвращать NOT_READY. */
void        motor_service_register_owner(void *task_handle);

typedef enum {
    MOTOR_OK = 0,
    MOTOR_ERR_BUSY,
    MOTOR_ERR_BAD_STEPS,
    MOTOR_ERR_BAD_SPEED,
    MOTOR_ERR_NOT_READY,
} motor_result_t;

/* Запустить движение: знак steps задаёт направление, |steps| — число шагов,
   speed_sps — постоянная скорость (профиль не реализован).
   Завершение придёт в task_motor через xTaskNotify (см. task_motor.c). */
motor_result_t motor_service_move(int32_t steps, uint32_t speed_sps);

/* Немедленный обрыв текущего движения. Безопасно вызывать всегда. */
void        motor_service_abort(void);

/* Обновить s_position по фактически выпущенным шагам. Вызывается ТОЛЬКО
   из task_motor (одиночный writer для s_position). */
void        motor_service_sync_position_from_pwm(void);

#endif /* APP_MOTOR_SERVICE_H */
