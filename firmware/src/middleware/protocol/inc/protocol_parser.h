#ifndef PROTOCOL_PARSER_H
#define PROTOCOL_PARSER_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

typedef struct {
    uint8_t  cmd;
    uint8_t  seq;
    uint16_t len;
    const uint8_t *payload;
} proto_frame_t;

typedef enum {
    PROTO_OK         = 0,
    PROTO_NEED_MORE,
    PROTO_BAD_CRC,
    PROTO_BAD_SOF,
    PROTO_OVERFLOW,
} proto_status_t;

typedef struct proto_parser_s proto_parser_t;

void           proto_parser_init(proto_parser_t *p);
proto_status_t proto_parser_feed(proto_parser_t *p, const uint8_t *data, size_t n,
                                 proto_frame_t *out);

#endif /* PROTOCOL_PARSER_H */