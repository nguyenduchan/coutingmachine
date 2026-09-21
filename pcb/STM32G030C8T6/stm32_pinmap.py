"""STM32G030C8T6 (LQFP48) pinmap for compact counting-machine carrier.

Pin sides (package top view, pin1 NW, CCW):
  W: 1–12   S: 13–24   E: 25–36   N: 37–48
Route short: N→HMI, W→opto/count, S→TMC, E/SE→PWR/VIB/USB-UART.
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

# South edge — TMC inland / motors (LQFP south pads PA4–PB1)
TMC_PINS = {"STEP": "PA4", "DIR": "PA5", "EN": "PA6"}
TMC2_PINS = {"STEP": "PA7", "DIR": "PB0", "EN": "PB1"}

# West — opto cluster + north count jacks (PA0–PA3)
BUP_PIN = "PA0"
IN2_PIN = "PA1"
IN3_PIN = "PA2"
CNT5_PIN = "PA3"

# South→east wrap — U_PWR* / U_VIB on south-east
PWR_PINS = {
    "PWM1": "PB10",
    "PWM2": "PB11",
    "EN1": "PB12",
    "EN2": "PB13",
    "FAULT": "PB14",
}
VIB_PINS = {
    "CTRL": "PB15",
    "FAULT": "PA8",
}

# North — TM1637 + keypad (toward J_DISP / J_KEY)
# J_KEY rot90: pad1 west → pad8 east; LQFP north W→E: PB9…PB3, PD3 (match → 0 cross)
TM1637_PINS = {"CLK": "PA15", "DIO": "PD0"}
KEYPAD_PINS = {
    "ROW0": "PB9",
    "ROW1": "PB8",
    "ROW2": "PB7",
    "ROW3": "PB6",
    "COL0": "PB5",
    "COL1": "PB4",
    "COL2": "PB3",
    "COL3": "PD3",
}

# East — CH340 / USB (USART1 fixed)
USART1_PINS = {"TX": "PA9", "RX": "PA10"}
BOOT_PINS = {"SWDIO": "PA13", "SWCLK": "PA14"}

# Status LEDs (active-high: GPIO → R → LED → GND); Hi-Z boot = OFF
LED_PINS = {"RUN": "PB2", "ERR": "PC6"}

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
        *LED_PINS.values(),
    }
)
assert len(USED_GPIO) == 33, USED_GPIO
assert len(set(USED_GPIO)) == 33, USED_GPIO
