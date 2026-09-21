/**
 * TM1637 4-digit 7-segment module (J_DISP: CLK / DIO / +5V / GND).
 * Compatible with common Shopee modules (0.36" / 0.56").
 * Pins: PA15=CLK, PD0=DIO (board_pins.h).
 */
#ifndef TM1637_H
#define TM1637_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

void tm1637_init(void);

/** Brightness 0 (dim) .. 7 (bright). Also turns display on. */
void tm1637_set_brightness(uint8_t level);

void tm1637_clear(void);

/** Display power on/off (giữ nội dung đã ghi — dùng nhấp nháy). */
void tm1637_display_on(bool on);

/** Show unsigned value 0..9999 (wraps modulo 10000). leading_zero blanks MSDs. */
void tm1637_show_uint(uint32_t value, bool leading_zero);

/** Raw 4 digits 0..9 (or 0x10 = blank). */
void tm1637_show_digits(const uint8_t dig[4]);

#ifdef __cplusplus
}
#endif

#endif /* TM1637_H */
