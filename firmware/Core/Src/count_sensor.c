#include "count_sensor.h"
#include "board_pins.h"
#include "count_filter.h"
#include "count_bup.h"
#include "count_cnt5.h"
#include "tmc_step.h"
#include "stm32g0xx_hal.h"

enum {
    CH_BUP = 0,
    CH_CNT5 = 1,
    CH_NUM = 2
};

static count_filter_t s_f[CH_NUM];
static uint32_t       s_prev[CH_NUM];
static bool           s_ignore[CH_NUM]; /* kẹt / giắc trống */
static int            s_lock;           /* -1 hoặc CH_* */
static uint32_t       s_count;
static bool           s_jam_locked;

static bool pin_high_bup(void)
{
    return HAL_GPIO_ReadPin(PIN_BUP_Port, PIN_BUP_Pin) == GPIO_PIN_SET;
}

static bool pin_high_cnt5(void)
{
    return HAL_GPIO_ReadPin(PIN_CNT5_Port, PIN_CNT5_Pin) == GPIO_PIN_SET;
}

static void gpio_init_both(void)
{
    __HAL_RCC_GPIOA_CLK_ENABLE();

    GPIO_InitTypeDef g = {0};
    g.Mode = GPIO_MODE_INPUT;
    g.Pull = GPIO_PULLUP;

    g.Pin = PIN_BUP_Pin;
    HAL_GPIO_Init(PIN_BUP_Port, &g);
    g.Pin = PIN_CNT5_Pin;
    HAL_GPIO_Init(PIN_CNT5_Port, &g);
}

void count_sensor_init(void)
{
    count_filter_cfg_t cfg_bup = count_bup_profile();
    count_filter_cfg_t cfg_5v = count_cnt5_profile();

    count_filter_init(&s_f[CH_BUP], &cfg_bup);
    count_filter_init(&s_f[CH_CNT5], &cfg_5v);

    s_prev[CH_BUP] = 0;
    s_prev[CH_CNT5] = 0;
    s_ignore[CH_BUP] = false;
    s_ignore[CH_CNT5] = false;
    s_lock = -1;
    s_count = 0;
    s_jam_locked = false;

    gpio_init_both();
}

count_channel_t count_sensor_channel(void)
{
    if (s_lock == CH_BUP) {
        return COUNT_CH_BUP;
    }
    if (s_lock == CH_CNT5) {
        return COUNT_CH_CNT5;
    }
    return COUNT_CH_NONE;
}

void count_sensor_tick(void)
{
    uint32_t now = tmc_now_us();

    if (!s_ignore[CH_BUP]) {
        count_filter_feed(&s_f[CH_BUP], pin_high_bup(), now);
    }
    if (!s_ignore[CH_CNT5]) {
        count_filter_feed(&s_f[CH_CNT5], pin_high_cnt5(), now);
    }

    for (int ch = 0; ch < CH_NUM; ch++) {
        if (s_ignore[ch]) {
            continue;
        }

        /* Kẹt mức (giắc trống / LED luôn sáng) khi chưa khóa → bỏ kênh */
        if (count_filter_jam(&s_f[ch])) {
            if (s_lock < 0) {
                s_ignore[ch] = true;
                count_filter_clear_jam(&s_f[ch]);
                continue;
            }
            if (s_lock == ch) {
                s_jam_locked = true;
            }
            continue;
        }

        uint32_t c = count_filter_get(&s_f[ch]);
        if (c <= s_prev[ch]) {
            continue;
        }
        uint32_t delta = c - s_prev[ch];
        s_prev[ch] = c;

        if (s_lock < 0) {
            s_lock = ch; /* khóa kênh có xung hợp lệ đầu tiên */
        }
        if (s_lock == ch) {
            s_count += delta;
        }
        /* kênh kia có xung sau khi đã khóa → bỏ qua, không cộng */
    }
}

uint32_t count_sensor_get(void)
{
    return s_count;
}

void count_sensor_reset(void)
{
    count_filter_reset_count(&s_f[CH_BUP]);
    count_filter_reset_count(&s_f[CH_CNT5]);
    s_prev[CH_BUP] = 0;
    s_prev[CH_CNT5] = 0;
    s_ignore[CH_BUP] = false;
    s_ignore[CH_CNT5] = false;
    s_lock = -1;
    s_count = 0;
    s_jam_locked = false;
}

bool count_sensor_blocked(void)
{
    if (s_lock == CH_BUP) {
        return count_filter_blocked(&s_f[CH_BUP]);
    }
    if (s_lock == CH_CNT5) {
        return count_filter_blocked(&s_f[CH_CNT5]);
    }
    return count_filter_blocked(&s_f[CH_BUP])
        || count_filter_blocked(&s_f[CH_CNT5]);
}

bool count_sensor_jam(void)
{
    return s_jam_locked;
}

void count_sensor_clear_jam(void)
{
    s_jam_locked = false;
    count_filter_clear_jam(&s_f[CH_BUP]);
    count_filter_clear_jam(&s_f[CH_CNT5]);
}

uint32_t count_sensor_glitches(void)
{
    return count_filter_glitches(&s_f[CH_BUP])
         + count_filter_glitches(&s_f[CH_CNT5]);
}
