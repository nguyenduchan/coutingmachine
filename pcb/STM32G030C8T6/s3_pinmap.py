"""ESP32-S3-DevKitC-1 (44-pin) pinmap for counting-machine baseboard.

USB at top. Left = J1 pads 1..22, Right = J3 pads 23..44.
Avoid GPIO19/20 (USB) and GPIO43/44 (UART0 console).

TARGET PART: ESP32-S3-DevKitC-1 **N16R8** (octal PSRAM).
GPIO35/36/37 unusable (octal PSRAM).

BOM sync:
  - U10 = Shopee 74HC595-24IO module (3x595) east of ESP32 -> ULN (12 of 24 Q)
  - 4x PC817: HOME x3 + BUP
  - TFT LCD SPI + XPT2046 touch (MISO/T_CS/T_IRQ)
  - EC11 ENC on IO38/IO41
  - Spare: IO7, IO8, IO14, IO15

Never buy a "V" suffix part (N16R8V / N32R16V).
"""

from __future__ import annotations

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
    (24, "TX0", "bidirectional"),
    (25, "RX0", "bidirectional"),
    (26, "IO1", "bidirectional"),
    (27, "IO2", "bidirectional"),
    (28, "IO42", "bidirectional"),
    (29, "IO41", "bidirectional"),
    (30, "IO40", "bidirectional"),
    (31, "IO39", "bidirectional"),
    (32, "IO38", "bidirectional"),
    (33, "IO37", "bidirectional"),
    (34, "IO36", "bidirectional"),
    (35, "IO35", "bidirectional"),
    (36, "IO0", "bidirectional"),
    (37, "IO45", "bidirectional"),
    (38, "IO48", "bidirectional"),
    (39, "IO47", "bidirectional"),
    (40, "IO21", "bidirectional"),
    (41, "IO20", "bidirectional"),
    (42, "IO19", "bidirectional"),
    (43, "GNDb", "passive"),
    (44, "GNDc", "passive"),
]

OPTO_GPIO = [
    (1, "IO1"),
    (2, "IO2"),
    (4, "IO4"),
    (5, "IO5"),
]

# 74HC595-24IO module CTRL: LDSI/LDSCK/LDSTR/LDEN = SER/SRCLK/RCLK/OE
SHIFT_GPIO = {"SER": 10, "SRCLK": 11, "RCLK": 12, "OE": 13}
# Phase nets are SR_Q0..SR_Q11 (not direct GPIO). Kept empty for verify helpers.
BYJ_GPIO: dict = {}
DRV_MOTORS: list = []

TMC_GPIO = {"STEP": 16, "DIR": 17, "EN": 18}
TMC_UART_GPIO = None

TFT_GPIO = {
    "SCK": 39,
    "MOSI": 40,
    "MISO": 47,  # T_DO
    "CS": 42,
    "DC": 21,
    "RST": 46,
    "BL": 45,
    "T_CS": 48,
    "T_IRQ": 6,
}

# Note: DevKitC-1 v1.1 WS2812 also on IO38 — LED may flicker with ENC.
ENC_GPIO = {"A": 38, "B": 41}
ENC_JACK = "J18"

BUZZER_GPIO = 9
MOSFET_GPIO = 3

SPARE_GPIO = (7, 8, 14, 15)

PIN_BY_NAME = {name: num for num, name, _ in LEFT_PINS + RIGHT_PINS}
for num, name, _ in LEFT_PINS + RIGHT_PINS:
    if name.startswith("IO") and name[2:].isdigit():
        PIN_BY_NAME[int(name[2:])] = num


def pad_local(pin_num: int) -> tuple[float, float]:
    pitch = 2.54
    row = 25.4
    if pin_num <= 22:
        return (0.0, (pin_num - 1) * pitch)
    return (row, (pin_num - 23) * pitch)
