#include "count_filter.h"

void count_filter_init(count_filter_t *f, const count_filter_cfg_t *cfg)
{
    if (f == NULL || cfg == NULL) {
        return;
    }
    f->cfg = *cfg;
    if (f->cfg.debounce_us < 50u) {
        f->cfg.debounce_us = 50u;
    }
    f->raw_candidate = false;
    f->raw_since_us = 0;
    f->stable_active = false;
    f->state_since_us = 0;
    f->armed = true; /* power-up: ready for first part */
    f->counted_this_break = false;
    f->jam = false;
    f->count = 0;
    f->rejected_glitch = 0;
}

static bool raw_means_active(const count_filter_t *f, bool pin_high)
{
    return f->cfg.active_low ? !pin_high : pin_high;
}

void count_filter_feed(count_filter_t *f, bool raw_pin_high, uint32_t now_us)
{
    if (f == NULL) {
        return;
    }

    bool raw_active = raw_means_active(f, raw_pin_high);

    if (raw_active != f->raw_candidate) {
        f->raw_candidate = raw_active;
        f->raw_since_us = now_us;
    }

    bool debounced = ((uint32_t)(now_us - f->raw_since_us) >= f->cfg.debounce_us);

    if (debounced && raw_active != f->stable_active) {
        if (raw_active) {
            /* Enter break */
            f->stable_active = true;
            f->state_since_us = now_us;
            f->counted_this_break = false;
        } else {
            /* Enter clear */
            if (!f->counted_this_break) {
                f->rejected_glitch++;
            }
            f->stable_active = false;
            f->state_since_us = now_us;
            f->armed = false; /* need min_idle before next count */
            f->jam = false;
            f->counted_this_break = false;
        }
    }

    if (f->stable_active) {
        uint32_t held = (uint32_t)(now_us - f->state_since_us);

        if (f->cfg.max_active_us != 0u && held >= f->cfg.max_active_us) {
            f->jam = true;
        }

        if (f->armed && !f->counted_this_break && held >= f->cfg.min_active_us) {
            f->count++;
            f->counted_this_break = true;
            f->armed = false; /* require clear + min_idle to re-arm */
        }
    } else {
        /* Stable clear: re-arm after min_idle */
        if (!f->armed
            && (uint32_t)(now_us - f->state_since_us) >= f->cfg.min_idle_us) {
            f->armed = true;
        }
    }
}

uint32_t count_filter_get(const count_filter_t *f)
{
    return (f != NULL) ? f->count : 0u;
}

void count_filter_reset_count(count_filter_t *f)
{
    if (f != NULL) {
        f->count = 0;
        f->rejected_glitch = 0;
        f->counted_this_break = false;
        f->jam = false;
        f->armed = true;
    }
}

bool count_filter_blocked(const count_filter_t *f)
{
    return (f != NULL) && f->stable_active;
}

bool count_filter_jam(const count_filter_t *f)
{
    return (f != NULL) && f->jam;
}

void count_filter_clear_jam(count_filter_t *f)
{
    if (f != NULL) {
        f->jam = false;
    }
}

uint32_t count_filter_glitches(const count_filter_t *f)
{
    return (f != NULL) ? f->rejected_glitch : 0u;
}
