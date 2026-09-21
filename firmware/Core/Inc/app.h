/**
 * Application layer — kept outside CubeMX-regenerated main.c USER CODE.
 */
#ifndef APP_H
#define APP_H

#ifdef __cplusplus
extern "C" {
#endif

/** Call once after HAL_Init + SystemClock_Config + MX_GPIO_Init. */
void App_Init(void);

/** Call every main-loop iteration (motors + count sensor). */
void App_Loop(void);

#ifdef __cplusplus
}
#endif

#endif /* APP_H */
