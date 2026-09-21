/**
 * Fiber optic photo sensor on J15 → same PC817 /BUP (PA0) as BUP jack.
 * Often faster / narrower pulses for small parts — tighter timing.
 */
#ifndef COUNT_FIBER_H
#define COUNT_FIBER_H

#include "count_filter.h"

#ifdef __cplusplus
extern "C" {
#endif

static inline count_filter_cfg_t count_fiber_profile(void)
{
    count_filter_cfg_t c = {
        .debounce_us   = 200u,      /* 0.2 ms — faster edges */
        .min_active_us = 800u,      /* ≥0.8 ms */
        .min_idle_us   = 1500u,     /* ≥1.5 ms gap */
        .max_active_us = 2000000u,
        .active_low    = true,
    };
    return c;
}

#ifdef __cplusplus
}
#endif

#endif /* COUNT_FIBER_H */
