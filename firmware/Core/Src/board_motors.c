#include "board_motors.h"
#include "board_pins.h"
#include "stm32g0xx_hal.h"

static tmc_axis_t s_axes[MOTOR_COUNT];

void motors_init(void)
{
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();

    /* Luôn init cả 2 kênh — TMC2 có thể không cắm */
    tmc_axis_init(&s_axes[MOTOR_1],
                  PIN_TMC1_STEP_Port, PIN_TMC1_STEP_Pin,
                  PIN_TMC1_DIR_Port,  PIN_TMC1_DIR_Pin,
                  PIN_TMC1_EN_Port,   PIN_TMC1_EN_Pin);

    tmc_axis_init(&s_axes[MOTOR_2],
                  PIN_TMC2_STEP_Port, PIN_TMC2_STEP_Pin,
                  PIN_TMC2_DIR_Port,  PIN_TMC2_DIR_Pin,
                  PIN_TMC2_EN_Port,   PIN_TMC2_EN_Pin);

    uint32_t acc = (MOTOR_ACCEL_RPM_S * BOARD_MOTOR_STEPS_PER_REV) / 60u;
    uint32_t dec = (MOTOR_DECEL_RPM_S * BOARD_MOTOR_STEPS_PER_REV) / 60u;
    if (acc == 0u) {
        acc = 1u;
    }
    if (dec == 0u) {
        dec = 1u;
    }
    tmc_axis_set_accel(&s_axes[MOTOR_1], acc, dec);
    tmc_axis_set_accel(&s_axes[MOTOR_2], acc, dec);
}

tmc_axis_t *motors_axis(motor_id_t id)
{
    if ((unsigned)id >= (unsigned)MOTOR_COUNT) {
        return NULL;
    }
    return &s_axes[id];
}

void motors_enable(motor_id_t id, bool on)
{
    tmc_axis_t *ax = motors_axis(id);
    if (ax != NULL) {
        tmc_axis_enable(ax, on);
    }
}

void motors_disable_all(void)
{
    tmc_axis_disable(&s_axes[MOTOR_1]);
    tmc_axis_disable(&s_axes[MOTOR_2]);
}

bool motors_set_speed_sps(motor_id_t id, uint32_t steps_per_sec)
{
    tmc_axis_t *ax = motors_axis(id);
    return (ax != NULL) && tmc_axis_set_speed_sps(ax, steps_per_sec);
}

bool motors_set_speed_rpm(motor_id_t id, uint32_t rpm)
{
    tmc_axis_t *ax = motors_axis(id);
    return (ax != NULL)
        && tmc_axis_set_speed_rpm(ax, rpm, BOARD_MOTOR_STEPS_PER_REV);
}

uint32_t motors_get_speed_sps(motor_id_t id)
{
    tmc_axis_t *ax = motors_axis(id);
    return (ax != NULL) ? tmc_axis_get_speed_sps(ax) : 0u;
}

bool motors_run(motor_id_t id, tmc_dir_t dir)
{
    tmc_axis_t *ax = motors_axis(id);
    return (ax != NULL) && tmc_axis_run(ax, dir);
}

bool motors_run_cw(motor_id_t id)
{
    return motors_run(id, TMC_DIR_CW);
}

bool motors_run_ccw(motor_id_t id)
{
    return motors_run(id, TMC_DIR_CCW);
}

void motors_run_counting(uint32_t rpm)
{
    /* Luôn cả 2: đĩa CCW + bánh răng CW (TMC2 trống cũng OK) */
    motors_set_speed_rpm(MOTOR_1, rpm);
    if (!motors_is_running(MOTOR_1)) {
        (void)motors_run(MOTOR_1, TMC_DIR_CCW);
    }
    motors_set_speed_rpm(MOTOR_2, rpm);
    if (!motors_is_running(MOTOR_2)) {
        (void)motors_run(MOTOR_2, TMC_DIR_CW);
    }
}

void motors_stop(motor_id_t id)
{
    tmc_axis_t *ax = motors_axis(id);
    if (ax != NULL) {
        tmc_axis_stop(ax);
    }
}

void motors_stop_coast(motor_id_t id)
{
    tmc_axis_t *ax = motors_axis(id);
    if (ax != NULL) {
        tmc_axis_stop_coast(ax);
    }
}

void motors_stop_all(void)
{
    tmc_axis_stop(&s_axes[MOTOR_1]);
    tmc_axis_stop(&s_axes[MOTOR_2]);
}

void motors_stop_all_hard(void)
{
    tmc_axis_stop_hard(&s_axes[MOTOR_1]);
    tmc_axis_stop_hard(&s_axes[MOTOR_2]);
}

bool motors_is_running(motor_id_t id)
{
    tmc_axis_t *ax = motors_axis(id);
    return (ax != NULL) && tmc_axis_is_running(ax);
}

void motors_tick(void)
{
    uint32_t now = tmc_now_us();
    tmc_axis_tick(&s_axes[MOTOR_1], now);
    tmc_axis_tick(&s_axes[MOTOR_2], now);
}

bool motors_move(motor_id_t id, int32_t steps, uint32_t period_us)
{
    tmc_axis_t *ax = motors_axis(id);
    if (ax == NULL) {
        return false;
    }
    return tmc_axis_move(ax, steps, period_us);
}

bool motors_move_default(motor_id_t id, int32_t steps)
{
    return motors_move(id, steps, BOARD_MOTOR_DEFAULT_PERIOD_US);
}
