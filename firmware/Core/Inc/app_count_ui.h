/**
 * Counting UI — state machine.
 *
 * Phím: D ngắn=SET target (nhập chuỗi số, commit khi A=START) ·
 *       D giữ≥0.8s=nhập RPM (≤80) · A=START/lưu RPM · B=STOP · C=XẢ ·
 *       #=xem set · *=xem tổng
 * Target (+ RPM) lưu Flash — giữ sau tắt nguồn.
 */
#ifndef APP_COUNT_UI_H
#define APP_COUNT_UI_H

#include "keypad_4x4.h"

#ifdef __cplusplus
extern "C" {
#endif

void count_ui_init(void);
void count_ui_tick(void);
void count_ui_on_key(const keypad_event_t *ev);

#ifdef __cplusplus
}
#endif

#endif /* APP_COUNT_UI_H */
