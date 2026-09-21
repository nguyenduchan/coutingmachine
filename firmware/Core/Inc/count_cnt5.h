/**
 * Cheap 5 V IR / through-beam on J_CNT5 → PC817 → /CNT5 (PA3).
 * Noisier modules: longer debounce and wider min pulse/gap.
 */
#ifndef COUNT_CNT5_H
#define COUNT_CNT5_H

#include "count_filter.h"

#ifdef __cplusplus
extern "C" {
#endif

static inline count_filter_cfg_t count_cnt5_profile(void)
{
    count_filter_cfg_t c = {
        .debounce_us   = 1000u,     /* 1 ms */
        .min_active_us = 5000u,     /* ≥5 ms */
        .min_idle_us   = 8000u,     /* ≥8 ms */
        .max_active_us = 3000000u,  /* 3 s → jam */
        .active_low    = true,
    };
    return c;
}

#ifdef __cplusplus
}
#endif

#endif /* COUNT_CNT5_H */
