/**
 * Count UI — state machine (switch/case).
 *
 *   Giữ D ≥800ms → nhập RPM (≤ COUNT_UI_RPM_MAX), hiện TM1637, A=lưu
 *   Thả D sớm     → SET target
 *   C=XẢ · A=START · B=STOP · #=xem set · *=xem tổng
 */
#include "app_count_ui.h"
#include "board_config.h"
#include "board_motors.h"
#include "board_pins.h"
#include "count_sensor.h"
#include "tm1637.h"
#include "stm32g0xx_hal.h"

#ifndef COUNT_UI_BLINK_MS
#define COUNT_UI_BLINK_MS  400u
#endif

typedef enum {
    ST_IDLE = 0,
    ST_SET,
    ST_RPM,
    ST_RUN,
    ST_DUMP,
    ST_DONE,
    ST_PEEK_SET,
    ST_PEEK_TOTAL
} ui_state_t;

static ui_state_t s_state;
static ui_state_t s_peek_return;
static uint32_t   s_target;
static uint32_t   s_entry;
static bool       s_entry_fresh;
static uint32_t   s_total;
static uint32_t   s_last_run;
static uint32_t   s_peek_until;
static uint32_t   s_last_object_ms;
static bool       s_blink_phase;
static uint32_t   s_blink_ms;
static bool       s_stalling;
static uint32_t   s_rpm_fast;       /* tốc độ max đang dùng (≤ RPM_MAX) */

static bool       s_d_down;
static uint32_t   s_d_down_ms;
static bool       s_d_long_fired;

static void disc_stop(void);
static void disc_run_rpm(uint32_t rpm);
static void apply_speed_for_remaining(uint32_t remaining);
static uint32_t clamp_rpm(uint32_t rpm);
static void display_for_state(void);
static void goto_state(ui_state_t next);
static void begin_peek(ui_state_t peek, uint32_t value);
static void end_peek(void);
static void stall_reset(void);
static void stall_update(void);
static void action_start(void);
static void action_dump(void);
static void action_stop(void);
static void action_enter_set(void);
static void action_enter_rpm(void);
static void action_save_rpm(void);
static void action_clear_entry(void);
static void action_digit(char ch);
static void on_key_d_press(void);
static void on_key_d_release(void);
static void on_key_idle(const keypad_event_t *ev);
static void on_key_set(const keypad_event_t *ev);
static void on_key_rpm(const keypad_event_t *ev);
static void on_key_run(const keypad_event_t *ev);
static void on_key_dump(const keypad_event_t *ev);
static void on_key_done(const keypad_event_t *ev);
static void on_key_peek(const keypad_event_t *ev);
static void tick_counting(bool ignore_target);
static void tick_peek(void);
static void tick_d_long(void);

static uint32_t clamp_rpm(uint32_t rpm)
{
    if (rpm > COUNT_UI_RPM_MAX) {
        return COUNT_UI_RPM_MAX;
    }
    if (rpm < COUNT_UI_RPM_ENTRY_MIN) {
        return COUNT_UI_RPM_ENTRY_MIN;
    }
    return rpm;
}

static void disc_stop(void)
{
    motors_stop_all();
}

static void disc_run_rpm(uint32_t rpm)
{
    if (rpm < COUNT_UI_RPM_MIN) {
        rpm = COUNT_UI_RPM_MIN;
    }
    if (rpm > s_rpm_fast) {
        rpm = s_rpm_fast;
    }
    motors_run_counting(rpm);
}

static void apply_speed_for_remaining(uint32_t remaining)
{
    if (remaining == 0u) {
        disc_stop();
        return;
    }
    if (remaining >= COUNT_UI_SLOW_ZONE) {
        disc_run_rpm(s_rpm_fast);
        return;
    }
    uint32_t span = (COUNT_UI_SLOW_ZONE > 1u) ? (COUNT_UI_SLOW_ZONE - 1u) : 1u;
    uint32_t rpm = COUNT_UI_RPM_MIN
        + ((s_rpm_fast - COUNT_UI_RPM_MIN) * (remaining - 1u)) / span;
    disc_run_rpm(rpm);
}

static void stall_reset(void)
{
    s_last_object_ms = HAL_GetTick();
    s_stalling = false;
    s_blink_phase = true;
    s_blink_ms = HAL_GetTick();
    tm1637_display_on(true);
}

static void stall_update(void)
{
    uint32_t now = HAL_GetTick();

    if ((uint32_t)(now - s_last_object_ms) < COUNT_UI_STALL_MS) {
        if (s_stalling) {
            s_stalling = false;
            tm1637_display_on(true);
            display_for_state();
        }
        return;
    }

    s_stalling = true;
    if ((uint32_t)(now - s_blink_ms) >= COUNT_UI_BLINK_MS) {
        s_blink_ms = now;
        s_blink_phase = !s_blink_phase;
        tm1637_display_on(s_blink_phase);
    }
}

static void display_for_state(void)
{
    switch (s_state) {
    case ST_SET:
        tm1637_show_uint(s_entry, false);
        break;
    case ST_RPM:
        tm1637_show_uint(s_entry, false);
        break;
    case ST_PEEK_SET:
        tm1637_show_uint(s_target, false);
        break;
    case ST_PEEK_TOTAL:
        tm1637_show_uint(s_total % 10000u, false);
        break;
    case ST_IDLE:
    case ST_RUN:
    case ST_DUMP:
    case ST_DONE:
    default:
        tm1637_show_uint(count_sensor_get(), false);
        break;
    }
}

static void goto_state(ui_state_t next)
{
    s_state = next;
    tm1637_display_on(true);
    s_stalling = false;
    display_for_state();
}

static void begin_peek(ui_state_t peek, uint32_t value)
{
    switch (s_state) {
    case ST_PEEK_SET:
    case ST_PEEK_TOTAL:
        break;
    default:
        s_peek_return = s_state;
        break;
    }
    s_state = peek;
    s_peek_until = HAL_GetTick() + 2000u;
    tm1637_display_on(true);
    tm1637_show_uint(value, false);
}

static void end_peek(void)
{
    goto_state(s_peek_return);
}

static void action_start(void)
{
    if (s_state == ST_SET) {
        s_target = s_entry;
        s_entry_fresh = true;
    }
    if (s_target == 0u) {
        goto_state(ST_IDLE);
        return;
    }

    count_sensor_reset();
    count_sensor_clear_jam();
    HAL_GPIO_WritePin(PIN_LED_ERR_Port, PIN_LED_ERR_Pin, GPIO_PIN_RESET);
    s_last_run = 0;
    s_state = ST_RUN;
    stall_reset();
    tm1637_show_uint(0, false);
    apply_speed_for_remaining(s_target);
}

static void action_dump(void)
{
    count_sensor_reset();
    count_sensor_clear_jam();
    HAL_GPIO_WritePin(PIN_LED_ERR_Port, PIN_LED_ERR_Pin, GPIO_PIN_RESET);
    s_last_run = 0;
    s_state = ST_DUMP;
    stall_reset();
    tm1637_show_uint(0, false);
    disc_run_rpm(s_rpm_fast);
}

static void action_stop(void)
{
    disc_stop();
    goto_state(ST_IDLE);
}

static void action_enter_set(void)
{
    disc_stop();
    s_entry = s_target;
    s_entry_fresh = true;
    goto_state(ST_SET);
}

static void action_enter_rpm(void)
{
    disc_stop();
    s_entry = s_rpm_fast;
    s_entry_fresh = true;
    goto_state(ST_RPM);
}

static void action_save_rpm(void)
{
    s_rpm_fast = clamp_rpm(s_entry);
    s_entry = s_rpm_fast;
    s_entry_fresh = true;
    tm1637_show_uint(s_rpm_fast, false);
    goto_state(ST_IDLE);
    tm1637_show_uint(s_rpm_fast, false); /* flash giá trị đã lưu */
}

static void action_clear_entry(void)
{
    s_entry = 0;
    s_entry_fresh = true;
    tm1637_show_uint(0, false);
}

static void action_digit(char ch)
{
    uint8_t d = (uint8_t)(ch - '0');
    if (s_entry_fresh) {
        s_entry = d;
        s_entry_fresh = false;
    } else {
        uint32_t n = s_entry * 10u + d;
        if (s_state == ST_RPM) {
            if (n > COUNT_UI_RPM_MAX) {
                n = COUNT_UI_RPM_MAX;
            }
        } else if (n > 9999u) {
            n = 9999u;
        }
        s_entry = n;
    }
    if (s_state == ST_RPM && s_entry > COUNT_UI_RPM_MAX) {
        s_entry = COUNT_UI_RPM_MAX;
    }
    tm1637_show_uint(s_entry, false);
}

static void on_key_d_press(void)
{
    s_d_down = true;
    s_d_down_ms = HAL_GetTick();
    s_d_long_fired = false;
}

static void on_key_d_release(void)
{
    if (!s_d_down) {
        return;
    }
    s_d_down = false;
    if (s_d_long_fired) {
        return; /* đã vào RPM */
    }
    /* nhấn ngắn → SET target (không khi đang RUN/DUMP) */
    switch (s_state) {
    case ST_RUN:
    case ST_DUMP:
        break;
    default:
        action_enter_set();
        break;
    }
}

static void tick_d_long(void)
{
    if (!s_d_down || s_d_long_fired) {
        return;
    }
    if ((uint32_t)(HAL_GetTick() - s_d_down_ms) < COUNT_UI_SET_LONG_MS) {
        return;
    }
    s_d_long_fired = true;
    switch (s_state) {
    case ST_RUN:
    case ST_DUMP:
        break; /* đang chạy: bỏ qua long-press */
    default:
        action_enter_rpm();
        break;
    }
}

static void on_key_idle(const keypad_event_t *ev)
{
    if (ev->fn == KEY_FN_D) {
        if (ev->type == KEYPAD_EVT_PRESS) {
            on_key_d_press();
        } else if (ev->type == KEYPAD_EVT_RELEASE) {
            on_key_d_release();
        }
        return;
    }
    if (ev->type != KEYPAD_EVT_PRESS) {
        return;
    }

    switch (ev->fn) {
    case KEY_FN_A:
        action_start();
        break;
    case KEY_FN_C:
        action_dump();
        break;
    case KEY_FN_B:
        action_stop();
        break;
    case KEY_FN_HASH:
        begin_peek(ST_PEEK_SET, s_target);
        break;
    case KEY_FN_STAR:
        begin_peek(ST_PEEK_TOTAL, s_total % 10000u);
        break;
    default:
        break;
    }
}

static void on_key_set(const keypad_event_t *ev)
{
    if (ev->fn == KEY_FN_D) {
        if (ev->type == KEYPAD_EVT_PRESS) {
            on_key_d_press();
        } else if (ev->type == KEYPAD_EVT_RELEASE) {
            on_key_d_release();
        }
        return;
    }
    if (ev->type != KEYPAD_EVT_PRESS) {
        return;
    }
    if (ev->is_digit) {
        action_digit(ev->ch);
        return;
    }

    switch (ev->fn) {
    case KEY_FN_C:
        action_clear_entry();
        break;
    case KEY_FN_A:
        action_start();
        break;
    case KEY_FN_B:
        action_stop();
        break;
    case KEY_FN_HASH:
        begin_peek(ST_PEEK_SET, s_entry);
        break;
    case KEY_FN_STAR:
        begin_peek(ST_PEEK_TOTAL, s_total % 10000u);
        break;
    default:
        break;
    }
}

static void on_key_rpm(const keypad_event_t *ev)
{
    if (ev->type != KEYPAD_EVT_PRESS) {
        return;
    }
    if (ev->is_digit) {
        action_digit(ev->ch);
        return;
    }

    switch (ev->fn) {
    case KEY_FN_C:
        action_clear_entry();
        break;
    case KEY_FN_A:    /* lưu RPM */
        action_save_rpm();
        break;
    case KEY_FN_B:    /* hủy */
        goto_state(ST_IDLE);
        break;
    case KEY_FN_HASH:
        begin_peek(ST_PEEK_SET, s_rpm_fast);
        break;
    case KEY_FN_STAR:
        begin_peek(ST_PEEK_TOTAL, s_total % 10000u);
        break;
    default:
        break;
    }
}

static void on_key_run(const keypad_event_t *ev)
{
    if (ev->type != KEYPAD_EVT_PRESS) {
        return;
    }
    switch (ev->fn) {
    case KEY_FN_B:
        action_stop();
        break;
    case KEY_FN_C:
        disc_stop();
        action_dump();
        break;
    case KEY_FN_D:
        on_key_d_press(); /* long có thể bỏ; short release → SET sau khi dừng? */
        action_enter_set();
        s_d_down = false;
        break;
    case KEY_FN_HASH:
        begin_peek(ST_PEEK_SET, s_target);
        break;
    case KEY_FN_STAR:
        begin_peek(ST_PEEK_TOTAL, s_total % 10000u);
        break;
    default:
        break;
    }
}

static void on_key_dump(const keypad_event_t *ev)
{
    if (ev->type != KEYPAD_EVT_PRESS) {
        return;
    }
    switch (ev->fn) {
    case KEY_FN_B:
        action_stop();
        break;
    case KEY_FN_D:
        action_enter_set();
        break;
    case KEY_FN_HASH:
        begin_peek(ST_PEEK_SET, s_target);
        break;
    case KEY_FN_STAR:
        begin_peek(ST_PEEK_TOTAL, s_total % 10000u);
        break;
    default:
        break;
    }
}

static void on_key_done(const keypad_event_t *ev)
{
    if (ev->fn == KEY_FN_D) {
        if (ev->type == KEYPAD_EVT_PRESS) {
            on_key_d_press();
        } else if (ev->type == KEYPAD_EVT_RELEASE) {
            on_key_d_release();
        }
        return;
    }
    if (ev->type != KEYPAD_EVT_PRESS) {
        return;
    }
    switch (ev->fn) {
    case KEY_FN_A:
        action_start();
        break;
    case KEY_FN_C:
        action_dump();
        break;
    case KEY_FN_B:
        action_stop();
        break;
    case KEY_FN_HASH:
        begin_peek(ST_PEEK_SET, s_target);
        break;
    case KEY_FN_STAR:
        begin_peek(ST_PEEK_TOTAL, s_total % 10000u);
        break;
    default:
        break;
    }
}

static void on_key_peek(const keypad_event_t *ev)
{
    end_peek();
    count_ui_on_key(ev);
}

static void tick_counting(bool ignore_target)
{
    uint32_t c = count_sensor_get();

    if (c != s_last_run) {
        s_total += (c - s_last_run);
        s_last_run = c;
        s_last_object_ms = HAL_GetTick();
        s_stalling = false;
        tm1637_display_on(true);
        tm1637_show_uint(c, false);

        if (!ignore_target && c >= s_target) {
            disc_stop();
            s_state = ST_DONE;
            tm1637_show_uint(s_target, false);
            return;
        }
        if (!ignore_target) {
            apply_speed_for_remaining(s_target - c);
        }
    }

    stall_update();

    if (ignore_target && s_stalling) {
        disc_stop();
        tm1637_display_on(true);
        s_state = ST_DONE;
        tm1637_show_uint(c, false);
        return;
    }

    if (count_sensor_jam()) {
        HAL_GPIO_WritePin(PIN_LED_ERR_Port, PIN_LED_ERR_Pin, GPIO_PIN_SET);
        motors_stop_all_hard();
        goto_state(ST_IDLE);
    }
}

static void tick_peek(void)
{
    if ((int32_t)(HAL_GetTick() - s_peek_until) >= 0) {
        end_peek();
    }
}

void count_ui_init(void)
{
    s_state = ST_IDLE;
    s_peek_return = ST_IDLE;
    s_target = 0;
    s_entry = 0;
    s_entry_fresh = true;
    s_total = 0;
    s_last_run = 0;
    s_peek_until = 0;
    s_last_object_ms = 0;
    s_blink_phase = true;
    s_blink_ms = 0;
    s_stalling = false;
    s_rpm_fast = clamp_rpm(COUNT_UI_RPM_FAST);
    s_d_down = false;
    s_d_down_ms = 0;
    s_d_long_fired = false;
    disc_stop();
    tm1637_display_on(true);
    tm1637_show_uint(0, false);
}

void count_ui_tick(void)
{
    tick_d_long();

    switch (s_state) {
    case ST_RUN:
        tick_counting(false);
        break;
    case ST_DUMP:
        tick_counting(true);
        break;
    case ST_PEEK_SET:
    case ST_PEEK_TOTAL:
        tick_peek();
        break;
    default:
        break;
    }
}

void count_ui_on_key(const keypad_event_t *ev)
{
    if (ev == NULL) {
        return;
    }

    switch (s_state) {
    case ST_IDLE:
        on_key_idle(ev);
        break;
    case ST_SET:
        on_key_set(ev);
        break;
    case ST_RPM:
        on_key_rpm(ev);
        break;
    case ST_RUN:
        on_key_run(ev);
        break;
    case ST_DUMP:
        on_key_dump(ev);
        break;
    case ST_DONE:
        on_key_done(ev);
        break;
    case ST_PEEK_SET:
    case ST_PEEK_TOTAL:
        on_key_peek(ev);
        break;
    default:
        break;
    }
}
