#include "tmc_step.h"

#ifndef TMC_STEP_PULSE_HIGH_US
#define TMC_STEP_PULSE_HIGH_US  2u
#endif

#ifndef TMC_TICK_CATCHUP_MAX
#define TMC_TICK_CATCHUP_MAX  8u
#endif

#ifndef TMC_SPEED_SPS_MAX
#define TMC_SPEED_SPS_MAX  20000u
#endif

#ifndef TMC_DEFAULT_ACCEL_SPS2
#define TMC_DEFAULT_ACCEL_SPS2  2500u   /* ~47 RPM/s @ 3200 step/rev */
#endif

#ifndef TMC_DEFAULT_DECEL_SPS2
#define TMC_DEFAULT_DECEL_SPS2  2000u   /* giảm chậm hơn một chút */
#endif

#ifndef TMC_RAMP_INTERVAL_US
#define TMC_RAMP_INTERVAL_US  2000u     /* cập nhật tốc độ mỗi 2 ms */
#endif

static void delay_us(uint32_t us)
{
    if (us == 0u) {
        return;
    }
    uint32_t mhz = SystemCoreClock / 1000000u;
    if (mhz == 0u) {
        mhz = 16u;
    }
    uint32_t cycles = us * mhz;
    while (cycles--) {
        __NOP();
    }
}

static void gpio_out(GPIO_TypeDef *port, uint16_t pin, GPIO_PinState s)
{
    HAL_GPIO_WritePin(port, pin, s);
}

static void gpio_init_out(GPIO_TypeDef *port, uint16_t pin)
{
    GPIO_InitTypeDef g = {0};
    g.Pin = pin;
    g.Mode = GPIO_MODE_OUTPUT_PP;
    g.Pull = GPIO_NOPULL;
    g.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(port, &g);
}

static void apply_dir(tmc_axis_t *ax, bool forward)
{
    bool dir_level = forward ^ ax->dir_invert;
    gpio_out(ax->dir_port, ax->dir_pin, dir_level ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

static void pulse_step(tmc_axis_t *ax, bool forward)
{
    gpio_out(ax->step_port, ax->step_pin, GPIO_PIN_SET);
    delay_us(TMC_STEP_PULSE_HIGH_US);
    gpio_out(ax->step_port, ax->step_pin, GPIO_PIN_RESET);
    ax->position += forward ? 1 : -1;
}

static void apply_period_from_current(tmc_axis_t *ax)
{
    if (ax->current_sps == 0u) {
        ax->period_us = 0;
        return;
    }
    ax->period_us = 1000000u / ax->current_sps;
    if (ax->period_us < 2u) {
        ax->period_us = 2u;
    }
}

static void ramp_toward_target(tmc_axis_t *ax, uint32_t now_us)
{
    uint32_t dt = (uint32_t)(now_us - ax->last_ramp_us);
    if (dt < TMC_RAMP_INTERVAL_US) {
        return;
    }
    ax->last_ramp_us = now_us;

    uint32_t rate = (ax->current_sps < ax->target_sps)
                  ? ax->accel_sps2
                  : ax->decel_sps2;
    /* delta_sps = rate * dt_us / 1e6 */
    uint32_t delta = (uint32_t)(((uint64_t)rate * (uint64_t)dt) / 1000000ull);
    if (delta == 0u) {
        delta = 1u;
    }

    if (ax->current_sps < ax->target_sps) {
        uint32_t room = ax->target_sps - ax->current_sps;
        ax->current_sps += (delta > room) ? room : delta;
    } else if (ax->current_sps > ax->target_sps) {
        uint32_t room = ax->current_sps - ax->target_sps;
        ax->current_sps -= (delta > room) ? room : delta;
    }

    apply_period_from_current(ax);

    if (ax->target_sps == 0u && ax->current_sps == 0u) {
        ax->running = false;
    }
}

uint32_t tmc_now_us(void)
{
    uint32_t ms = HAL_GetTick();
    uint32_t load = SysTick->LOAD + 1u;
    uint32_t val = SysTick->VAL;
    return (ms * 1000u) + (((load - val) * 1000u) / load);
}

void tmc_axis_init(tmc_axis_t *ax,
                   GPIO_TypeDef *step_port, uint16_t step_pin,
                   GPIO_TypeDef *dir_port,  uint16_t dir_pin,
                   GPIO_TypeDef *en_port,   uint16_t en_pin)
{
    if (ax == NULL) {
        return;
    }
    ax->step_port = step_port;
    ax->step_pin = step_pin;
    ax->dir_port = dir_port;
    ax->dir_pin = dir_pin;
    ax->en_port = en_port;
    ax->en_pin = en_pin;
    ax->dir_invert = false;
    ax->enabled = false;
    ax->position = 0;
    ax->target_sps = 0;
    ax->current_sps = 0;
    ax->period_us = 0;
    ax->next_step_us = 0;
    ax->last_ramp_us = 0;
    ax->accel_sps2 = TMC_DEFAULT_ACCEL_SPS2;
    ax->decel_sps2 = TMC_DEFAULT_DECEL_SPS2;
    ax->running = false;
    ax->run_dir = TMC_DIR_CW;

    gpio_init_out(step_port, step_pin);
    gpio_init_out(dir_port, dir_pin);
    gpio_init_out(en_port, en_pin);

    gpio_out(step_port, step_pin, GPIO_PIN_RESET);
    gpio_out(dir_port, dir_pin, GPIO_PIN_RESET);
    gpio_out(en_port, en_pin, GPIO_PIN_SET);
}

void tmc_axis_set_dir_invert(tmc_axis_t *ax, bool invert)
{
    if (ax != NULL) {
        ax->dir_invert = invert;
    }
}

void tmc_axis_set_accel(tmc_axis_t *ax, uint32_t accel_sps2, uint32_t decel_sps2)
{
    if (ax == NULL) {
        return;
    }
    ax->accel_sps2 = (accel_sps2 != 0u) ? accel_sps2 : TMC_DEFAULT_ACCEL_SPS2;
    ax->decel_sps2 = (decel_sps2 != 0u) ? decel_sps2 : TMC_DEFAULT_DECEL_SPS2;
}

void tmc_axis_enable(tmc_axis_t *ax, bool enable)
{
    if (ax == NULL) {
        return;
    }
    gpio_out(ax->en_port, ax->en_pin, enable ? GPIO_PIN_RESET : GPIO_PIN_SET);
    ax->enabled = enable;
}

bool tmc_axis_is_enabled(const tmc_axis_t *ax)
{
    return (ax != NULL) && ax->enabled;
}

void tmc_axis_step(tmc_axis_t *ax, bool forward)
{
    if (ax == NULL || !ax->enabled) {
        return;
    }
    apply_dir(ax, forward);
    delay_us(1);
    pulse_step(ax, forward);
}

bool tmc_axis_set_speed_sps(tmc_axis_t *ax, uint32_t steps_per_sec)
{
    if (ax == NULL) {
        return false;
    }
    if (steps_per_sec > TMC_SPEED_SPS_MAX) {
        steps_per_sec = TMC_SPEED_SPS_MAX;
    }
    ax->target_sps = steps_per_sec;
    /* Không gán current ngay — tick sẽ ramp */
    if (steps_per_sec == 0u && !ax->running) {
        ax->current_sps = 0;
        ax->period_us = 0;
    }
    return true;
}

bool tmc_axis_set_speed_rpm(tmc_axis_t *ax, uint32_t rpm, uint32_t steps_per_rev)
{
    if (ax == NULL || steps_per_rev == 0u) {
        return false;
    }
    uint64_t sps = ((uint64_t)rpm * (uint64_t)steps_per_rev) / 60ull;
    if (sps > TMC_SPEED_SPS_MAX) {
        sps = TMC_SPEED_SPS_MAX;
    }
    return tmc_axis_set_speed_sps(ax, (uint32_t)sps);
}

uint32_t tmc_axis_get_speed_sps(const tmc_axis_t *ax)
{
    return (ax != NULL) ? ax->current_sps : 0u;
}

uint32_t tmc_axis_get_target_sps(const tmc_axis_t *ax)
{
    return (ax != NULL) ? ax->target_sps : 0u;
}

bool tmc_axis_run(tmc_axis_t *ax, tmc_dir_t dir)
{
    if (ax == NULL || ax->target_sps == 0u) {
        return false;
    }
    tmc_axis_enable(ax, true);
    ax->run_dir = dir;
    ax->running = true;
    apply_dir(ax, dir == TMC_DIR_CW);
    delay_us(1);
    uint32_t now = tmc_now_us();
    ax->next_step_us = now;
    ax->last_ramp_us = now;
    /* Bắt đầu từ đứng yên nếu đang = 0 — ramp lên target */
    return true;
}

void tmc_axis_run_cw(tmc_axis_t *ax)
{
    (void)tmc_axis_run(ax, TMC_DIR_CW);
}

void tmc_axis_run_ccw(tmc_axis_t *ax)
{
    (void)tmc_axis_run(ax, TMC_DIR_CCW);
}

void tmc_axis_stop(tmc_axis_t *ax)
{
    if (ax == NULL) {
        return;
    }
    ax->target_sps = 0;
    if (!ax->running || ax->current_sps == 0u) {
        ax->running = false;
        ax->current_sps = 0;
        ax->period_us = 0;
    }
    /* else: tick ramp xuống 0 rồi clear running */
}

void tmc_axis_stop_hard(tmc_axis_t *ax)
{
    if (ax == NULL) {
        return;
    }
    ax->target_sps = 0;
    ax->current_sps = 0;
    ax->period_us = 0;
    ax->running = false;
}

void tmc_axis_stop_coast(tmc_axis_t *ax)
{
    tmc_axis_stop_hard(ax);
    tmc_axis_enable(ax, false);
}

bool tmc_axis_is_running(const tmc_axis_t *ax)
{
    return (ax != NULL) && ax->running;
}

bool tmc_axis_is_ramping(const tmc_axis_t *ax)
{
    return (ax != NULL) && ax->running && (ax->current_sps != ax->target_sps);
}

void tmc_axis_tick(tmc_axis_t *ax, uint32_t now_us)
{
    if (ax == NULL || !ax->running || !ax->enabled) {
        return;
    }

    ramp_toward_target(ax, now_us);

    if (ax->period_us == 0u || ax->current_sps == 0u) {
        return;
    }

    bool forward = (ax->run_dir == TMC_DIR_CW);
    unsigned n = 0;
    while ((int32_t)(now_us - ax->next_step_us) >= 0) {
        pulse_step(ax, forward);
        ax->next_step_us += ax->period_us;
        if (++n >= TMC_TICK_CATCHUP_MAX) {
            ax->next_step_us = now_us + ax->period_us;
            break;
        }
    }
}

bool tmc_axis_move(tmc_axis_t *ax, int32_t steps, uint32_t period_us)
{
    tmc_axis_t *list[1] = { ax };
    return tmc_axes_move(list, 1u, steps, period_us);
}

bool tmc_axes_move(tmc_axis_t *const *axes, unsigned count,
                   int32_t steps, uint32_t period_us)
{
    if (axes == NULL || count == 0u || period_us < 2u) {
        return false;
    }
    for (unsigned a = 0; a < count; a++) {
        if (axes[a] == NULL) {
            return false;
        }
        tmc_axis_stop_hard(axes[a]);
    }
    if (steps == 0) {
        return true;
    }

    bool forward = steps > 0;
    uint32_t n = (uint32_t)(forward ? steps : -steps);
    uint32_t pulse_budget = TMC_STEP_PULSE_HIGH_US + 1u;
    uint32_t low_us = (period_us > pulse_budget * count)
                    ? (period_us - pulse_budget * count)
                    : 1u;

    for (unsigned a = 0; a < count; a++) {
        tmc_axis_enable(axes[a], true);
        apply_dir(axes[a], forward);
    }
    delay_us(1);

    for (uint32_t i = 0; i < n; i++) {
        for (unsigned a = 0; a < count; a++) {
            gpio_out(axes[a]->step_port, axes[a]->step_pin, GPIO_PIN_SET);
        }
        delay_us(TMC_STEP_PULSE_HIGH_US);
        for (unsigned a = 0; a < count; a++) {
            gpio_out(axes[a]->step_port, axes[a]->step_pin, GPIO_PIN_RESET);
            axes[a]->position += forward ? 1 : -1;
        }
        delay_us(low_us);
    }
    return true;
}

void tmc_axis_stop_hold(tmc_axis_t *ax)
{
    tmc_axis_stop(ax);
    if (ax != NULL) {
        tmc_axis_enable(ax, true);
    }
}

void tmc_axis_disable(tmc_axis_t *ax)
{
    tmc_axis_stop_coast(ax);
}

int32_t tmc_axis_position(const tmc_axis_t *ax)
{
    return (ax != NULL) ? ax->position : 0;
}

void tmc_axis_set_position(tmc_axis_t *ax, int32_t pos)
{
    if (ax != NULL) {
        ax->position = pos;
    }
}
