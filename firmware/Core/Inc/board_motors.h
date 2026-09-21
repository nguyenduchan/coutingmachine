/**
 * Board-level NEMA17 + TMC2208/2209 — luôn 2 kênh.
 * U4/TMC2 có thể không lắp; firmware vẫn drive STEP/DIR/EN2.
 */
#ifndef BOARD_MOTORS_H
#define BOARD_MOTORS_H

#include <stdbool.h>
#include <stdint.h>

#include "board_config.h"
#include "tmc_step.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    MOTOR_1 = 0,   /* U3 / TMC1 — đĩa chính (CCW) */
    MOTOR_2 = 1,   /* U4 / TMC2 — bánh răng (CW); optional phần cứng */
    MOTOR_COUNT = 2
} motor_id_t;

void motors_init(void);

tmc_axis_t *motors_axis(motor_id_t id);

void motors_enable(motor_id_t id, bool on);
void motors_disable_all(void);

bool motors_set_speed_sps(motor_id_t id, uint32_t steps_per_sec);
bool motors_set_speed_rpm(motor_id_t id, uint32_t rpm);
uint32_t motors_get_speed_sps(motor_id_t id);

bool motors_run(motor_id_t id, tmc_dir_t dir);
bool motors_run_cw(motor_id_t id);
bool motors_run_ccw(motor_id_t id);

/** Luôn chạy cả 2: M1=CCW, M2=CW (cùng rpm, có ramp). */
void motors_run_counting(uint32_t rpm);

void motors_stop(motor_id_t id);
void motors_stop_coast(motor_id_t id);
void motors_stop_all(void);
void motors_stop_all_hard(void);

bool motors_is_running(motor_id_t id);
void motors_tick(void);

bool motors_move(motor_id_t id, int32_t steps, uint32_t period_us);
bool motors_move_default(motor_id_t id, int32_t steps);

#ifdef __cplusplus
}
#endif

#endif /* BOARD_MOTORS_H */
