# CountingMachine — Makefile build (STM32CubeIDE GNU tools)
# Usage (PowerShell):
#   mingw32-make -C firmware
#   or: make all

TARGET   = CountingMachine_G030
BUILD    = build

# CubeIDE toolchain (override TOOLCHAIN if needed)
TOOLCHAIN ?= C:/ST/STM32CubeIDE_2.2.0/STM32CubeIDE/plugins/com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32.14.3.rel1.win32_1.0.100.202602081740/tools/bin

PREFIX   = $(TOOLCHAIN)/arm-none-eabi-
CC       = $(PREFIX)gcc
AS       = $(PREFIX)gcc -x assembler-with-cpp
OBJCOPY  = $(PREFIX)objcopy
SIZE     = $(PREFIX)size

LIB      = _lib
LDSCRIPT = STM32G030C8TX_FLASH.ld

C_DEFS = \
  -DUSE_HAL_DRIVER \
  -DSTM32G030xx

C_INCLUDES = \
  -ICore/Inc \
  -I$(LIB)/hal/Inc \
  -I$(LIB)/cmsis_device/Include \
  -I$(LIB)/cmsis_core/CMSIS/Core/Include

# Application
APP_SRCS = \
  Core/Src/main.c \
  Core/Src/app.c \
  Core/Src/app_count_ui.c \
  Core/Src/board_motors.c \
  Core/Src/count_filter.c \
  Core/Src/count_sensor.c \
  Core/Src/keypad_4x4.c \
  Core/Src/nv_settings.c \
  Core/Src/stm32g0xx_hal_msp.c \
  Core/Src/stm32g0xx_it.c \
  Core/Src/syscalls.c \
  Core/Src/tm1637.c \
  Core/Src/tmc_step.c \
  $(LIB)/cmsis_device/Source/Templates/system_stm32g0xx.c

# Minimal HAL
HAL_SRCS = \
  $(LIB)/hal/Src/stm32g0xx_hal.c \
  $(LIB)/hal/Src/stm32g0xx_hal_cortex.c \
  $(LIB)/hal/Src/stm32g0xx_hal_dma.c \
  $(LIB)/hal/Src/stm32g0xx_hal_dma_ex.c \
  $(LIB)/hal/Src/stm32g0xx_hal_exti.c \
  $(LIB)/hal/Src/stm32g0xx_hal_flash.c \
  $(LIB)/hal/Src/stm32g0xx_hal_flash_ex.c \
  $(LIB)/hal/Src/stm32g0xx_hal_gpio.c \
  $(LIB)/hal/Src/stm32g0xx_hal_pwr.c \
  $(LIB)/hal/Src/stm32g0xx_hal_pwr_ex.c \
  $(LIB)/hal/Src/stm32g0xx_hal_rcc.c \
  $(LIB)/hal/Src/stm32g0xx_hal_rcc_ex.c

ASM_SRCS = $(LIB)/cmsis_device/Source/Templates/gcc/startup_stm32g030xx.s

C_SOURCES = $(APP_SRCS) $(HAL_SRCS)

MCU = -mcpu=cortex-m0plus -mthumb
OPT = -Og
CFLAGS = $(MCU) $(C_DEFS) $(C_INCLUDES) $(OPT) -Wall -fdata-sections -ffunction-sections -g -gdwarf-2
CFLAGS += -MMD -MP -MF"$(@:%.o=%.d)"
ASFLAGS = $(MCU) -g
LDFLAGS = $(MCU) -T$(LDSCRIPT) -Wl,-Map=$(BUILD)/$(TARGET).map,--cref -Wl,--gc-sections --specs=nano.specs --specs=nosys.specs

OBJECTS = $(addprefix $(BUILD)/,$(notdir $(C_SOURCES:.c=.o)))
OBJECTS += $(addprefix $(BUILD)/,$(notdir $(ASM_SRCS:.s=.o)))

vpath %.c $(sort $(dir $(C_SOURCES)))
vpath %.s $(sort $(dir $(ASM_SRCS)))

.PHONY: all clean size

all: $(BUILD)/$(TARGET).elf $(BUILD)/$(TARGET).hex $(BUILD)/$(TARGET).bin size

$(BUILD):
	mkdir -p $(BUILD)

$(BUILD)/%.o: %.c | $(BUILD)
	$(CC) -c $(CFLAGS) $< -o $@

$(BUILD)/%.o: %.s | $(BUILD)
	$(AS) -c $(ASFLAGS) $< -o $@

$(BUILD)/$(TARGET).elf: $(OBJECTS) $(LDSCRIPT)
	$(CC) $(OBJECTS) $(LDFLAGS) -o $@

$(BUILD)/$(TARGET).hex: $(BUILD)/$(TARGET).elf
	$(OBJCOPY) -O ihex $< $@

$(BUILD)/$(TARGET).bin: $(BUILD)/$(TARGET).elf
	$(OBJCOPY) -O binary -S $< $@

size: $(BUILD)/$(TARGET).elf
	$(SIZE) $<

clean:
	rm -rf $(BUILD)
