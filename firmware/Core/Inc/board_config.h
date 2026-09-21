/**
 * Board options for STM32CubeIDE builds.
 */
#ifndef BOARD_CONFIG_H
#define BOARD_CONFIG_H

/**
 * Firmware luôn điều khiển 2 kênh TMC (U3+U4).
 * Phần cứng: TMC2 / NEMA2 có thể không lắp — GPIO vẫn toggling vào đế trống, an toàn.
 */
#define BOARD_MOTOR_COUNT  2

#ifndef BOARD_MOTOR_DEFAULT_PERIOD_US
#define BOARD_MOTOR_DEFAULT_PERIOD_US  400u
#endif

#ifndef BOARD_MOTOR_STEPS_PER_REV
#define BOARD_MOTOR_STEPS_PER_REV  3200u
#endif

/* Cảm biến: luôn đọc PA0 (/BUP) + PA3 (/CNT5); không cần BOARD_COUNT_SENSOR */

/**
 * Tốc độ đĩa (RPM trục NEMA17 → đĩa).
 * Max 80: đĩa đếm thuốc/hạt ~Ø120–180 mm — cao hơn dễ văng vật nhẹ.
 * Mặc định 50: an toàn đa vật; chỉnh bằng giữ D (SET).
 */
#ifndef COUNT_UI_RPM_MAX
#define COUNT_UI_RPM_MAX   80u
#endif
#ifndef COUNT_UI_RPM_FAST
#define COUNT_UI_RPM_FAST  50u
#endif
#ifndef COUNT_UI_RPM_MIN
#define COUNT_UI_RPM_MIN   8u
#endif
#ifndef COUNT_UI_RPM_ENTRY_MIN
#define COUNT_UI_RPM_ENTRY_MIN  15u
#endif
#ifndef COUNT_UI_SLOW_ZONE
#define COUNT_UI_SLOW_ZONE 10u
#endif
#ifndef COUNT_UI_STALL_MS
#define COUNT_UI_STALL_MS  5000u
#endif
#ifndef COUNT_UI_SET_LONG_MS
#define COUNT_UI_SET_LONG_MS  800u
#endif

#ifndef MOTOR_ACCEL_RPM_S
#define MOTOR_ACCEL_RPM_S  40u
#endif
#ifndef MOTOR_DECEL_RPM_S
#define MOTOR_DECEL_RPM_S  30u
#endif

#endif /* BOARD_CONFIG_H */
