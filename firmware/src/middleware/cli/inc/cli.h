#ifndef MW_CLI_H
#define MW_CLI_H

#include <stdint.h>
#include <stdbool.h>

/* Текстовый CLI поверх UART. Грамматика — строки в ASCII, разделитель \r или \n
   (или \r\n). Парсер хоста (PySide6) должен читать построчно и различать ответы
   по первому символу:

       +OK ...        — успешный ответ на команду
       -ERR ...       — ошибка выполнения команды
       $T,...         — сэмпл стрима телеметрии (CSV)
       !EVENT ...     — асинхронное событие (смена состояния, fault, done)
       # ...          — комментарий/баннер, можно игнорировать

   Команды:
       PING                          → +OK PING uptime=<ms>
       VER                           → +OK VER <maj>.<min>.<patch>
       STATE                         → +OK STATE BOOT|IDLE|MOVING|FAULT
       MOVE <steps> <speed> <accel>  → +OK MOVE ... | -ERR MOVE <reason>
       STOP                          → +OK STOP
       TELEM ON|OFF                  → +OK TELEM ON|OFF
       TELEM RATE <hz>               → +OK TELEM RATE <hz>          (1..1000)
       HELP                          → +OK HELP ...
       RESET                         → +OK RESET     (далее MCU перезагружается)

   Формат стрима телеметрии (когда TELEM ON):
       $T,<ts_ms>,<position>,<current>,<temp_c10>\r\n
       где temp_c10 = температура × 10 (десятые доли °C, знаковое). */

void cli_init(void);
void cli_feed(uint8_t b);                   /* подаёт 1 принятый байт */

bool     cli_telem_enabled(void);           /* true если TELEM ON */
uint16_t cli_telem_rate_hz(void);           /* текущая частота, Гц */

/* Эмиссия асинхронного события: cli_event("STATE %s", "MOVING") → !STATE MOVING\r\n */
void cli_event(const char *fmt, ...);

#endif /* MW_CLI_H */
