/**
 * Count input — always read both MCU channels:
 *   CH0 PA0 /BUP  = J14 BUP hoặc J15 FIBER (chung net)
 *   CH1 PA3 /CNT5 = J_CNT5 IR 5V
 *
 * Khóa kênh: xung hợp lệ đầu tiên → chỉ kênh đó cộng count.
 * Kênh kẹt (jam) khi chưa khóa → bỏ qua (giắc trống / nhiễu mức).
 */
#ifndef COUNT_SENSOR_H
#define COUNT_SENSOR_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    COUNT_CH_NONE = 0, /* chưa khóa */
    COUNT_CH_BUP,      /* PA0 — J14/J15 */
    COUNT_CH_CNT5      /* PA3 — J_CNT5 */
} count_channel_t;

void count_sensor_init(void);

/** Kênh đang khóa sau xung hợp lệ đầu (NONE nếu chưa). */
count_channel_t count_sensor_channel(void);

void count_sensor_tick(void);

uint32_t count_sensor_get(void);
void     count_sensor_reset(void);

bool count_sensor_blocked(void);
bool count_sensor_jam(void);
void count_sensor_clear_jam(void);
uint32_t count_sensor_glitches(void);

#ifdef __cplusplus
}
#endif

#endif /* COUNT_SENSOR_H */
