#ifndef PROTOCOL_GEN_H
#define PROTOCOL_GEN_H
/* Сгенерировано из shared/protocol/protocol.yaml — НЕ РЕДАКТИРОВАТЬ ВРУЧНУЮ. */

#include <stdint.h>

#define PROTO_SOF        0xA5u
#define PROTO_VERSION    1u

typedef enum {
    CMD_PING             = 0x01,
    CMD_GET_VERSION      = 0x02,
    CMD_MOTOR_MOVE       = 0x10,
    CMD_MOTOR_STOP       = 0x11,
    STREAM_TELEMETRY     = 0x20,
} proto_cmd_t;

#endif /* PROTOCOL_GEN_H */