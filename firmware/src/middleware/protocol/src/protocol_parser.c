#include "protocol_parser.h"

struct proto_parser_s {
    uint32_t state;
    /* TODO: байтовый автомат разбора кадров */
};

void proto_parser_init(proto_parser_t *p) {
    if (p) p->state = 0;
}

proto_status_t proto_parser_feed(proto_parser_t *p, const uint8_t *data, size_t n,
                                 proto_frame_t *out) {
    (void)p; (void)data; (void)n; (void)out;
    /* TODO: реализация */
    return PROTO_NEED_MORE;
}