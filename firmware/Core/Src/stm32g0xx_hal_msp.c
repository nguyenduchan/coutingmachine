/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file    stm32g0xx_hal_msp.c
  * @brief   HAL MSP init — CubeMX regenerates peripheral MSP here
  ******************************************************************************
  */
/* USER CODE END Header */

#include "main.h"

void HAL_MspInit(void)
{
  __HAL_RCC_SYSCFG_CLK_ENABLE();
  __HAL_RCC_PWR_CLK_ENABLE();
}
