#include "onewire.h"
#include "bsp_pins.h"

#include "stm32f4xx.h"
#include "stm32f4xx_ll_bus.h"
#include "stm32f4xx_ll_gpio.h"

/* Тайминги Standard speed (Maxim AN-126), мкс. */
#define OW_T_A   6U      /* write-1 low / read-init low */
#define OW_T_B   64U     /* write-1 high tail */
#define OW_T_C   60U     /* write-0 low */
#define OW_T_D   10U     /* write-0 recovery */
#define OW_T_E   9U      /* read sample delay (после release к моменту t≈15мкс) */
#define OW_T_F   55U     /* read tail */
#define OW_T_H   480U    /* reset low */
#define OW_T_I   70U     /* reset wait → presence sample */
#define OW_T_J   410U    /* reset recovery */

#define OW_PORT  PIN_DS18B20_PORT
#define OW_PIN   PIN_DS18B20_PIN

static uint32_t s_cyc_per_us;

static inline void ow_low(void)   { LL_GPIO_ResetOutputPin(OW_PORT, OW_PIN); }
static inline void ow_release(void){ LL_GPIO_SetOutputPin (OW_PORT, OW_PIN); }
static inline int  ow_sample(void){ return LL_GPIO_IsInputPinSet(OW_PORT, OW_PIN) ? 1 : 0; }

static inline void delay_us(uint32_t us) {
    uint32_t start  = DWT->CYCCNT;
    uint32_t target = us * s_cyc_per_us;
    while ((DWT->CYCCNT - start) < target) { }
}

static void dwt_enable(void) {
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CYCCNT = 0;
    DWT->CTRL  |= DWT_CTRL_CYCCNTENA_Msk;
    s_cyc_per_us = SystemCoreClock / 1000000U;
    if (s_cyc_per_us == 0U) s_cyc_per_us = 1U;   /* paranoia */
}

void ow_init(void) {
    LL_AHB1_GRP1_EnableClock(LL_AHB1_GRP1_PERIPH_GPIOB);

    /* Open-drain: «1» = шина отпущена и подтянута внешним резистором,
       «0» = MCU притягивает в землю. Так получается single-master 1-Wire. */
    LL_GPIO_InitTypeDef g = {0};
    g.Pin        = OW_PIN;
    g.Mode       = LL_GPIO_MODE_OUTPUT;
    g.OutputType = LL_GPIO_OUTPUT_OPENDRAIN;
    g.Speed      = LL_GPIO_SPEED_FREQ_HIGH;
    g.Pull       = LL_GPIO_PULL_UP;
    LL_GPIO_Init(OW_PORT, &g);

    ow_release();
    dwt_enable();
}

bool ow_reset(void) {
    bool present;
    __disable_irq();
    ow_low();
    delay_us(OW_T_H);
    ow_release();
    delay_us(OW_T_I);
    present = (ow_sample() == 0);    /* устройство тянет шину в 0 = «я на месте» */
    delay_us(OW_T_J);
    __enable_irq();
    return present;
}

static inline void ow_write_bit_locked(int bit) {
    if (bit) {
        ow_low();
        delay_us(OW_T_A);
        ow_release();
        delay_us(OW_T_B);
    } else {
        ow_low();
        delay_us(OW_T_C);
        ow_release();
        delay_us(OW_T_D);
    }
}

static inline int ow_read_bit_locked(void) {
    ow_low();
    delay_us(OW_T_A);
    ow_release();
    delay_us(OW_T_E);
    int bit = ow_sample();
    delay_us(OW_T_F);
    return bit;
}

void ow_write_byte(uint8_t b) {
    __disable_irq();
    for (int i = 0; i < 8; ++i) {
        ow_write_bit_locked(b & 0x01);
        b >>= 1;
    }
    __enable_irq();
}

uint8_t ow_read_byte(void) {
    uint8_t b = 0;
    __disable_irq();
    for (int i = 0; i < 8; ++i) {
        if (ow_read_bit_locked()) b |= (uint8_t)(1U << i);
    }
    __enable_irq();
    return b;
}

void ow_read_bytes(uint8_t *out, size_t n) {
    for (size_t i = 0; i < n; ++i) out[i] = ow_read_byte();
}
