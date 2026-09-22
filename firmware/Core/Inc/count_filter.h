/**
 * Shared anti-noise count filter for photo / U-slot / IR sensors.
 *
 * One count per object: debounce → confirm min break width → ignore chatter
 * until beam clear for min_idle (re-arm). Optional jam if break too long.
 */
#ifndef COUNT_FILTER_H
#define COUNT_FILTER_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    uint32_t debounce_us;   /* raw must hold before level accepted */
    uint32_t min_active_us; /* min break duration to count a part */
    uint32_t min_idle_us;   /* min clear duration before next count */
    uint32_t max_active_us; /* 0=off; sustained break → jam */
    bool     active_low;    /* PC817: low = object in beam */
} count_filter_cfg_t;

typedef struct {
    count_filter_cfg_t cfg;

    bool     raw_candidate;
    uint32_t raw_since_us;

    bool     stable_active;
    uint32_t state_since_us;

    bool     armed;               /* clear long enough — may accept next count */
    bool     counted_this_break;
    bool     jam;

    uint32_t count;
    uint32_t rejected_glitch;
} count_filter_t;

void count_filter_init(count_filter_t *f, const count_filter_cfg_t *cfg);
void count_filter_feed(count_filter_t *f, bool raw_pin_high, uint32_t now_us);

uint32_t count_filter_get(const count_filter_t *f);
void     count_filter_reset_count(count_filter_t *f);
bool     count_filter_blocked(const count_filter_t *f);
bool     count_filter_jam(const count_filter_t *f);
void     count_filter_clear_jam(count_filter_t *f);
uint32_t count_filter_glitches(const count_filter_t *f);

#ifdef __cplusplus
}
#endif

#endif /* COUNT_FILTER_H */
