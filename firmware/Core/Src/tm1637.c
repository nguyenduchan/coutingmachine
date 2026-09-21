#include "tm1637.h"
#include "board_pins.h"
#include "stm32g0xx_hal.h"

/* TM1637 bit timing — module is 5V; STM32 3V3 usually OK on CLK/DIO */
#ifndef TM1637_BIT_DELAY_US
#define TM1637_BIT_DELAY_US  5u
#endif

#define TM1637_CMD_DATA   0x40u  /* auto-increment address */
#define TM1637_CMD_ADDR   0xC0u  /* start at DIG1 */
#define TM1637_CMD_DISP   0x80u  /* display off base */
#define TM1637_CMD_ON     0x88u  /* display on + brightness */

/* gfedcba — common cathode TM1637 */
static const uint8_t s_seg[16] = {
    0x3f, 0x06, 0x5b, 0x4f, 0x66, 0x6d, 0x7d, 0x07, /* 0-7 */
    0x7f, 0x6f, 0x77, 0x7c, 0x39, 0x5e, 0x79, 0x71  /* 8-9 A-F */
};

#define SEG_BLANK  0x00u

static uint8_t s_brightness = 4;

static void delay_us(uint32_t us)
{
    uint32_t mhz = SystemCoreClock / 1000000u;
    if (mhz == 0u) {
        mhz = 16u;
    }
    uint32_t cycles = us * mhz;
    while (cycles--) {
        __NOP();
    }
}

static void clk_write(GPIO_PinState s)
{
    HAL_GPIO_WritePin(PIN_TM1637_CLK_Port, PIN_TM1637_CLK_Pin, s);
}

static void dio_write(GPIO_PinState s)
{
    HAL_GPIO_WritePin(PIN_TM1637_DIO_Port, PIN_TM1637_DIO_Pin, s);
}

static void dio_as_output(void)
{
    GPIO_InitTypeDef g = {0};
    g.Pin = PIN_TM1637_DIO_Pin;
    g.Mode = GPIO_MODE_OUTPUT_OD; /* open-drain for ACK */
    g.Pull = GPIO_PULLUP;
    g.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(PIN_TM1637_DIO_Port, &g);
}

static void start_cond(void)
{
    dio_as_output();
    dio_write(GPIO_PIN_SET);
    clk_write(GPIO_PIN_SET);
    delay_us(TM1637_BIT_DELAY_US);
    dio_write(GPIO_PIN_RESET);
    delay_us(TM1637_BIT_DELAY_US);
    clk_write(GPIO_PIN_RESET);
}

static void stop_cond(void)
{
    clk_write(GPIO_PIN_RESET);
    dio_as_output();
    dio_write(GPIO_PIN_RESET);
    delay_us(TM1637_BIT_DELAY_US);
    clk_write(GPIO_PIN_SET);
    delay_us(TM1637_BIT_DELAY_US);
    dio_write(GPIO_PIN_SET);
    delay_us(TM1637_BIT_DELAY_US);
}

static void write_byte(uint8_t b)
{
    dio_as_output();
    for (unsigned i = 0; i < 8u; i++) {
        clk_write(GPIO_PIN_RESET);
        delay_us(TM1637_BIT_DELAY_US);
        dio_write((b & 1u) ? GPIO_PIN_SET : GPIO_PIN_RESET);
        delay_us(TM1637_BIT_DELAY_US);
        clk_write(GPIO_PIN_SET);
        delay_us(TM1637_BIT_DELAY_US);
        b >>= 1;
    }
    /* ACK clock — release DIO (OD + PU), slave pulls low */
    clk_write(GPIO_PIN_RESET);
    dio_write(GPIO_PIN_SET);
    delay_us(TM1637_BIT_DELAY_US);
    clk_write(GPIO_PIN_SET);
    delay_us(TM1637_BIT_DELAY_US);
    clk_write(GPIO_PIN_RESET);
}

static void write_cmd(uint8_t cmd)
{
    start_cond();
    write_byte(cmd);
    stop_cond();
}

static void write_digits_raw(const uint8_t seg[4])
{
    write_cmd(TM1637_CMD_DATA);
    start_cond();
    write_byte(TM1637_CMD_ADDR);
    for (unsigned i = 0; i < 4u; i++) {
        write_byte(seg[i]);
    }
    stop_cond();
    write_cmd((uint8_t)(TM1637_CMD_ON | (s_brightness & 7u)));
}

void tm1637_init(void)
{
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOD_CLK_ENABLE();

    GPIO_InitTypeDef g = {0};
    g.Mode = GPIO_MODE_OUTPUT_OD;
    g.Pull = GPIO_PULLUP;
    g.Speed = GPIO_SPEED_FREQ_LOW;

    g.Pin = PIN_TM1637_CLK_Pin;
    HAL_GPIO_Init(PIN_TM1637_CLK_Port, &g);
    g.Pin = PIN_TM1637_DIO_Pin;
    HAL_GPIO_Init(PIN_TM1637_DIO_Port, &g);

    clk_write(GPIO_PIN_SET);
    dio_write(GPIO_PIN_SET);
    s_brightness = 4;
    tm1637_clear();
}

void tm1637_set_brightness(uint8_t level)
{
    if (level > 7u) {
        level = 7u;
    }
    s_brightness = level;
    write_cmd((uint8_t)(TM1637_CMD_ON | s_brightness));
}

void tm1637_display_on(bool on)
{
    if (on) {
        write_cmd((uint8_t)(TM1637_CMD_ON | (s_brightness & 7u)));
    } else {
        write_cmd(TM1637_CMD_DISP); /* display off, brightness bits ignored */
    }
}

void tm1637_clear(void)
{
    uint8_t z[4] = { SEG_BLANK, SEG_BLANK, SEG_BLANK, SEG_BLANK };
    write_digits_raw(z);
}

void tm1637_show_digits(const uint8_t dig[4])
{
    uint8_t seg[4];
    for (unsigned i = 0; i < 4u; i++) {
        if (dig[i] > 15u) {
            seg[i] = SEG_BLANK;
        } else {
            seg[i] = s_seg[dig[i]];
        }
    }
    write_digits_raw(seg);
}

void tm1637_show_uint(uint32_t value, bool leading_zero)
{
    value %= 10000u;
    uint8_t dig[4];
    dig[0] = (uint8_t)((value / 1000u) % 10u);
    dig[1] = (uint8_t)((value / 100u) % 10u);
    dig[2] = (uint8_t)((value / 10u) % 10u);
    dig[3] = (uint8_t)(value % 10u);

    if (!leading_zero) {
        bool blank = true;
        for (unsigned i = 0; i < 3u; i++) {
            if (blank && dig[i] == 0u) {
                dig[i] = 0x10u; /* blank sentinel for show_digits */
            } else {
                blank = false;
            }
        }
    }
    tm1637_show_digits(dig);
}
