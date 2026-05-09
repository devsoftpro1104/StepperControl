#ifndef MW_SHELL_H
#define MW_SHELL_H

#include <stdint.h>
#include <stdbool.h>

/* Текстовый CLI-shell поверх UART. Парсер строк + диспетчер команд +
   эмиттер `+OK/-ERR/$/!` строк. См. подробное описание грамматики
   в docs/cli.md.

   Замечание по слоям: shell — это диспетчер команд приложения,
   поэтому он напрямую вызывает app/devices/drivers (исключение из
   правила «middleware → hal_port»). Описано в docs/architecture.md §5.5. */

void shell_init(void);
void shell_feed(uint8_t b);                  /* подаёт 1 принятый байт */

/* Эмиссия асинхронного события: shell_event("STATE %s", "MOVING") → !STATE MOVING\r\n */
void shell_event(const char *fmt, ...);

#endif /* MW_SHELL_H */
