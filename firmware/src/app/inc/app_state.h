#ifndef APP_STATE_H
#define APP_STATE_H

#include <stdint.h>
#include <stdbool.h>

typedef enum {
    APP_STATE_BOOT = 0,
    APP_STATE_IDLE,
    APP_STATE_MOVING,
    APP_STATE_FAULT,
} app_state_t;

app_state_t app_state_get(void);
void        app_state_set(app_state_t s);

#endif /* APP_STATE_H */