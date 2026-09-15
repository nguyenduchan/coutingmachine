"""STM32G030C8T6 (LQFP48) pinmap for compact counting-machine carrier.

Dual TMC sockets; opto IN (NPN only); pluggable power (MOSFET) + vibratory control sockets.
"""

from __future__ import annotations

LQFP48_PINS: list[tuple[int, str]] = [
    (1, "PC13"),
    (2, "PC14"),
    (3, "PC15"),
    (4, "VBAT"),
    (5, "VREF+"),
    (6, "VDD"),
    (7, "VSS"),
    (8, "PF0"),
    (9, "PF1"),
    (10, "NRST"),
    (11, "PA0"),
    (12, "PA1"),
    (13, "PA2"),
    (14, "PA3"),
    (15, "PA4"),
    (16, "PA5"),
    (17, "PA6"),
    (18, "PA7"),
    (19, "PB0"),
    (20, "PB1"),
    (21, "PB2"),
    (22, "PB10"),
    (23, "PB11"),
    (24, "PB12"),
    (25, "PB13"),
    (26, "PB14"),
    (27, "PB15"),
    (28, "PA8"),
    (29, "PA9"),
    (30, "PC6"),
    (31, "PC7"),
    (32, "PA10"),
    (33, "PA11"),
    (34, "PA12"),
    (35, "PA13"),
    (36, "PA14"),
    (37, "PA15"),
    (38, "PD0"),
    (39, "PD1"),
    (40, "PD2"),
    (41, "PD3"),
    (42, "PB3"),
    (43, "PB4"),
    (44, "PB5"),
    (45, "PB6"),
    (46, "PB7"),
    (47, "PB8"),
    (48, "PB9"),
]

PIN_BY_NAME: dict[str, int] = {name: num for num, name in LQFP48_PINS}

TMC_PINS = {"STEP": "PA0", "DIR": "PA1", "EN": "PA2"}
TMC2_PINS = {"STEP": "PA6", "DIR": "PA7", "EN": "PA8"}

BUP_PIN = "PA3"
IN2_PIN = "PB15"
IN3_PIN = "PB4"
# Edge jack J_CNT5 — cheap 5V through-beam / IR (NPN or OC to GND)
CNT5_PIN = "PD1"

# One pluggable MOSFET module per 24V output channel (U_PWR1 / U_PWR2)
PWR_PINS = {
    "PWM1": "PA11",
    "PWM2": "PA12",
    "EN1": "PB5",
    "EN2": "PB6",
    "FAULT": "PB7",  # shared OD from either module
}
# Pluggable AC vibratory / SSR control (U_VIB) — SSR lives on module
VIB_PINS = {
    "CTRL": "PB8",
    "FAULT": "PB9",  # input
}

TM1637_PINS = {"CLK": "PA4", "DIO": "PA5"}
KEYPAD_PINS = {
    "ROW0": "PB0",
    "ROW1": "PB1",
    "ROW2": "PB2",
    "ROW3": "PB10",
    "COL0": "PB11",
    "COL1": "PB12",
    "COL2": "PB13",
    "COL3": "PB14",
}
USART1_PINS = {"TX": "PA9", "RX": "PA10"}
# SWDIO kept for factory pogo if needed; SWCLK=BOOT0 for USB-UART bootloader
BOOT_PINS = {"SWDIO": "PA13", "SWCLK": "PA14"}  # no SWO / no J_DBG (USB nạp)

USED_GPIO = sorted(
    {
        *TMC_PINS.values(),
        *TMC2_PINS.values(),
        BUP_PIN,
        IN2_PIN,
        IN3_PIN,
        CNT5_PIN,
        *PWR_PINS.values(),
        *VIB_PINS.values(),
        *TM1637_PINS.values(),
        *KEYPAD_PINS.values(),
        *USART1_PINS.values(),
        *BOOT_PINS.values(),
    }
)
assert len(USED_GPIO) == 31, USED_GPIO
assert len(set(USED_GPIO)) == 31, USED_GPIO
