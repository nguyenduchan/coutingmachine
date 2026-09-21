/**
 * Board GPIO — mirrors pcb/STM32G030C8T6/stm32_pinmap.py (repo root relative).
 * Keep in sync when carrier nets / pinmap change.
 */
#ifndef BOARD_PINS_H
#define BOARD_PINS_H

#ifdef __cplusplus
extern "C" {
#endif

/* --- TMC2209 #1 (U3) --- */
#define PIN_TMC1_STEP_Port   GPIOA
#define PIN_TMC1_STEP_Pin    GPIO_PIN_4
#define PIN_TMC1_DIR_Port    GPIOA
#define PIN_TMC1_DIR_Pin     GPIO_PIN_5
#define PIN_TMC1_EN_Port     GPIOA
#define PIN_TMC1_EN_Pin      GPIO_PIN_6

/* --- TMC2209 #2 (U4) --- */
#define PIN_TMC2_STEP_Port   GPIOA
#define PIN_TMC2_STEP_Pin    GPIO_PIN_7
#define PIN_TMC2_DIR_Port    GPIOB
#define PIN_TMC2_DIR_Pin     GPIO_PIN_0
#define PIN_TMC2_EN_Port     GPIOB
#define PIN_TMC2_EN_Pin      GPIO_PIN_1

/* --- Opto / count inputs (active-low via PC817) --- */
#define PIN_BUP_Port         GPIOA
#define PIN_BUP_Pin          GPIO_PIN_0
#define PIN_IN2_Port         GPIOA
#define PIN_IN2_Pin          GPIO_PIN_1
#define PIN_IN3_Port         GPIOA
#define PIN_IN3_Pin          GPIO_PIN_2
#define PIN_CNT5_Port        GPIOA
#define PIN_CNT5_Pin         GPIO_PIN_3

/* --- Dual H-bridge power modules (U_PWR*) --- */
#define PIN_PWR_PWM1_Port    GPIOB
#define PIN_PWR_PWM1_Pin     GPIO_PIN_10
#define PIN_PWR_PWM2_Port    GPIOB
#define PIN_PWR_PWM2_Pin     GPIO_PIN_11
#define PIN_PWR_EN1_Port     GPIOB
#define PIN_PWR_EN1_Pin      GPIO_PIN_12
#define PIN_PWR_EN2_Port     GPIOB
#define PIN_PWR_EN2_Pin      GPIO_PIN_13
#define PIN_PWR_FAULT_Port   GPIOB
#define PIN_PWR_FAULT_Pin    GPIO_PIN_14

/* --- Vibration driver (U_VIB) --- */
#define PIN_VIB_CTRL_Port    GPIOB
#define PIN_VIB_CTRL_Pin     GPIO_PIN_15
#define PIN_VIB_FAULT_Port   GPIOA
#define PIN_VIB_FAULT_Pin    GPIO_PIN_8

/* --- TM1637 display (J_DISP) --- */
#define PIN_TM1637_CLK_Port  GPIOA
#define PIN_TM1637_CLK_Pin   GPIO_PIN_15
#define PIN_TM1637_DIO_Port  GPIOD
#define PIN_TM1637_DIO_Pin   GPIO_PIN_0

/* --- 4x4 keypad --- */
#define PIN_KEY_ROW0_Port    GPIOB
#define PIN_KEY_ROW0_Pin     GPIO_PIN_9
#define PIN_KEY_ROW1_Port    GPIOB
#define PIN_KEY_ROW1_Pin     GPIO_PIN_8
#define PIN_KEY_ROW2_Port    GPIOB
#define PIN_KEY_ROW2_Pin     GPIO_PIN_7
#define PIN_KEY_ROW3_Port    GPIOB
#define PIN_KEY_ROW3_Pin     GPIO_PIN_6
#define PIN_KEY_COL0_Port    GPIOB
#define PIN_KEY_COL0_Pin     GPIO_PIN_5
#define PIN_KEY_COL1_Port    GPIOB
#define PIN_KEY_COL1_Pin     GPIO_PIN_4
#define PIN_KEY_COL2_Port    GPIOB
#define PIN_KEY_COL2_Pin     GPIO_PIN_3
#define PIN_KEY_COL3_Port    GPIOD
#define PIN_KEY_COL3_Pin     GPIO_PIN_3

/* --- USART1 ↔ CH340 --- */
#define PIN_USART1_TX_Port   GPIOA
#define PIN_USART1_TX_Pin    GPIO_PIN_9
#define PIN_USART1_RX_Port   GPIOA
#define PIN_USART1_RX_Pin    GPIO_PIN_10

/* --- Status LEDs (active-high) --- */
#define PIN_LED_RUN_Port     GPIOB
#define PIN_LED_RUN_Pin      GPIO_PIN_2
#define PIN_LED_ERR_Port     GPIOC
#define PIN_LED_ERR_Pin      GPIO_PIN_6

/* --- SWD / boot (do not drive as GPIO while debugging) --- */
#define PIN_SWDIO_Port       GPIOA
#define PIN_SWDIO_Pin        GPIO_PIN_13
#define PIN_SWCLK_Port       GPIOA
#define PIN_SWCLK_Pin        GPIO_PIN_14

#ifdef __cplusplus
}
#endif

#endif /* BOARD_PINS_H */
