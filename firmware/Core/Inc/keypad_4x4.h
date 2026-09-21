/**
 * 4×4 membrane keypad on J_KEY (ROW0–3, COL0–3).
 *
 * Layout (ROW ↓, COL →):
 *   1  2  3  A
 *   4  5  6  B
 *   7  8  9  C
 *   *  0  #  D
 *
 * Digits '0'..'9'; function keys via keypad_fn_t / keypad_is_fn().
 */
#ifndef KEYPAD_4X4_H
#define KEYPAD_4X4_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/** Function keys (non-digit). */
typedef enum {
    KEY_FN_NONE = 0,
    KEY_FN_A,       /* START */
    KEY_FN_B,       /* STOP */
    KEY_FN_C,       /* XẢ (dump); khi SET = xóa nhập */
    KEY_FN_D,       /* SET target */
    KEY_FN_STAR,    /* show total counted */
    KEY_FN_HASH     /* show target set */
} keypad_fn_t;

typedef enum {
    KEYPAD_EVT_NONE = 0,
    KEYPAD_EVT_PRESS,
    KEYPAD_EVT_RELEASE
} keypad_evt_type_t;

typedef struct {
    keypad_evt_type_t type;
    char              ch;      /* '0'..'9', 'A'..'D', '*', '#' */
    keypad_fn_t       fn;      /* KEY_FN_NONE if digit */
    bool              is_digit;
    uint8_t           row;     /* 0..3 */
    uint8_t           col;     /* 0..3 */
} keypad_event_t;

void keypad_init(void);

/** Scan + debounce — call from App_Loop (every few ms). */
void keypad_tick(void);

/** Pop one queued event; false if empty. */
bool keypad_poll(keypad_event_t *out);

/** Last pressed char, or 0 if none since reset. */
char keypad_last_char(void);

bool keypad_is_digit(char ch);
keypad_fn_t keypad_char_to_fn(char ch);

#ifdef __cplusplus
}
#endif

#endif /* KEYPAD_4X4_H */
