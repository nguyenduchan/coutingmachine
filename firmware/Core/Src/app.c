#include "app.h"
#include "main.h"
#include "board_pins.h"
#include "board_motors.h"
#include "board_config.h"
#include "count_sensor.h"
#include "keypad_4x4.h"
#include "tm1637.h"
#include "app_count_ui.h"

static void Board_Extra_GPIO_Init(void);
static void Board_SafeDefaults(void);

void App_Init(void)
{
    Board_Extra_GPIO_Init();
    Board_SafeDefaults();

    motors_init();
    count_sensor_init();
    keypad_init();
    tm1637_init();
    tm1637_set_brightness(5);
    count_ui_init();
}

void App_Loop(void)
{
    static uint32_t led_ms;

    motors_tick();
    count_sensor_tick();
    keypad_tick();

    keypad_event_t kev;
    while (keypad_poll(&kev)) {
        count_ui_on_key(&kev); /* PRESS + RELEASE (giữ D = RPM) */
    }

    count_ui_tick();

    uint32_t now = HAL_GetTick();
    if ((now - led_ms) >= 500u) {
        led_ms = now;
        HAL_GPIO_TogglePin(PIN_LED_RUN_Port, PIN_LED_RUN_Pin);
    }
}

static void Board_Extra_GPIO_Init(void)
{
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_GPIOD_CLK_ENABLE();

    GPIO_InitTypeDef g = {0};

    g.Mode = GPIO_MODE_OUTPUT_PP;
    g.Pull = GPIO_NOPULL;
    g.Speed = GPIO_SPEED_FREQ_LOW;
    g.Pin = PIN_DO1_Pin | PIN_DO2_Pin | PIN_LED_RUN_Pin;
    HAL_GPIO_Init(GPIOB, &g);

    g.Pin = PIN_LED_ERR_Pin;
    HAL_GPIO_Init(GPIOC, &g);

    g.Mode = GPIO_MODE_INPUT;
    g.Pull = GPIO_PULLUP;
    g.Pin = PIN_BUP_Pin | PIN_IN2_Pin | PIN_IN3_Pin | PIN_CNT5_Pin;
    HAL_GPIO_Init(GPIOA, &g);
}

static void Board_SafeDefaults(void)
{
    HAL_GPIO_WritePin(PIN_DO1_Port, PIN_DO1_Pin, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(PIN_DO2_Port, PIN_DO2_Pin, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(PIN_LED_RUN_Port, PIN_LED_RUN_Pin, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(PIN_LED_ERR_Port, PIN_LED_ERR_Pin, GPIO_PIN_RESET);
}
