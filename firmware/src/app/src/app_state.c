#include "app_state.h"

static volatile app_state_t s_state = APP_STATE_BOOT;

app_state_t app_state_get(void)        { return s_state; }
void        app_state_set(app_state_t s){ s_state = s;    }