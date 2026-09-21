/**
 * TMC2208 / TMC2209 StepStick — STEP/DIR/EN GPIO driver (one axis).
 * Continuous run with accel/decel ramp (tránh dòng khởi động đột ngột).
 */
#ifndef TMC_STEP_H
#define TMC_STEP_H

#include <stdbool.h>
#include <stdint.h>

#include "stm32g0xx_hal.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    TMC_DIR_CW  = 0,  /* cùng kim đồng hồ (bánh răng MOTOR_2) */
    TMC_DIR_CCW = 1   /* ngược kim đồng hồ (đĩa MOTOR_1) */
} tmc_dir_t;

typedef struct {
    GPIO_TypeDef *step_port;
    uint16_t      step_pin;
    GPIO_TypeDef *dir_port;
    uint16_t      dir_pin;
    GPIO_TypeDef *en_port;
    uint16_t      en_pin;

    bool     dir_invert;
    bool     enabled;
    int32_t  position;

    uint32_t target_sps;    /* tốc độ đích (set_speed / stop→0) */
    uint32_t current_sps;   /* tốc độ thực (ramp) */
    uint32_t period_us;     /* từ current_sps */
    uint32_t next_step_us;
    uint32_t last_ramp_us;
    uint32_t accel_sps2;    /* steps/s² tăng */
    uint32_t decel_sps2;    /* steps/s² giảm */
    bool     running;
    tmc_dir_t run_dir;
} tmc_axis_t;

void tmc_axis_init(tmc_axis_t *ax,
                   GPIO_TypeDef *step_port, uint16_t step_pin,
                   GPIO_TypeDef *dir_port,  uint16_t dir_pin,
                   GPIO_TypeDef *en_port,   uint16_t en_pin);

void tmc_axis_set_dir_invert(tmc_axis_t *ax, bool invert);

/** Gia tốc / giảm tốc (steps/s²). 0 = dùng mặc định nội bộ. */
void tmc_axis_set_accel(tmc_axis_t *ax, uint32_t accel_sps2, uint32_t decel_sps2);

void tmc_axis_enable(tmc_axis_t *ax, bool enable);
bool tmc_axis_is_enabled(const tmc_axis_t *ax);

void tmc_axis_step(tmc_axis_t *ax, bool forward);

/** Đặt tốc độ đích (ramp tới đây, không nhảy cóc). 0 = soft-stop. */
bool tmc_axis_set_speed_sps(tmc_axis_t *ax, uint32_t steps_per_sec);
bool tmc_axis_set_speed_rpm(tmc_axis_t *ax, uint32_t rpm, uint32_t steps_per_rev);

uint32_t tmc_axis_get_speed_sps(const tmc_axis_t *ax);       /* current */
uint32_t tmc_axis_get_target_sps(const tmc_axis_t *ax);

bool tmc_axis_run(tmc_axis_t *ax, tmc_dir_t dir);
void tmc_axis_run_cw(tmc_axis_t *ax);
void tmc_axis_run_ccw(tmc_axis_t *ax);

/** Soft-stop: target=0, ramp xuống rồi ngừng xung (giữ EN). */
void tmc_axis_stop(tmc_axis_t *ax);

/** Dừng ngay + tắt EN (jam / khẩn cấp). */
void tmc_axis_stop_hard(tmc_axis_t *ax);
void tmc_axis_stop_coast(tmc_axis_t *ax); /* = stop_hard */

bool tmc_axis_is_running(const tmc_axis_t *ax);
bool tmc_axis_is_ramping(const tmc_axis_t *ax);

void tmc_axis_tick(tmc_axis_t *ax, uint32_t now_us);
uint32_t tmc_now_us(void);

bool tmc_axis_move(tmc_axis_t *ax, int32_t steps, uint32_t period_us);
bool tmc_axes_move(tmc_axis_t *const *axes, unsigned count,
                   int32_t steps, uint32_t period_us);

void tmc_axis_stop_hold(tmc_axis_t *ax);
void tmc_axis_disable(tmc_axis_t *ax);

int32_t tmc_axis_position(const tmc_axis_t *ax);
void    tmc_axis_set_position(tmc_axis_t *ax, int32_t pos);

#ifdef __cplusplus
}
#endif

#endif /* TMC_STEP_H */
