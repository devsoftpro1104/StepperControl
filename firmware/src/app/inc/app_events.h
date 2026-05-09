#ifndef APP_EVENTS_H
#define APP_EVENTS_H

#include <stdint.h>

typedef enum {
    APP_EVT_NONE = 0,
    APP_EVT_PROTOCOL_FRAME,
    APP_EVT_MOTOR_DONE,
    APP_EVT_FAULT,
} app_event_id_t;

typedef struct {
    app_event_id_t id;
    uint32_t       arg;
} app_event_t;

#endif /* APP_EVENTS_H */