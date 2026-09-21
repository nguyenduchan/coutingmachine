"""ESP32-WROOM-32 pinmap for compact counting-machine carrier.

BOM sync: no 595/ULN/TFT/ENC/blower/HOME/buzzer.
TMC socket only; TM1637 on-board; 7seg + keypad via external headers; count sensor = BUP-U OR fiber (GPIO4).
"""

from __future__ import annotations

# Espressif ESP-WROOM-32 module pad numbers (antenna = top / +Y).
# Left column pads 1..19 top→bottom; right column 38..20 top→bottom (CCW).
# Names match nets we wire; NC pads omitted from GPIO map.

WROOM_LEFT = [
    (1, "GND"),
    (2, "3V3"),
    (3, "EN"),
    (4, "IO36"),
    (5, "IO39"),
    (6, "IO34"),
    (7, "IO35"),
    (8, "IO32"),
    (9, "IO33"),
    (10, "IO25"),
    (11, "IO26"),
    (12, "IO27"),
    (13, "IO14"),
    (14, "IO12"),
    (15, "GND"),
    (16, "IO13"),
    (17, "NC17"),
    (18, "NC18"),
    (19, "NC19"),
]

WROOM_RIGHT = [
    (38, "GND"),
    (37, "IO23"),
    (36, "IO22"),
    (35, "TXD0"),  # GPIO1 → CH340 RXD
    (34, "RXD0"),  # GPIO3 → CH340 TXD
    (33, "IO21"),
    (32, "NC32"),
    (31, "IO19"),
    (30, "IO18"),
    (29, "IO5"),
    (28, "IO17"),
    (27, "IO16"),
    (26, "IO4"),
    (25, "IO0"),
    (24, "IO2"),
    (23, "IO15"),
    (22, "NC22"),
    (21, "NC21"),
    (20, "GND"),
]

PIN_BY_NAME: dict[str, int] = {}
for num, name in WROOM_LEFT + WROOM_RIGHT:
    PIN_BY_NAME[name] = num
    if name.startswith("IO") and name[2:].isdigit():
        PIN_BY_NAME[int(name[2:])] = num

# Function → GPIO number (classic ESP32)
TMC_GPIO = {"STEP": 16, "DIR": 17, "EN": 18}
BUP_GPIO = 4  # shared: J14 U-slot IR XOR J15 fiber amp (NPN → PC817)
TM1637_GPIO = {"CLK": 22, "DIO": 23}
KEYPAD_GPIO = {
    "ROW0": 13,
    "ROW1": 12,
    "ROW2": 14,
    "ROW3": 27,
    "COL0": 26,
    "COL1": 33,
    "COL2": 32,
    "COL3": 5,
}

USED_GPIO = sorted(
    {
        *TMC_GPIO.values(),
        BUP_GPIO,
        *TM1637_GPIO.values(),
        *KEYPAD_GPIO.values(),
    }
)
assert len(USED_GPIO) == 14, USED_GPIO


def wroom_pad_local(pin_num: int) -> tuple[float, float]:
    """Local XY of WROOM pad; origin = module center; antenna +Y."""
    pitch = 1.27
    x_l, x_r = -9.0, 9.0
    y0 = 11.43  # pin 1 / 38 at top
    if pin_num <= 19:
        return (x_l, y0 - (pin_num - 1) * pitch)
    # right column: 38 at top … 20 at bottom
    return (x_r, y0 - (38 - pin_num) * pitch)
