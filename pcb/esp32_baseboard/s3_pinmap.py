"""ESP32-S3-DevKitC-1 (44-pin) pinmap for counting-machine baseboard.

USB at top. Left = J1 pads 1..22, Right = J3 pads 23..44.
Avoid GPIO19/20 (USB) and GPIO43/44 (UART0 console).

TARGET PART: ESP32-S3-DevKitC-1 **N16R8** (octal PSRAM) - the variant that is
actually stocked in VN. Octal PSRAM claims GPIO33-37, so **GPIO35/36/37 are
unusable** here and only 33 of the 36 header GPIOs are left.

That budget is exact: 28 for the design + 5 that must stay free (USB IO19/20,
UART0 IO43/44, BOOT IO0) = 33.

HMI: TFT ILI9488 SPI + XPT2046 resistive touch (shared SCK/MOSI; dedicated
MISO=T_DO + T_CS; no T_IRQ — poll). LCD SDO is NOT wired. GPIO41 and GPIO38
carry the EC11 rotary encoder (ENC_A/B).
On-screen Enter replaces ENC_SW so no third GPIO is required.

ENC_A and the buzzer swapped GPIOs (IO9 <-> IO38) for layout: both header
rows of the socket are fixed, and IO38/IO41 are the pair that comes out on
the same side as J18, so the encoder no longer needs a net crossing the
socket. The buzzer is a single output and its jack moved instead.

GPIO0 carries the BOOT button, so it is input-only in practice.

GPIO45/46 ARE usable as outputs: they are strapping pins held by an internal
weak pull-down through reset, so whatever they drive sees a defined LOW until
firmware takes over. That is exactly the safe state for a backlight and for an
active-low reset, which is why the TFT uses them.

Never buy a "V" suffix part (N16R8V / N32R16V): those run VDD_SPI at 1.8 V,
which drags GPIO47/48 down to 1.8 V logic and breaks TFT MISO / T_CS.
"""

from __future__ import annotations

# Official DevKitC-1 header names (silk-friendly)
LEFT_PINS = [
    (1, "3V3", "power_out"),
    (2, "3V3b", "power_out"),
    (3, "RST", "input"),
    (4, "IO4", "bidirectional"),
    (5, "IO5", "bidirectional"),
    (6, "IO6", "bidirectional"),
    (7, "IO7", "bidirectional"),
    (8, "IO15", "bidirectional"),
    (9, "IO16", "bidirectional"),
    (10, "IO17", "bidirectional"),
    (11, "IO18", "bidirectional"),
    (12, "IO8", "bidirectional"),
    (13, "IO3", "bidirectional"),
    (14, "IO46", "bidirectional"),
    (15, "IO9", "bidirectional"),
    (16, "IO10", "bidirectional"),
    (17, "IO11", "bidirectional"),
    (18, "IO12", "bidirectional"),
    (19, "IO13", "bidirectional"),
    (20, "IO14", "bidirectional"),
    (21, "5V", "power_in"),
    (22, "GND", "passive"),
]

RIGHT_PINS = [
    (23, "GND", "passive"),
    (24, "TX0", "bidirectional"),  # IO43
    (25, "RX0", "bidirectional"),  # IO44
    (26, "IO1", "bidirectional"),
    (27, "IO2", "bidirectional"),
    (28, "IO42", "bidirectional"),
    (29, "IO41", "bidirectional"),
    (30, "IO40", "bidirectional"),
    (31, "IO39", "bidirectional"),
    (32, "IO38", "bidirectional"),
    (33, "IO37", "bidirectional"),  # NC on octal — do not route
    (34, "IO36", "bidirectional"),
    (35, "IO35", "bidirectional"),
    (36, "IO0", "bidirectional"),
    (37, "IO45", "bidirectional"),
    (38, "IO48", "bidirectional"),
    (39, "IO47", "bidirectional"),
    (40, "IO21", "bidirectional"),
    (41, "IO20", "bidirectional"),  # USB D+
    (42, "IO19", "bidirectional"),  # USB D-
    (43, "GNDb", "passive"),
    (44, "GNDc", "passive"),
]

# --- Functional assignment (commercial SKU) ---
# Opto OUT1..6 = limits, OUT7 = BUP. OUT8 field channel exists on U9/J4 but
# is NOT wired to the MCU (GPIO9 is the buzzer).
OPTO_GPIO = [
    (1, "IO1"),
    (2, "IO2"),
    (4, "IO4"),
    (5, "IO5"),
    (6, "IO6"),
    (7, "IO7"),
    (8, "IO8"),
]

# DRV8871 ×3 (IN1/IN2)
DRV_MOTORS = [
    ("5", 10, 11, 34, 35),  # U5 IO10/11
    ("6", 12, 13, 36, 37),  # U6 IO12/13
    ("7", 14, 15, 38, 39),  # U7 IO14/15
]

# EN is active low and floats at reset -> a 10k pull-up to 3V3 on the
# baseboard is required, or the stepper is energised from power-on until
# firmware runs.
# No UART: PDN_UART would need GPIO36, which octal PSRAM has taken. Set the
# run current with the module's Vref trimmer; DRV_STATUS readback is not
# available on this build.
TMC_GPIO = {"STEP": 16, "DIR": 17, "EN": 18}
TMC_UART_GPIO = None  # unavailable on N16R8 (GPIO36 = octal PSRAM)

# TFT SPI + XPT2046 touch (polled — no IRQ pin).
# RST and BL sit on the two strapping pins on purpose: both are pulled low
# through reset, so the panel comes up held in reset with the backlight off
# and no external resistor. Firmware releases RST, then ramps BL on LEDC.
# MISO = T_DO only (do NOT connect LCD SDO). ENC is on IO38/IO41.
TFT_GPIO = {
    "SCK": 39,  # + T_CLK on cable
    "MOSI": 40,  # + T_DIN on cable
    "MISO": 47,  # T_DO only
    "CS": 42,  # LCD_CS
    "DC": 21,
    "RST": 46,
    "BL": 45,
    "T_CS": 48,
}

# GPIO38 also drives the on-board WS2812 on DevKitC-1 **v1.1**, so ENC_A
# shares it. The WS2812 only presents its DIN input, so driving IO38 as an
# encoder input is fine; the LED may flicker as the knob turns. Pin the BOM to
# v1.1 — on v1.0 the WS2812 is on GPIO48 instead, i.e. on touch T_CS.
# EC11 on housing wall → cable → J18 (GND/3V3/A/B). SW unused — Enter on TFT.
# Pull-ups: KY-040 module has them, or use INPUT_PULLUP / 10k to 3V3.
ENC_GPIO = {"A": 38, "B": 41}  # J18.3 CLK→IO38, J18.4 DT→IO41
ENC_JACK = "J18"  # PinHeader 1x04 on carrier; encoder is off-board

BUZZER_GPIO = 9

# GPIO3 is a strapping pin (JTAG source select) with NO internal pull at
# reset, so it floats. A 10k pull-down to GND is required, otherwise the
# diaphragm pump can switch on during boot.
MOSFET_GPIO = 3

# KiCad symbol/footprint pad number for a GPIO silk name like "IO10"
PIN_BY_NAME = {name: num for num, name, _ in LEFT_PINS + RIGHT_PINS}
# Also map logical GPIO numbers used in DRV_MOTORS
for num, name, _ in LEFT_PINS + RIGHT_PINS:
    if name.startswith("IO") and name[2:].isdigit():
        PIN_BY_NAME[int(name[2:])] = num


def pad_local(pin_num: int) -> tuple[float, float]:
    """Footprint local (x,y) for pad number (USB-top convention)."""
    pitch = 2.54
    row = 25.4
    if pin_num <= 22:
        return (0.0, (pin_num - 1) * pitch)
    return (row, (pin_num - 23) * pitch)
