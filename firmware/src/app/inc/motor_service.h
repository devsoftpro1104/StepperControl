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

typedef enum {
    MOTOR_DIR_CW  = 0,
    MOTOR_DIR_CCW = 1,
} motor_dir_t;

void        motor_service_init(void);

bool        motor_service_running(void);
void        motor_service_start(void);
void        motor_service_stop(void);

uint32_t    motor_service_period_ms(void);
bool        motor_service_set_period_ms(uint32_t ms);
bool        motor_service_set_rate_hz(uint32_t hz);
uint32_t    motor_service_rate_hz(void);

/* Состояние двигателя (заполняется будущим профилировщиком). Сейчас все нули. */
int32_t     motor_service_position(void);        /* шагов от старта */
int32_t     motor_service_target(void);          /* шагов до цели  */
uint32_t    motor_service_speed_sps(void);       /* текущая скорость, шаг/с */

bool        motor_service_en(void);
void        motor_service_set_en(bool on);       /* физически дёргает PIN_EN */

motor_dir_t motor_service_dir(void);
void        motor_service_set_dir(motor_dir_t d); /* физически дёргает PIN_DIR */

#endif /* APP_MOTOR_SERVICE_H */
