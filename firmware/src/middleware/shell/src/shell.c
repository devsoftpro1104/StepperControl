#include "shell.h"
#include "uart.h"
#include "app_state.h"
#include "bsp_version.h"
#include "project_config.h"
#include "temp_service.h"
#include "ds18b20.h"

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

static volatile bool     s_telem_on   = false;
static volatile uint16_t s_telem_rate = 50U;

bool     shell_telem_enabled(void) { return s_telem_on; }
uint16_t shell_telem_rate_hz(void) { return s_telem_rate; }

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

static void cmd_telem(int argc, char *argv[]) {
    if (argc < 2) { shell_println("-ERR TELEM usage TELEM ON|OFF|RATE <hz>"); return; }
    to_upper_inplace(argv[1]);
    if (strcmp(argv[1], "ON") == 0) {
        s_telem_on = true;
        shell_println("+OK TELEM ON");
    } else if (strcmp(argv[1], "OFF") == 0) {
        s_telem_on = false;
        shell_println("+OK TELEM OFF");
    } else if (strcmp(argv[1], "RATE") == 0) {
        if (argc != 3) { shell_println("-ERR TELEM usage TELEM RATE <hz>"); return; }
        long hz;
        if (!parse_long(argv[2], &hz) || hz < 1 || hz > 1000) {
            shell_println("-ERR TELEM bad-rate");
            return;
        }
        s_telem_rate = (uint16_t)hz;
        shell_printf("+OK TELEM RATE %ld", hz);
    } else {
        shell_println("-ERR TELEM bad-arg");
    }
}

static void cmd_temp(int argc, char *argv[]) {
    if (argc < 2) { shell_println("-ERR TEMP usage TEMP READ|START|STOP|PERIOD <ms>"); return; }
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
    } else if (strcmp(argv[1], "START") == 0) {
        temp_service_start();
        shell_println("+OK TEMP START");
    } else if (strcmp(argv[1], "STOP") == 0) {
        temp_service_stop();
        shell_println("+OK TEMP STOP");
    } else if (strcmp(argv[1], "PERIOD") == 0) {
        if (argc != 3) { shell_println("-ERR TEMP usage TEMP PERIOD <ms>"); return; }
        long ms;
        if (!parse_long(argv[2], &ms) || ms <= 0) {
            shell_println("-ERR TEMP bad-number");
            return;
        }
        if (!temp_service_set_period_ms((uint32_t)ms)) {
            shell_printf("-ERR TEMP bad-period min=%u max=%u",
                         (unsigned)TEMP_PERIOD_MIN_MS,
                         (unsigned)TEMP_PERIOD_MAX_MS);
            return;
        }
        shell_printf("+OK TEMP PERIOD %ld", ms);
    } else {
        shell_println("-ERR TEMP bad-arg");
    }
}

static void cmd_help(int argc, char *argv[]) {
    (void)argc; (void)argv;
    shell_println("+OK HELP cmds=PING,VER,STATE,MOVE,STOP,TELEM,TEMP,HELP,RESET");
    shell_println("# MOVE <steps:i32> <speed_sps:u32> <accel_sps2:u32>");
    shell_println("# TELEM ON|OFF|RATE <hz:1..1000>");
    shell_println("# TEMP READ|START|STOP|PERIOD <ms:800..60000>");
    shell_println("# stream:  $T, <ts_ms>, <pos>, <current>, <temp_c>");
    shell_println("# stream:  $T18, <ts_ms>, <temp_c>     (DS18B20)");
    shell_println("# events:  !STATE <name>  !FAULT <reason>  !DONE <what>");
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
    { "PING",  cmd_ping  },
    { "VER",   cmd_ver   },
    { "STATE", cmd_state },
    { "MOVE",  cmd_move  },
    { "STOP",  cmd_stop  },
    { "TELEM", cmd_telem },
    { "TEMP",  cmd_temp  },
    { "HELP",  cmd_help  },
    { "RESET", cmd_reset },
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
