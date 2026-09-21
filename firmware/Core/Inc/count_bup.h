/**
 * Autonics BUP-30S (U-slot) on J14 → PC817 → /BUP (PA0).
 * Cleaner edges than cheap IR; moderate part speed.
 */
#ifndef COUNT_BUP_H
#define COUNT_BUP_H

#include "count_filter.h"

#ifdef __cplusplus
extern "C" {
#endif

static inline count_filter_cfg_t count_bup_profile(void)
{
    count_filter_cfg_t c = {
        .debounce_us   = 500u,      /* 0.5 ms */
        .min_active_us = 2000u,     /* ≥2 ms break */
        .min_idle_us   = 3000u,     /* ≥3 ms clear before next */
        .max_active_us = 2000000u,  /* 2 s → jam */
        .active_low    = true,
    };
    return c;
}

#ifdef __cplusplus
}
#endif

#endif /* COUNT_BUP_H */
