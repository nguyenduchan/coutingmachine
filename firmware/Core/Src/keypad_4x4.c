#include "keypad_4x4.h"
#include "board_pins.h"
#include "stm32g0xx_hal.h"

#ifndef KEYPAD_DEBOUNCE_MS
#define KEYPAD_DEBOUNCE_MS  30u
#endif

#ifndef KEYPAD_QUEUE_LEN
#define KEYPAD_QUEUE_LEN  8u
#endif

/* ROW = drive (open-drain / PP low when scanning), COL = read pull-up */
static GPIO_TypeDef *const s_row_port[4] = {
    PIN_KEY_ROW0_Port, PIN_KEY_ROW1_Port, PIN_KEY_ROW2_Port, PIN_KEY_ROW3_Port
};
static const uint16_t s_row_pin[4] = {
    PIN_KEY_ROW0_Pin, PIN_KEY_ROW1_Pin, PIN_KEY_ROW2_Pin, PIN_KEY_ROW3_Pin
};
static GPIO_TypeDef *const s_col_port[4] = {
    PIN_KEY_COL0_Port, PIN_KEY_COL1_Port, PIN_KEY_COL2_Port, PIN_KEY_COL3_Port
};
static const uint16_t s_col_pin[4] = {
    PIN_KEY_COL0_Pin, PIN_KEY_COL1_Pin, PIN_KEY_COL2_Pin, PIN_KEY_COL3_Pin
};

/* Standard membrane legend */
static const char s_map[4][4] = {
    { '1', '2', '3', 'A' },
    { '4', '5', '6', 'B' },
    { '7', '8', '9', 'C' },
    { '*', '0', '#', 'D' },
};

static uint16_t s_stable_mask;   /* bit = row*4+col */
static uint16_t s_raw_mask;
static uint32_t s_change_ms;
static uint16_t s_prev_stable;

static keypad_event_t s_q[KEYPAD_QUEUE_LEN];
static uint8_t s_q_head;
static uint8_t s_q_tail;
static char s_last_ch;

static void q_push(const keypad_event_t *ev)
{
    uint8_t next = (uint8_t)((s_q_head + 1u) % KEYPAD_QUEUE_LEN);
    if (next == s_q_tail) {
        /* overflow: drop oldest */
        s_q_tail = (uint8_t)((s_q_tail + 1u) % KEYPAD_QUEUE_LEN);
    }
    s_q[s_q_head] = *ev;
    s_q_head = next;
}

static void rows_all_high_z(void)
{
    for (unsigned r = 0; r < 4u; r++) {
        /* Idle: drive high so no phantom paths; scan drives one low */
        HAL_GPIO_WritePin(s_row_port[r], s_row_pin[r], GPIO_PIN_SET);
    }
}

static uint16_t scan_raw(void)
{
    uint16_t mask = 0;

    for (unsigned r = 0; r < 4u; r++) {
        rows_all_high_z();
        HAL_GPIO_WritePin(s_row_port[r], s_row_pin[r], GPIO_PIN_RESET);
        /* settle */
        for (volatile unsigned i = 0; i < 20u; i++) {
            __NOP();
        }

        for (unsigned c = 0; c < 4u; c++) {
            if (HAL_GPIO_ReadPin(s_col_port[c], s_col_pin[c]) == GPIO_PIN_RESET) {
                mask |= (uint16_t)(1u << (r * 4u + c));
            }
        }
    }
    rows_all_high_z();
    return mask;
}

static void emit_edge(uint8_t idx, bool pressed)
{
    uint8_t row = (uint8_t)(idx / 4u);
    uint8_t col = (uint8_t)(idx % 4u);
    char ch = s_map[row][col];

    keypad_event_t ev = {
        .type = pressed ? KEYPAD_EVT_PRESS : KEYPAD_EVT_RELEASE,
        .ch = ch,
        .fn = keypad_char_to_fn(ch),
        .is_digit = keypad_is_digit(ch),
        .row = row,
        .col = col,
    };
    if (pressed) {
        s_last_ch = ch;
    }
    q_push(&ev);
}

void keypad_init(void)
{
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOD_CLK_ENABLE();

    GPIO_InitTypeDef g = {0};

    g.Mode = GPIO_MODE_OUTPUT_PP;
    g.Pull = GPIO_NOPULL;
    g.Speed = GPIO_SPEED_FREQ_LOW;
    for (unsigned r = 0; r < 4u; r++) {
        g.Pin = s_row_pin[r];
        HAL_GPIO_Init(s_row_port[r], &g);
        HAL_GPIO_WritePin(s_row_port[r], s_row_pin[r], GPIO_PIN_SET);
    }

    g.Mode = GPIO_MODE_INPUT;
    g.Pull = GPIO_PULLUP;
    for (unsigned c = 0; c < 4u; c++) {
        g.Pin = s_col_pin[c];
        HAL_GPIO_Init(s_col_port[c], &g);
    }

    s_stable_mask = 0;
    s_raw_mask = 0;
    s_prev_stable = 0;
    s_change_ms = HAL_GetTick();
    s_q_head = 0;
    s_q_tail = 0;
    s_last_ch = 0;
}

void keypad_tick(void)
{
    uint16_t raw = scan_raw();
    uint32_t now = HAL_GetTick();

    if (raw != s_raw_mask) {
        s_raw_mask = raw;
        s_change_ms = now;
        return;
    }

    if ((uint32_t)(now - s_change_ms) < KEYPAD_DEBOUNCE_MS) {
        return;
    }

    if (raw == s_stable_mask) {
        return;
    }

    uint16_t changed = (uint16_t)(raw ^ s_stable_mask);
    for (uint8_t i = 0; i < 16u; i++) {
        if ((changed & (1u << i)) == 0u) {
            continue;
        }
        bool pressed = (raw & (1u << i)) != 0u;
        emit_edge(i, pressed);
    }

    s_prev_stable = s_stable_mask;
    s_stable_mask = raw;
    (void)s_prev_stable;
}

bool keypad_poll(keypad_event_t *out)
{
    if (out == NULL || s_q_tail == s_q_head) {
        return false;
    }
    *out = s_q[s_q_tail];
    s_q_tail = (uint8_t)((s_q_tail + 1u) % KEYPAD_QUEUE_LEN);
    return true;
}

char keypad_last_char(void)
{
    return s_last_ch;
}

bool keypad_is_digit(char ch)
{
    return (ch >= '0' && ch <= '9');
}

keypad_fn_t keypad_char_to_fn(char ch)
{
    switch (ch) {
    case 'A': return KEY_FN_A;
    case 'B': return KEY_FN_B;
    case 'C': return KEY_FN_C;
    case 'D': return KEY_FN_D;
    case '*': return KEY_FN_STAR;
    case '#': return KEY_FN_HASH;
    default:  return KEY_FN_NONE;
    }
}
