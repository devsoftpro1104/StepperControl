#include "shell.h"
#include "uart.h"
#include "app_state.h"
#include "bsp_version.h"
#include "project_config.h"
#include "temp_service.h"
#include "ds18b20.h"
#include "hall_service.h"
#include "ah49e.h"
#include "motor_service.h"

#include "stm32f4xx.h"           /* NVIC_SystemReset */
#include "FreeRTOS.h"
#include "task.h"

#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define SHELL_LINE_MAX  128U
#define SHELL_MAX_ARGS  8

static char     s_line[SHELL_LINE_MAX];
static uint16_t s_line_len;
static bool     s_overflow;

static void shell_write(const char *s, uint16_t n) {
    if (n) uart2_send((const uint8_t *)s, n);
}

static void shell_println(const char *s) {
    shell_write(s, (uint16_t)strlen(s));
    shell_write("\r\n", 2U);
}

static void shell_printf(const char *fmt, ...) {
    char buf[128];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    if (n < 0) return;
    if (n >= (int)sizeof(buf)) n = (int)sizeof(buf) - 1;
    shell_write(buf, (uint16_t)n);
    shell_write("\r\n", 2U);
}

void shell_event(const char *fmt, ...) {
    char buf[96];
    buf[0] = '!';
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(buf + 1, sizeof(buf) - 1, fmt, ap);
    va_end(ap);
    if (n < 0) return;
    if (n > (int)sizeof(buf) - 2) n = (int)sizeof(buf) - 2;
    shell_write(buf, (uint16_t)(n + 1));
    shell_write("\r\n", 2U);
}

static const char *state_name(app_state_t s) {
    switch (s) {
        case APP_STATE_BOOT:   return "BOOT";
        case APP_STATE_IDLE:   return "IDLE";
        case APP_STATE_MOVING: return "MOVING";
        case APP_STATE_FAULT:  return "FAULT";
        default:               return "UNKNOWN";
    }
}

static int tokenise(char *line, char *argv[], int max_argv) {
    int argc = 0;
    char *p = line;
    while (*p && argc < max_argv) {
        while (*p == ' ' || *p == '\t') *p++ = '\0';
        if (!*p) break;
        argv[argc++] = p;
        while (*p && *p != ' ' && *p != '\t') p++;
    }
    return argc;
}

static void to_upper_inplace(char *s) {
    for (; *s; ++s) if (*s >= 'a' && *s <= 'z') *s = (char)(*s - ('a' - 'A'));
}

static bool parse_long(const char *s, long *out) {
    char *end = NULL;
    long v = strtol(s, &end, 10);
    if (end == s || end == NULL || *end != '\0') return false;
    *out = v;
    return true;
}

/* ---- handlers --------------------------------------------------------- */

static void cmd_ping(int argc, char *argv[]) {
    (void)argc; (void)argv;
    shell_printf("+OK PING uptime=%lu", (unsigned long)xTaskGetTickCount());
}

static void cmd_ver(int argc, char *argv[]) {
    (void)argc; (void)argv;
    shell_printf("+OK VER %u.%u.%u",
                 (unsigned)FW_VERSION_MAJOR,
                 (unsigned)FW_VERSION_MINOR,
                 (unsigned)FW_VERSION_PATCH);
}

static void cmd_state(int argc, char *argv[]) {
    (void)argc; (void)argv;
    shell_printf("+OK STATE %s", state_name(app_state_get()));
}

static void cmd_move(int argc, char *argv[]) {
    if (argc != 4) { shell_println("-ERR MOVE usage MOVE <steps> <speed> <accel>"); return; }
    long steps, speed, accel;
    if (!parse_long(argv[1], &steps) ||
        !parse_long(argv[2], &speed) ||
        !parse_long(argv[3], &accel)) {
        shell_println("-ERR MOVE bad-number");
        return;
    }
    if (speed <= 0 || (uint32_t)speed > PROJ_MOTOR_MAX_SPEED_SPS) {
        shell_println("-ERR MOVE bad-speed");
        return;
    }
    if (accel <= 0) { shell_println("-ERR MOVE bad-accel"); return; }
    if (app_state_get() == APP_STATE_FAULT) { shell_println("-ERR MOVE fault"); return; }

    /* TODO: реальный enqueue профиля движения в task_motor */
    app_state_set(APP_STATE_MOVING);
    shell_event("STATE MOVING");
    shell_printf("+OK MOVE steps=%ld speed=%ld accel=%ld", steps, speed, accel);
}

static void cmd_stop(int argc, char *argv[]) {
    (void)argc; (void)argv;
    /* TODO: сигнал task_motor об аборте */
    if (app_state_get() != APP_STATE_FAULT) {
        app_state_set(APP_STATE_IDLE);
        shell_event("STATE IDLE");
    }
    shell_println("+OK STOP");
}

static void cmd_temp(int argc, char *argv[]) {
    if (argc < 2) { shell_println("-ERR TEMP usage TEMP ON|OFF|RATE <hz>|READ"); return; }
    to_upper_inplace(argv[1]);

    if (strcmp(argv[1], "READ") == 0) {
        /* Синхронное чтение: блокирует shell на ≈770 мс. Допустимо — shell
           обрабатывается в task_protocol, остальные задачи продолжают работать. */
        int16_t c10;
        ds18b20_status_t st = ds18b20_read_blocking(&c10);
        switch (st) {
            case DS18B20_OK: {
                temp_service_publish(c10);
                char tstr[8];
                temp_format_c10(tstr, sizeof(tstr), c10);
                shell_printf("+OK TEMP %s", tstr);
                break;
            }
            case DS18B20_NO_DEVICE: shell_println("-ERR TEMP no-device"); break;
            case DS18B20_BAD_CRC:   shell_println("-ERR TEMP bad-crc");   break;
            case DS18B20_BAD_VALUE: shell_println("-ERR TEMP bad-value"); break;
            default:                shell_println("-ERR TEMP unknown");   break;
        }
    } else if (strcmp(argv[1], "ON") == 0) {
        temp_service_start();
        shell_println("+OK TEMP ON");
    } else if (strcmp(argv[1], "OFF") == 0) {
        temp_service_stop();
        shell_println("+OK TEMP OFF");
    } else if (strcmp(argv[1], "RATE") == 0) {
        if (argc != 3) { shell_println("-ERR TEMP usage TEMP RATE <hz>"); return; }
        long hz;
        if (!parse_long(argv[2], &hz) || hz <= 0) {
            shell_println("-ERR TEMP bad-number");
            return;
        }
        if (!temp_service_set_rate_hz((uint32_t)hz)) {
            shell_printf("-ERR TEMP bad-rate min=%u max=%u",
                         (unsigned)TEMP_RATE_MIN_HZ,
                         (unsigned)TEMP_RATE_MAX_HZ);
            return;
        }
        shell_printf("+OK TEMP RATE %ld", hz);
    } else {
        shell_println("-ERR TEMP bad-arg");
    }
}

static void cmd_hall(int argc, char *argv[]) {
    if (argc < 2) { shell_println("-ERR HALL usage HALL ON|OFF|RATE <hz>|READ|ZERO|ZEROCLR"); return; }
    to_upper_inplace(argv[1]);

    if (strcmp(argv[1], "READ") == 0) {
        uint16_t raw = ah49e_read_raw();
        uint16_t mv  = ah49e_read_mv();
        int16_t  c   = ah49e_read_centered();
        hall_service_publish(raw, c);
        shell_printf("+OK HALL raw=%u mv=%u centered=%d", (unsigned)raw, (unsigned)mv, (int)c);
    } else if (strcmp(argv[1], "ON") == 0) {
        hall_service_start();
        shell_println("+OK HALL ON");
    } else if (strcmp(argv[1], "OFF") == 0) {
        hall_service_stop();
        shell_println("+OK HALL OFF");
    } else if (strcmp(argv[1], "RATE") == 0) {
        if (argc != 3) { shell_println("-ERR HALL usage HALL RATE <hz>"); return; }
        long hz;
        if (!parse_long(argv[2], &hz) || hz <= 0) {
            shell_println("-ERR HALL bad-number");
            return;
        }
        if (!hall_service_set_rate_hz((uint32_t)hz)) {
            shell_printf("-ERR HALL bad-rate min=%u max=%u",
                         (unsigned)HALL_RATE_MIN_HZ,
                         (unsigned)HALL_RATE_MAX_HZ);
            return;
        }
        shell_printf("+OK HALL RATE %ld", hz);
    } else if (strcmp(argv[1], "ZERO") == 0) {
        uint16_t z = ah49e_calibrate_zero();
        shell_printf("+OK HALL ZERO offset=%u", (unsigned)z);
    } else if (strcmp(argv[1], "ZEROCLR") == 0) {
        ah49e_clear_zero();
        shell_println("+OK HALL ZEROCLR");
    } else {
        shell_println("-ERR HALL bad-arg");
    }
}

/* --- MOTOR: телеметрия + bring-up GPIO --------------------------------- */

static void cmd_motor(int argc, char *argv[]) {
    if (argc < 2) { shell_println("-ERR MOTOR usage MOTOR ON|OFF|RATE <hz>|READ"); return; }
    to_upper_inplace(argv[1]);

    if (strcmp(argv[1], "READ") == 0) {
        shell_printf("+OK MOTOR pos=%ld speed=%lu target=%ld en=%s dir=%s",
                     (long)motor_service_position(),
                     (unsigned long)motor_service_speed_sps(),
                     (long)motor_service_target(),
                     motor_service_en() ? "on" : "off",
                     motor_service_dir() == MOTOR_DIR_CW ? "cw" : "ccw");
    } else if (strcmp(argv[1], "ON") == 0) {
        motor_service_start();
        shell_println("+OK MOTOR ON");
    } else if (strcmp(argv[1], "OFF") == 0) {
        motor_service_stop();
        shell_println("+OK MOTOR OFF");
    } else if (strcmp(argv[1], "RATE") == 0) {
        if (argc != 3) { shell_println("-ERR MOTOR usage MOTOR RATE <hz>"); return; }
        long hz;
        if (!parse_long(argv[2], &hz) || hz <= 0) {
            shell_println("-ERR MOTOR bad-number");
            return;
        }
        if (!motor_service_set_rate_hz((uint32_t)hz)) {
            shell_printf("-ERR MOTOR bad-rate min=%u max=%u",
                         (unsigned)MOTOR_RATE_MIN_HZ,
                         (unsigned)MOTOR_RATE_MAX_HZ);
            return;
        }
        shell_printf("+OK MOTOR RATE %ld", hz);
    } else {
        shell_println("-ERR MOTOR bad-arg");
    }
}

static void cmd_en(int argc, char *argv[]) {
    if (argc != 2) { shell_println("-ERR EN usage EN ON|OFF"); return; }
    to_upper_inplace(argv[1]);
    if (strcmp(argv[1], "ON") == 0) {
        motor_service_set_en(true);
        shell_println("+OK EN ON");
    } else if (strcmp(argv[1], "OFF") == 0) {
        motor_service_set_en(false);
        shell_println("+OK EN OFF");
    } else {
        shell_println("-ERR EN bad-arg");
    }
}

static void cmd_dir(int argc, char *argv[]) {
    if (argc != 2) { shell_println("-ERR DIR usage DIR CW|CCW"); return; }
    to_upper_inplace(argv[1]);
    if (strcmp(argv[1], "CW") == 0) {
        motor_service_set_dir(MOTOR_DIR_CW);
        shell_println("+OK DIR CW");
    } else if (strcmp(argv[1], "CCW") == 0) {
        motor_service_set_dir(MOTOR_DIR_CCW);
        shell_println("+OK DIR CCW");
    } else {
        shell_println("-ERR DIR bad-arg");
    }
}

static void cmd_moveto(int argc, char *argv[]) {
    (void)argc; (void)argv;
    /* TODO: абсолютное позиционирование. Требует профилировщика и
       калибровки нуля (HOME). Пока — заглушка. */
    shell_println("-ERR MOVETO not-implemented");
}

static void cmd_home(int argc, char *argv[]) {
    (void)argc; (void)argv;
    /* TODO: гомирование по концевику или Hall-индексу. Требует
       реализации task_motor + опроса HALL в реальном времени. */
    shell_println("-ERR HOME not-implemented");
}

static void cmd_help(int argc, char *argv[]) {
    (void)argc; (void)argv;
    shell_println("+OK HELP cmds=PING,VER,STATE,MOVE,MOVETO,STOP,HOME,EN,DIR,MOTOR,TEMP,HALL,HELP,RESET");
    shell_println("# MOVE   <steps:i32> <speed_sps:u32> <accel_sps2:u32>");
    shell_println("# MOVETO <pos:i32>                                    (TBD)");
    shell_println("# HOME                                                (TBD)");
    shell_println("# EN     ON|OFF                                       (GPIO PA10)");
    shell_println("# DIR    CW|CCW                                       (GPIO PA9)");
    shell_println("# MOTOR  ON|OFF|RATE <hz:1..50>|READ                  -> $M");
    shell_println("# TEMP   ON|OFF|RATE <hz:1..1>|READ                   -> $T18 (DS18B20)");
    shell_println("# HALL   ON|OFF|RATE <hz:1..100>|READ|ZERO|ZEROCLR    -> $H   (AH49E)");
    shell_println("# stream: $M,   <ts>, <pos>, <speed>, <target>, <en>, <dir>");
    shell_println("# stream: $T18, <ts>, <temp_c>");
    shell_println("# stream: $H,   <ts>, <raw>, <centered>");
    shell_println("# events: !STATE <name>  !FAULT <reason>  !DONE <what>");
}

static void cmd_reset(int argc, char *argv[]) {
    (void)argc; (void)argv;
    /* uart2_send блокирующий — к моменту возврата ответ уже физически в линии. */
    shell_println("+OK RESET");
    NVIC_SystemReset();
}

/* ---- dispatch --------------------------------------------------------- */

typedef struct {
    const char *name;
    void (*fn)(int argc, char *argv[]);
} shell_cmd_t;

static const shell_cmd_t s_cmds[] = {
    { "PING",   cmd_ping   },
    { "VER",    cmd_ver    },
    { "STATE",  cmd_state  },
    { "MOVE",   cmd_move   },
    { "MOVETO", cmd_moveto },
    { "STOP",   cmd_stop   },
    { "HOME",   cmd_home   },
    { "EN",     cmd_en     },
    { "DIR",    cmd_dir    },
    { "MOTOR",  cmd_motor  },
    { "TEMP",   cmd_temp   },
    { "HALL",   cmd_hall   },
    { "HELP",   cmd_help   },
    { "RESET",  cmd_reset  },
};

static void shell_dispatch(char *line) {
    char *argv[SHELL_MAX_ARGS];
    int argc = tokenise(line, argv, SHELL_MAX_ARGS);
    if (argc == 0) return;
    if (argv[0][0] == '#') return;            /* строка-комментарий — игнор */
    to_upper_inplace(argv[0]);
    for (size_t i = 0; i < sizeof(s_cmds) / sizeof(s_cmds[0]); ++i) {
        if (strcmp(argv[0], s_cmds[i].name) == 0) {
            s_cmds[i].fn(argc, argv);
            return;
        }
    }
    shell_printf("-ERR unknown %s", argv[0]);
}

void shell_init(void) {
    s_line_len = 0;
    s_overflow = false;
    shell_printf("# stepper_control %u.%u.%u ready",
                 (unsigned)FW_VERSION_MAJOR,
                 (unsigned)FW_VERSION_MINOR,
                 (unsigned)FW_VERSION_PATCH);
    shell_event("STATE %s", state_name(app_state_get()));
}

void shell_feed(uint8_t b) {
    if (b == '\r' || b == '\n') {
        if (s_overflow) {
            shell_println("-ERR line-too-long");
        } else if (s_line_len > 0) {
            s_line[s_line_len] = '\0';
            shell_dispatch(s_line);
        }
        s_line_len = 0;
        s_overflow = false;
        return;
    }
    if (s_overflow) return;
    if (s_line_len >= SHELL_LINE_MAX - 1U) { s_overflow = true; return; }
    s_line[s_line_len++] = (char)b;
}
