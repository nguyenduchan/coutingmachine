/**
 * Non-volatile settings — last Flash page (survives power loss).
 * STM32G030C8: 64 KB, page 2 KB → page 31 @ 0x0800F800.
 */
#ifndef NV_SETTINGS_H
#define NV_SETTINGS_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    uint32_t target; /* batch count 1..9999 (0 = unset) */
    uint32_t rpm;    /* disc RPM */
} nv_settings_t;

/** Load from Flash. false → use caller defaults. */
bool nv_settings_load(nv_settings_t *out);

/** Erase + program last page. true on success. */
bool nv_settings_save(const nv_settings_t *in);

#ifdef __cplusplus
}
#endif

#endif /* NV_SETTINGS_H */
