#ifndef USBD_CONF_H
#define USBD_CONF_H

#define USBD_MAX_NUM_INTERFACES         1
#define USBD_MAX_NUM_CONFIGURATION      1
#define USBD_MAX_STR_DESC_SIZ           512
#define USBD_SELF_POWERED               1
#define USBD_DEBUG_LEVEL                0

#define USBD_CDC_INTERVAL               2000

/* TODO: подключить ST USB Device middleware и привязать malloc/free */

#endif /* USBD_CONF_H */