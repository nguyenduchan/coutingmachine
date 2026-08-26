#!/usr/bin/env python3
"""Generate dual MP1584EN + TMC2209 + 2x PC817-4CH + 3x DRV8871 + ESP32-S3 carrier.

Power path (modules on BOTTOM):
  12V-3A PSU --J1--> F1 PTC --> +12V (D1 TVS to GND)
       --> MP1584EN U2  -> +5V      -> ESP32-S3 / logic / TFT / buzzer
       --> MP1584EN U8  -> +5V_BLW -> AOD4184 (J16) -> diaphragm pump 5V (burst)
       --> TMC2209 (U3) VM=12V + VIO=3V3
       --> DRV8871 x3 (U5-U7) VM=12V
TOP: J2 NEMA17, J4 OPTO field, J5-J13 motors+limits, J14 BUP,
     J15 buzzer, J16 AOD4184 blower, J17 TFT+touch.
MCU: ESP32-S3-DevKitC-1 (44-pin, 2x22 @ 2.54, row 25.4). Prefer N8R2/N16R8;
     do not use GPIO35-37 on octal flash boards.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from s3_pinmap import (
    BUZZER_GPIO,
    DRV_MOTORS,
    LEFT_PINS,
    MOSFET_GPIO,
    OPTO_GPIO,
    PIN_BY_NAME,
    RIGHT_PINS,
    TFT_GPIO,
    TMC_GPIO,
    pad_local,
)

ROOT = Path(__file__).resolve().parent
LIB = ROOT / "libraries"
PRETTY = LIB / "ESP32_Carrier.pretty"

PITCH = 2.54
ROW_SPACING = 25.4
PAD_SIZE = 1.7
PAD_DRILL = 1.0
S3_PINS_PER_SIDE = 22

# MP1584EN mini buck ~22 x 17 mm (Shopee G178 / fixed 5V preferred).
# Pads IN+/IN- | OUT+/OUT- — VERIFY pitch on your module before fab.
MP1584_W = 22.0
MP1584_H = 17.0
MP1584_PAD_SPAN_X = 16.0  # left IN <-> right OUT pad centers
MP1584_PAD_SPAN_Y = 6.0   # + <-> - on each end (typical mini module)
# Aliases so older Mini560 layout math keeps working
MINI560_W = MP1584_W
MINI560_H = MP1584_H
MINI560_PAD_SPAN_X = MP1584_PAD_SPAN_X
MINI560_PAD_SPAN_Y = MP1584_PAD_SPAN_Y

TB_PITCH = 5.0
BOTTOM_ROT = 180

TMC_W = 20.4
TMC_H = 20.4
TMC_ROW = 15.24

MOTOR_HEADER = [
    ("1", "A2", 11),
    ("2", "A1", 12),
    ("3", "B1", 13),
    ("4", "B2", 14),
]

# J3 removed (unused). TFT/touch on J17.
# 11 pins: display block 3-8, touch block 9-11. RST is shared by the LCD and
# the touch controller (both active low); BL is PWM, not a 3V3 tie.
# No MISO - the SPI link is write-only so GPIO41 can carry the touch IRQ,
# which octal PSRAM (N16R8) would otherwise leave homeless.
TFT_HEADER = [
    ("1", "GND"),
    ("2", "3V3"),
    ("3", "SCK"),
    ("4", "MOSI"),
    ("5", "CS"),
    ("6", "DC"),
    ("7", "RST"),
    ("8", "BL"),
    ("9", "SDA"),
    ("10", "SCL"),
    ("11", "T_INT"),
]
TFT_PINS = len(TFT_HEADER)
TFT_FP = f"PinHeader_1x{TFT_PINS:02d}_TFT"
TFT_SYM = f"Conn_1x{TFT_PINS:02d}_TFT"

BUZZER_HEADER = [("1", "VCC5"), ("2", "GND"), ("3", "SIG")]
MOSFET_HEADER = [("1", "PWM"), ("2", "GND"), ("3", "+5V_BLW"), ("4", "FAN-")]

VIA12_DRILL = 0.6
VIA12_DIA = 1.1
VIA12_COUNT_X = 3
VIA12_COUNT_Y = 2
VIA12_PITCH = 1.8

PC817_4CH_W = 48.0
PC817_4CH_H = 38.0
PC817_4CH_ROW = 25.4  # IN row <-> OUT row (VERIFY on Shopee 4CH module)
# Legacy aliases (8CH removed from layout)
PC817_W = PC817_4CH_W
PC817_H = PC817_4CH_H
PC817_ROW = PC817_4CH_ROW
OPTO_FIELD_HEADER = [
    ("1", "GND_I"),
    ("2", "VCC_I"),
    ("3", "IN1"),
    ("4", "IN2"),
    ("5", "IN3"),
    ("6", "IN4"),
    ("7", "IN5"),
    ("8", "IN6"),
    ("9", "IN7"),
    ("10", "IN8"),
]

# DRV8871 breakout ~28x20 mm (VERIFY Shopee module before fab)
DRV_W = 28.0
DRV_H = 20.0
# Keep pad roles compatible with old L298N routing style
# (ref_suffix, IN1_gpio, IN2_gpio, mot_net_a, mot_net_b)
L298N_MOTORS = DRV_MOTORS  # alias for legacy code sections
L298N_W = DRV_W
L298N_H = DRV_H

def pad_world(at_x: float, at_y: float, rot_deg: float, lx: float, ly: float) -> tuple[float, float]:
    """Footprint local pad -> board coordinates (KiCad rot 0/180)."""
    if int(rot_deg) % 360 == 180:
        return (at_x - lx, at_y - ly)
    return (at_x + lx, at_y + ly)


def write_pin_header_footprint(n_pins: int, name: str, pin_names: list[str]) -> Path:
    """1xN male pin header on TOP (F.Cu) - pins stick up for external wiring."""
    pitch = PITCH
    span = (n_pins - 1) * pitch
    y0, y1 = -1.8, span + 1.8
    x0, x1 = -1.8, 1.8
    lines: list[str] = []
    a = lines.append
    a(f'(footprint "{name}"')
    a("\t(version 20260206)")
    a('\t(generator "gen_power_carrier.py")')
    a('\t(generator_version "1.0")')
    a('\t(layer "F.Cu")')
    a(f'\t(descr "1x{n_pins} pin header 2.54mm TOP side external wiring")')
    a('\t(tags "PinHeader 2.54mm male top")')
    a('\t(property "Reference" "J**"')
    a(f"\t\t(at 0 {y0 - 2.0} 0)")
    a('\t\t(layer "F.SilkS")')
    a("\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a("\t)")
    a(f'\t(property "Value" "{name}"')
    a(f"\t\t(at 0 {y1 + 2.0} 0)")
    a('\t\t(layer "F.Fab")')
    a("\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a("\t)")
    a('\t(property "Datasheet" "~"')
    a('\t\t(at 0 0 0)')
    a('\t\t(layer "F.Fab")')
    a("\t\t(hide yes)")
    a("\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a("\t)")
    a("\t(attr through_hole)")
    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
        a("\t(fp_rect")
        a(f"\t\t(start {x0} {y0})")
        a(f"\t\t(end {x1} {y1})")
        a(f"\t\t(stroke (width {w}) (type solid))")
        a("\t\t(fill none)")
        a(f'\t\t(layer "{layer}")')
        a("\t)")
    for i, label in enumerate(pin_names):
        y = i * pitch
        a(f'\t(fp_text user "{label}"')
        a(f"\t\t(at {x1 + 2.0} {y} 0)")
        a('\t\t(layer "F.SilkS")')
        a('\t\t(effects (font (size 0.8 0.8) (thickness 0.12)) (justify left))')
        a("\t)")
        shape = "rect" if i == 0 else "circle"
        a(f'\t(pad "{i + 1}" thru_hole {shape}')
        a(f"\t\t(at 0 {y})")
        a("\t\t(size 1.7 1.7)")
        a("\t\t(drill 1.0)")
        a('\t\t(layers "*.Cu" "*.Mask")')
        a("\t\t(remove_unused_layers no)")
        a("\t)")
    a(")")
    out = PRETTY / f"{name}.kicad_mod"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def write_tmc2209_footprint() -> Path:
    """THT landing for BTT-style TMC2209 stepstick (verify on Shopee module)."""
    # Control column x=-row/2: EN..DIR ; Power column x=+row/2: VM..GND
    ctrl = [
        ("1", "EN"),
        ("2", "MS1"),
        ("3", "MS2"),
        ("4", "PDN"),
        ("5", "PDN2"),
        ("6", "CLK"),
        ("7", "STEP"),
        ("8", "DIR"),
    ]
    pwr = [
        ("9", "VM"),
        ("10", "GND"),
        ("11", "A2"),
        ("12", "A1"),
        ("13", "B1"),
        ("14", "B2"),
        ("15", "VIO"),
        ("16", "GND2"),
    ]
    hx = TMC_ROW / 2
    y0 = -3.5 * PITCH
    lines: list[str] = []
    a = lines.append
    a('(footprint "TMC2209_StepStick"')
    a("\t(version 20260206)")
    a('\t(generator "gen_power_carrier.py")')
    a('\t(generator_version "1.0")')
    a('\t(layer "F.Cu")')
    a(
        '\t(descr "TMC2209 stepstick ~15.24x20.32mm (BTT pinout). '
        'Verify Shopee thegioimodule before fab.")'
    )
    a('\t(tags "TMC2209 stepper driver module NEMA17")')
    a('\t(property "Reference" "U**"')
    a(f'\t\t(at 0 {-TMC_H / 2 - 1.8} 0)')
    a('\t\t(layer "F.SilkS")')
    a("\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a("\t)")
    a('\t(property "Value" "TMC2209_StepStick"')
    a(f'\t\t(at 0 {TMC_H / 2 + 1.8} 0)')
    a('\t\t(layer "F.Fab")')
    a("\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a("\t)")
    a("\t(attr through_hole)")
    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
        a("\t(fp_rect")
        a(f"\t\t(start {-TMC_W / 2} {-TMC_H / 2})")
        a(f"\t\t(end {TMC_W / 2} {TMC_H / 2})")
        a(f"\t\t(stroke (width {w}) (type solid))")
        a("\t\t(fill none)")
        a(f'\t\t(layer "{layer}")')
        a("\t)")
    a('\t(fp_text user "CTRL"')
    a(f"\t\t(at {-hx - 3.5} 0 90)")
    a('\t\t(layer "F.SilkS")')
    a('\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))')
    a("\t)")
    a('\t(fp_text user "PWR"')
    a(f"\t\t(at {hx + 3.5} 0 90)")
    a('\t\t(layer "F.SilkS")')
    a('\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))')
    a("\t)")
    for i, (num, name) in enumerate(ctrl):
        y = y0 + i * PITCH
        a(f'\t(fp_text user "{name}"')
        a(f"\t\t(at {-hx - 2.8} {y} 0)")
        a('\t\t(layer "F.SilkS")')
        a('\t\t(effects (font (size 0.7 0.7) (thickness 0.1)) (justify right))')
        a("\t)")
        shape = "rect" if i == 0 else "circle"
        a(f'\t(pad "{num}" thru_hole {shape}')
        a(f"\t\t(at {-hx} {y})")
        a("\t\t(size 1.7 1.7)")
        a("\t\t(drill 1.0)")
        a('\t\t(layers "*.Cu" "*.Mask")')
        a("\t)")
    for i, (num, name) in enumerate(pwr):
        y = y0 + i * PITCH
        a(f'\t(fp_text user "{name}"')
        a(f"\t\t(at {hx + 2.8} {y} 0)")
        a('\t\t(layer "F.SilkS")')
        a('\t\t(effects (font (size 0.7 0.7) (thickness 0.1)) (justify left))')
        a("\t)")
        a(f'\t(pad "{num}" thru_hole circle')
        a(f"\t\t(at {hx} {y})")
        a("\t\t(size 1.7 1.7)")
        a("\t\t(drill 1.0)")
        a('\t\t(layers "*.Cu" "*.Mask")')
        a("\t)")
    a(")")
    out = PRETTY / "TMC2209_StepStick.kicad_mod"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def uid() -> str:
    return str(uuid.uuid4())



def write_pc817_4ch_footprint() -> Path:
    """THT landing for PC817 4-channel module (~48x38mm, dual 1x6)."""
    hx = PC817_4CH_ROW / 2
    xs = [(i - 2.5) * PITCH for i in range(6)]
    in_names = ["GND_I", "VCC_I", "IN1", "IN2", "IN3", "IN4"]
    out_names = ["GND_O", "VCC_O", "OUT1", "OUT2", "OUT3", "OUT4"]
    lines: list[str] = []
    a = lines.append
    a('(footprint "PC817_4CH_Opto"')
    a("\t(version 20260206)")
    a('\t(generator "gen_power_carrier.py")')
    a('\t(generator_version "1.0")')
    a('\t(layer "F.Cu")')
    a(
        '\t(descr "PC817 4-channel opto isolation ~48x38mm (NOYITO-style). '
        'VERIFY pad pitch/row on real module before fab.")'
    )
    a('\t(tags "PC817 optocoupler 4ch isolation")')
    a('\t(property "Reference" "U**"')
    a(f'\t\t(at 0 {-PC817_4CH_H / 2 - 1.8} 0)')
    a('\t\t(layer "F.SilkS")')
    a("\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a("\t)")
    a('\t(property "Value" "PC817_4CH_Opto"')
    a(f'\t\t(at 0 {PC817_4CH_H / 2 + 1.8} 0)')
    a('\t\t(layer "F.Fab")')
    a("\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a("\t)")
    a("\t(attr through_hole)")
    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
        a("\t(fp_rect")
        a(f"\t\t(start {-PC817_4CH_W / 2} {-PC817_4CH_H / 2})")
        a(f"\t\t(end {PC817_4CH_W / 2} {PC817_4CH_H / 2})")
        a(f"\t\t(stroke (width {w}) (type solid))")
        a("\t\t(fill none)")
        a(f'\t\t(layer "{layer}")')
        a("\t)")
    a('\t(fp_text user "IN FIELD"')
    a(f"\t\t(at 0 {-hx - 3.2} 0)")
    a('\t\t(layer "F.SilkS")')
    a('\t\t(effects (font (size 0.75 0.75) (thickness 0.1)))')
    a("\t)")
    a('\t(fp_text user "OUT MCU"')
    a(f"\t\t(at 0 {hx + 3.2} 0)")
    a('\t\t(layer "F.SilkS")')
    a('\t\t(effects (font (size 0.75 0.75) (thickness 0.1)))')
    a("\t)")
    for i, name in enumerate(in_names):
        num = str(i + 1)
        x = xs[i]
        a(f'\t(fp_text user "{name}"')
        a(f"\t\t(at {x} {-hx - 2.2} 0)")
        a('\t\t(layer "F.SilkS")')
        a('\t\t(effects (font (size 0.55 0.55) (thickness 0.08)))')
        a("\t)")
        shape = "rect" if i == 0 else "circle"
        a(f'\t(pad "{num}" thru_hole {shape}')
        a(f"\t\t(at {x} {-hx})")
        a("\t\t(size 1.7 1.7)")
        a("\t\t(drill 1.0)")
        a('\t\t(layers "*.Cu" "*.Mask")')
        a("\t)")
    for i, name in enumerate(out_names):
        num = str(i + 7)
        x = xs[i]
        a(f'\t(fp_text user "{name}"')
        a(f"\t\t(at {x} {hx + 2.2} 0)")
        a('\t\t(layer "F.SilkS")')
        a('\t\t(effects (font (size 0.55 0.55) (thickness 0.08)))')
        a("\t)")
        a(f'\t(pad "{num}" thru_hole circle')
        a(f"\t\t(at {x} {hx})")
        a("\t\t(size 1.7 1.7)")
        a("\t\t(drill 1.0)")
        a('\t\t(layers "*.Cu" "*.Mask")')
        a("\t)")
    a(")")
    out = PRETTY / "PC817_4CH_Opto.kicad_mod"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def write_pc817_8ch_footprint() -> Path:
    """Deprecated: kept for lib compatibility; layout uses 2x 4CH."""
    return write_pc817_4ch_footprint()




def write_r_axial_4k7_bup() -> Path:
    """THT axial resistor ~7.5 mm pad pitch for BUP NPN pull-up."""
    lines: list[str] = []
    a = lines.append
    a('(footprint "R_Axial_4k7_BUP"')
    a("\t(version 20260206)")
    a('\t(generator "gen_power_carrier.py")')
    a('\t(generator_version "1.0")')
    a('\t(layer "F.Cu")')
    a('\t(descr "Axial 4k7 pull-up for BUP-30S NPN -> opto")')
    a('\t(tags "resistor axial")')
    a('\t(property "Reference" "R**"')
    a('\t\t(at 0 -2.5 0)')
    a('\t\t(layer "F.SilkS")')
    a("\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))")
    a("\t)")
    a('\t(property "Value" "4k7"')
    a('\t\t(at 0 2.5 0)')
    a('\t\t(layer "F.Fab")')
    a("\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))")
    a("\t)")
    a("\t(attr through_hole)")
    a("\t(fp_line (start -2.5 0) (end 2.5 0) (stroke (width 0.12) (type solid)) (layer \"F.SilkS\"))")
    a('\t(pad "1" thru_hole circle (at -3.75 0) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))')
    a('\t(pad "2" thru_hole circle (at 3.75 0) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))')
    a(")")
    out = PRETTY / "R_Axial_4k7_BUP.kicad_mod"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out



def write_star_power_passives() -> list:
    """Bulk 470u, SNS 47u, 100nF 0805, 10R 1206."""
    outs = []

    def _radial(name: str, d: float, pitch: float, descr: str):
        r = d / 2
        lines = [
            f'(footprint "{name}"',
            "	(version 20260206)",
            '	(generator "gen_power_carrier.py")',
            '	(layer "F.Cu")',
            f'	(descr "{descr}")',
            f'	(property "Reference" "C**" (at 0 {-r - 1.5} 0)',
            '		(layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))',
            f'	(property "Value" "{name}" (at 0 {r + 1.5} 0)',
            '		(layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))',
            "	(attr through_hole)",
            f'	(fp_circle (center 0 0) (end {r} 0) (stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))',
            f'	(pad "1" thru_hole rect (at {-pitch / 2} 0) (size 1.8 1.8) (drill 0.9) (layers "*.Cu" "*.Mask"))',
            f'	(pad "2" thru_hole circle (at {pitch / 2} 0) (size 1.8 1.8) (drill 0.9) (layers "*.Cu" "*.Mask"))',
            ")",
        ]
        out = PRETTY / f"{name}.kicad_mod"
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return out

    outs.append(_radial("CP_Radial_D8_470u_25V", 8.0, 3.5, "470uF 25V bulk near motor driver"))
    outs.append(_radial("CP_Radial_D6_47u_25V", 6.3, 2.5, "47uF 25V SNS rail"))

    c0805 = (
        '(footprint "C_0805_100n"\n'
        "\t(version 20260206)\n"
        '\t(generator "gen_power_carrier.py")\n'
        '\t(layer "F.Cu")\n'
        '\t(descr "100nF 0805")\n'
        '\t(property "Reference" "C**" (at 0 -1.8 0) (layer "F.SilkS") '
        "(effects (font (size 0.7 0.7) (thickness 0.1))))\n"
        '\t(property "Value" "100n" (at 0 1.8 0) (layer "F.Fab") '
        "(effects (font (size 0.7 0.7) (thickness 0.1))))\n"
        "\t(attr smd)\n"
        '\t(fp_rect (start -1.1 -0.7) (end 1.1 0.7) (stroke (width 0.1) (type solid)) '
        '(fill none) (layer "F.CrtYd"))\n'
        '\t(pad "1" smd roundrect (at -0.95 0) (size 0.8 1.2) '
        '(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))\n'
        '\t(pad "2" smd roundrect (at 0.95 0) (size 0.8 1.2) '
        '(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))\n'
        ")\n"
    )
    p = PRETTY / "C_0805_100n.kicad_mod"
    p.write_text(c0805, encoding="utf-8")
    outs.append(p)

    r1206 = (
        '(footprint "R_1206_10R"\n'
        "\t(version 20260206)\n"
        '\t(generator "gen_power_carrier.py")\n'
        '\t(layer "F.Cu")\n'
        '\t(descr "10 ohm 1206 SNS series filter")\n'
        '\t(property "Reference" "R**" (at 0 -1.8 0) (layer "F.SilkS") '
        "(effects (font (size 0.7 0.7) (thickness 0.1))))\n"
        '\t(property "Value" "10R" (at 0 1.8 0) (layer "F.Fab") '
        "(effects (font (size 0.7 0.7) (thickness 0.1))))\n"
        "\t(attr smd)\n"
        '\t(fp_rect (start -1.7 -0.9) (end 1.7 0.9) (stroke (width 0.1) (type solid)) '
        '(fill none) (layer "F.CrtYd"))\n'
        '\t(pad "1" smd roundrect (at -1.4 0) (size 1.0 1.5) '
        '(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))\n'
        '\t(pad "2" smd roundrect (at 1.4 0) (size 1.0 1.5) '
        '(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))\n'
        ")\n"
    )
    p = PRETTY / "R_1206_10R.kicad_mod"
    p.write_text(r1206, encoding="utf-8")
    outs.append(p)
    return outs


def write_l298n_footprint() -> Path:
    """THT landing for DRV8871 breakout (GA12-N20). VERIFY pitch on real module."""
    pads = [
        ("1", "VM", -8.0, -8.0),
        ("2", "GND", 0.0, -8.0),
        ("3", "IN1", -10.0, 0.0),
        ("4", "IN2", -10.0, 6.0),
        ("5", "OUT1", 10.0, -4.0),
        ("6", "OUT2", 10.0, 4.0),
    ]
    lines: list[str] = []
    a = lines.append
    a('(footprint "DRV8871_Module"')
    a("\t(version 20260206)")
    a('\t(generator "gen_power_carrier.py")')
    a('\t(generator_version "2.0")')
    a('\t(layer "F.Cu")')
    a('\t(descr "DRV8871 DC motor driver ~28x20mm for GA12-N20. VERIFY before fab.")')
    a('\t(tags "DRV8871 DC motor driver")')
    a('\t(property "Reference" "U**"')
    a(f"\t\t(at 0 {-DRV_H / 2 - 1.8} 0)")
    a('\t\t(layer "F.SilkS")')
    a("\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a("\t)")
    a('\t(property "Value" "DRV8871_Module"')
    a(f"\t\t(at 0 {DRV_H / 2 + 1.8} 0)")
    a('\t\t(layer "F.Fab")')
    a("\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a("\t)")
    a("\t(attr through_hole)")
    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
        a("\t(fp_rect")
        a(f"\t\t(start {-DRV_W / 2} {-DRV_H / 2})")
        a(f"\t\t(end {DRV_W / 2} {DRV_H / 2})")
        a(f"\t\t(stroke (width {w}) (type solid))")
        a("\t\t(fill none)")
        a(f'\t\t(layer "{layer}")')
        a("\t)")
    a('\t(fp_text user "DRV8871"')
    a("\t\t(at 0 0 0)")
    a('\t\t(layer "F.SilkS")')
    a('\t\t(effects (font (size 1.0 1.0) (thickness 0.15)))')
    a("\t)")
    for i, (num, name, x, y) in enumerate(pads):
        a(f'\t(fp_text user "{name}"')
        a(f"\t\t(at {x} {y - 2.0} 0)")
        a('\t\t(layer "F.SilkS")')
        a('\t\t(effects (font (size 0.65 0.65) (thickness 0.1)))')
        a("\t)")
        shape = "rect" if i == 0 else "circle"
        a(f'\t(pad "{num}" thru_hole {shape}')
        a(f"\t\t(at {x} {y})")
        a("\t\t(size 1.8 1.8)")
        a("\t\t(drill 1.0)")
        a('\t\t(layers "*.Cu" "*.Mask")')
        a("\t)")
    a(")")
    out = PRETTY / "DRV8871_Module.kicad_mod"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out



def write_mini560_footprint() -> Path:
    """THT landing for MP1584EN mini buck (Shopee G178). VERIFY pad pitch."""
    hx = MP1584_PAD_SPAN_X / 2
    hy = MP1584_PAD_SPAN_Y / 2
    # body outline centered; pads: 1=VIN+, 2=VIN-, 3=VOUT+, 4=VOUT-
    pads = [
        ("1", "VIN+", -hx, -hy),
        ("2", "VIN-", -hx, hy),
        ("3", "VOUT+", hx, -hy),
        ("4", "VOUT-", hx, hy),
    ]
    x0, x1 = -MP1584_W / 2, MP1584_W / 2
    y0, y1 = -MP1584_H / 2, MP1584_H / 2

    lines: list[str] = []
    a = lines.append
    a('(footprint "MP1584_5V3A"')
    a("\t(version 20260206)")
    a('\t(generator "gen_power_carrier.py")')
    a('\t(generator_version "2.1")')
    a('\t(layer "F.Cu")')
    a(
        '\t(descr "MP1584EN mini buck ~22x17mm (Shopee G178). Prefer fixed 5V. '
        'Verify pad pitch before fab.")'
    )
    a('\t(tags "MP1584EN buck DC-DC 5V module carrier")')
    a('\t(property "Reference" "U**"')
    a(f'\t\t(at 0 {y0 - 1.8} 0)')
    a('\t\t(layer "F.SilkS")')
    a("\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a("\t)")
    a('\t(property "Value" "MP1584_5V3A"')
    a(f'\t\t(at 0 {y1 + 1.8} 0)')
    a('\t\t(layer "F.Fab")')
    a("\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a("\t)")
    a('\t(property "Datasheet" "https://www.monolithicpower.com/en/mp1584.html"')
    a('\t\t(at 0 0 0)')
    a('\t\t(layer "F.Fab")')
    a("\t\t(hide yes)")
    a("\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a("\t)")
    a('\t(property "Description" "MP1584EN 12V to 5V buck mini module"')
    a('\t\t(at 0 0 0)')
    a('\t\t(layer "F.Fab")')
    a("\t\t(hide yes)")
    a("\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a("\t)")
    a("\t(attr through_hole)")

    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
        a("\t(fp_rect")
        a(f"\t\t(start {x0} {y0})")
        a(f"\t\t(end {x1} {y1})")
        a(f"\t\t(stroke (width {w}) (type solid))")
        a("\t\t(fill none)")
        a(f'\t\t(layer "{layer}")')
        a("\t)")

    a('\t(fp_text user "IN"')
    a(f"\t\t(at {-hx - 2.8} 0 0)")
    a('\t\t(layer "F.SilkS")')
    a('\t\t(effects (font (size 0.7 0.7) (thickness 0.1)) (justify right))')
    a("\t)")
    a('\t(fp_text user "OUT5V"')
    a(f"\t\t(at {hx + 2.8} 0 0)")
    a('\t\t(layer "F.SilkS")')
    a('\t\t(effects (font (size 0.7 0.7) (thickness 0.1)) (justify left))')
    a("\t)")
    a('\t(fp_text user "MP1584"')
    a("\t\t(at 0 0 0)")
    a('\t\t(layer "F.SilkS")')
    a('\t\t(effects (font (size 0.9 0.9) (thickness 0.12)))')
    a("\t)")

    for num, name, x, y in pads:
        a(f'\t(fp_text user "{name}"')
        a(f"\t\t(at {x} {y - 2.2} 0)")
        a('\t\t(layer "F.SilkS")')
        a('\t\t(effects (font (size 0.65 0.65) (thickness 0.1)))')
        a("\t)")
        shape = "rect" if num == "1" else "circle"
        a(f'\t(pad "{num}" thru_hole {shape}')
        a(f"\t\t(at {x} {y})")
        a("\t\t(size 1.8 1.8)")
        a("\t\t(drill 1.0)")
        a('\t\t(layers "*.Cu" "*.Mask")')
        a("\t\t(remove_unused_layers no)")
        a("\t)")

    a(")")
    out = PRETTY / "MP1584_5V3A.kicad_mod"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def write_screw_terminal_footprint() -> Path:
    """2-pin screw terminal block, pitch 5.0 mm (KF301-5.0-2P style)."""
    # Body approx 10 x 7.5 mm, pads at Â±2.5
    bw, bh = 10.2, 8.0
    lines: list[str] = []
    a = lines.append
    a('(footprint "TerminalBlock_2P_5.0mm"')
    a("\t(version 20260206)")
    a('\t(generator "gen_power_carrier.py")')
    a('\t(generator_version "1.0")')
    a('\t(layer "F.Cu")')
    a('\t(descr "2-pin screw terminal pitch 5.0mm for 12V PSU wires")')
    a('\t(tags "screw terminal KF301 5.0mm 2P")')
    a('\t(property "Reference" "J**"')
    a('\t\t(at 0 -5.5 0)')
    a('\t\t(layer "F.SilkS")')
    a("\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a("\t)")
    a('\t(property "Value" "TerminalBlock_2P_5.0mm"')
    a('\t\t(at 0 6.2 0)')
    a('\t\t(layer "F.Fab")')
    a("\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a("\t)")
    a('\t(property "Datasheet" "~"')
    a('\t\t(at 0 0 0)')
    a('\t\t(layer "F.Fab")')
    a("\t\t(hide yes)")
    a("\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a("\t)")
    a('\t(property "Description" "Screw terminal 2P 5.0mm 12V input"')
    a('\t\t(at 0 0 0)')
    a('\t\t(layer "F.Fab")')
    a("\t\t(hide yes)")
    a("\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a("\t)")
    a("\t(attr through_hole)")

    x0, x1 = -bw / 2, bw / 2
    y0, y1 = -bh / 2, bh / 2
    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
        a("\t(fp_rect")
        a(f"\t\t(start {x0} {y0})")
        a(f"\t\t(end {x1} {y1})")
        a(f"\t\t(stroke (width {w}) (type solid))")
        a("\t\t(fill none)")
        a(f'\t\t(layer "{layer}")')
        a("\t)")

    # Wire-entry side marker (front of terminal)
    a("\t(fp_line")
    a(f"\t\t(start {x0} {y1})")
    a(f"\t\t(end {x1} {y1})")
    a("\t\t(stroke (width 0.25) (type solid))")
    a('\t\t(layer "F.SilkS")')
    a("\t)")
    a('\t(fp_text user "+12V"')
    a(f"\t\t(at {-TB_PITCH / 2} {y0 - 1.6} 0)")
    a('\t\t(layer "F.SilkS")')
    a('\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))')
    a("\t)")
    a('\t(fp_text user "GND"')
    a(f"\t\t(at {TB_PITCH / 2} {y0 - 1.6} 0)")
    a('\t\t(layer "F.SilkS")')
    a('\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))')
    a("\t)")

    a('\t(pad "1" thru_hole rect')
    a(f"\t\t(at {-TB_PITCH / 2} 0)")
    a("\t\t(size 2.8 2.8)")
    a("\t\t(drill 1.5)")
    a('\t\t(layers "*.Cu" "*.Mask")')
    a("\t\t(remove_unused_layers no)")
    a("\t)")
    a('\t(pad "2" thru_hole circle')
    a(f"\t\t(at {TB_PITCH / 2} 0)")
    a("\t\t(size 2.8 2.8)")
    a("\t\t(drill 1.5)")
    a('\t\t(layers "*.Cu" "*.Mask")')
    a("\t\t(remove_unused_layers no)")
    a("\t)")
    a(")")
    out = PRETTY / "TerminalBlock_2P_5.0mm.kicad_mod"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def write_ptc_fuse_footprint() -> Path:
    """THT radial PTC ~pitch 5.1 mm (RXE030 / MF-R300 class, ~3A hold)."""
    lines: list[str] = []
    a = lines.append
    a('(footprint "Fuse_PTC_Radial_5.1mm"')
    a("\t(version 20240108)")
    a('\t(generator "gen_power_carrier.py")')
    a('\t(layer "F.Cu")')
    a(
        '\t(descr "Radial PTC resettable fuse lead pitch 5.1mm '
        '(e.g. RXE030 / 30V 3A hold). Cheap input protection.")'
    )
    a('\t(tags "PTC fuse resettable")')
    a('\t(property "Reference" "F"')
    a("\t\t(at 0 -4.5 0)")
    a('\t\t(layer "F.SilkS")')
    a("\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a("\t)")
    a('\t(property "Value" "PTC_3A"')
    a("\t\t(at 0 4.5 0)")
    a('\t\t(layer "F.Fab")')
    a("\t\t(effects (font (size 0.8 0.8) (thickness 0.1)))")
    a("\t)")
    a("\t(attr through_hole)")
    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
        a("\t(fp_circle")
        a("\t\t(center 0 0)")
        a("\t\t(end 0 -4.5)")
        a(f'\t\t(stroke (width {w}) (type solid))')
        a("\t\t(fill none)")
        a(f'\t\t(layer "{layer}")')
        a("\t)")
    a('\t(pad "1" thru_hole rect (at -2.55 0) (size 1.8 1.8) (drill 1.0)')
    a('\t\t(layers "*.Cu" "*.Mask"))')
    a('\t(pad "2" thru_hole circle (at 2.55 0) (size 1.8 1.8) (drill 1.0)')
    a('\t\t(layers "*.Cu" "*.Mask"))')
    a(")")
    out = PRETTY / "Fuse_PTC_Radial_5.1mm.kicad_mod"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def write_tvs_do41_footprint() -> Path:
    """THT axial TVS DO-41 / DO-15 (P6KE15A / 1.5KE18CA class)."""
    lines: list[str] = []
    a = lines.append
    a('(footprint "Diode_TVS_DO41"')
    a("\t(version 20240108)")
    a('\t(generator "gen_power_carrier.py")')
    a('\t(layer "F.Cu")')
    a(
        '\t(descr "Axial TVS DO-41 ~7.5mm pitch. Use P6KE15A or SMB equiv for 12V bus.")'
    )
    a('\t(tags "TVS diode surge")')
    a('\t(property "Reference" "D"')
    a("\t\t(at 0 -2.8 0)")
    a('\t\t(layer "F.SilkS")')
    a("\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a("\t)")
    a('\t(property "Value" "P6KE15A"')
    a("\t\t(at 0 2.8 0)")
    a('\t\t(layer "F.Fab")')
    a("\t\t(effects (font (size 0.8 0.8) (thickness 0.1)))")
    a("\t)")
    a("\t(attr through_hole)")
    a(
        '\t(fp_line (start -3.0 0) (end 3.0 0) '
        '(stroke (width 0.12) (type solid)) (layer "F.SilkS"))'
    )
    a(
        '\t(fp_line (start 2.2 -1.2) (end 2.2 1.2) '
        '(stroke (width 0.12) (type solid)) (layer "F.SilkS"))'
    )
    a('\t(pad "1" thru_hole rect (at -3.75 0) (size 1.7 1.7) (drill 0.9)')
    a('\t\t(layers "*.Cu" "*.Mask"))')
    a('\t(pad "2" thru_hole circle (at 3.75 0) (size 1.7 1.7) (drill 0.9)')
    a('\t\t(layers "*.Cu" "*.Mask"))')
    a(")")
    out = PRETTY / "Diode_TVS_DO41.kicad_mod"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def write_esp32_footprint() -> Path:
    """ESP32-S3-DevKitC-1 female socket (2x22)."""
    y_last = (S3_PINS_PER_SIDE - 1) * PITCH
    x0, x1 = -1.8, ROW_SPACING + 1.8
    y0, y1 = -8.0, y_last + 3.0
    lines: list[str] = []
    a = lines.append
    a('(footprint "ESP32_S3_DevKitC_44Pin_Socket"')
    a("\t(version 20260206)")
    a('\t(generator "gen_power_carrier.py")')
    a('\t(generator_version "1.0")')
    a('\t(layer "F.Cu")')
    a('\t(descr "Female header socket for ESP32-S3-DevKitC-1 44-pin")')
    a('\t(tags "ESP32 DevKit socket 44-pin")')
    a('\t(property "Reference" "U**"')
    a('\t\t(at 12.7 -10.5 0)')
    a('\t\t(layer "F.SilkS")')
    a("\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a("\t)")
    a('\t(property "Value" "ESP32_S3_DevKitC_44Pin_Socket"')
    a(f'\t\t(at 12.7 {y_last + 5.0} 0)')
    a('\t\t(layer "F.Fab")')
    a("\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a("\t)")
    a('\t(property "Datasheet" "~"')
    a('\t\t(at 0 0 0)')
    a('\t\t(layer "F.Fab")')
    a("\t\t(hide yes)")
    a("\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a("\t)")
    a('\t(property "Description" "ESP32-S3-DevKitC-1 44-pin socket"')
    a('\t\t(at 0 0 0)')
    a('\t\t(layer "F.Fab")')
    a("\t\t(hide yes)")
    a("\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a("\t)")
    a("\t(attr through_hole)")
    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
        a("\t(fp_rect")
        a(f"\t\t(start {x0} {y0})")
        a(f"\t\t(end {x1} {y1})")
        a(f"\t\t(stroke (width {w}) (type solid))")
        a("\t\t(fill none)")
        a(f'\t\t(layer "{layer}")')
        a("\t)")
    a('\t(fp_text user "USB"')
    a(f"\t\t(at {ROW_SPACING / 2} {y0 + 2.5} 0)")
    a('\t\t(layer "F.SilkS")')
    a('\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))')
    a("\t)")
    for num, name, _ in LEFT_PINS:
        y = (num - 1) * PITCH
        a(f'\t(fp_text user "{name}"')
        a(f"\t\t(at -3.2 {y} 0)")
        a('\t\t(layer "F.SilkS")')
        a('\t\t(effects (font (size 0.8 0.8) (thickness 0.12)) (justify right))')
        a("\t)")
        shape = "rect" if num == 1 else "circle"
        a(f'\t(pad "{num}" thru_hole {shape}')
        a(f"\t\t(at 0 {y})")
        a(f"\t\t(size {PAD_SIZE} {PAD_SIZE})")
        a(f"\t\t(drill {PAD_DRILL})")
        a('\t\t(layers "*.Cu" "*.Mask")')
        a("\t\t(remove_unused_layers no)")
        a("\t)")
    for num, name, _ in RIGHT_PINS:
        y = (num - 23) * PITCH
        a(f'\t(fp_text user "{name}"')
        a(f"\t\t(at {ROW_SPACING + 3.2} {y} 0)")
        a('\t\t(layer "F.SilkS")')
        a('\t\t(effects (font (size 0.8 0.8) (thickness 0.12)) (justify left))')
        a("\t)")
        a(f'\t(pad "{num}" thru_hole circle')
        a(f"\t\t(at {ROW_SPACING} {y})")
        a(f"\t\t(size {PAD_SIZE} {PAD_SIZE})")
        a(f"\t\t(drill {PAD_DRILL})")
        a('\t\t(layers "*.Cu" "*.Mask")')
        a("\t\t(remove_unused_layers no)")
        a("\t)")
    a(")")
    out = PRETTY / "ESP32_S3_DevKitC_44Pin_Socket.kicad_mod"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def _sym_prop(name: str, value: str, hide: bool = False) -> list[str]:
    lines = [
        f'\t\t(property "{name}" "{value}"',
        "\t\t\t(at 0 0 0)",
    ]
    if hide:
        lines.append("\t\t\t(hide yes)")
    lines.append("\t\t\t(effects (font (size 1.27 1.27)))")
    lines.append("\t\t)")
    return lines


def write_symbol_lib() -> Path:
    pin_ys = [26.67 - i * 2.54 for i in range(S3_PINS_PER_SIDE)]
    body_x = 12.7
    body_top = pin_ys[0] + 2.54
    body_bot = pin_ys[-1] - 2.54

    lines: list[str] = []
    a = lines.append
    a("(kicad_symbol_lib")
    a("\t(version 20251024)")
    a('\t(generator "gen_power_carrier.py")')
    a('\t(generator_version "1.0")')

    # --- ESP32 ---
    a('\t(symbol "ESP32_S3_DevKitC_1"')
    a("\t\t(exclude_from_sim no)")
    a("\t\t(in_bom yes)")
    a("\t\t(on_board yes)")
    a("\t\t(in_pos_files yes)")
    a('\t\t(property "Reference" "U"')
    a(f"\t\t\t(at 0 {body_top + 2.54} 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Value" "ESP32_S3_DevKitC_1"')
    a(f"\t\t\t(at 0 {body_bot - 2.54} 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Footprint" "ESP32_Carrier:ESP32_S3_DevKitC_44Pin_Socket"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Datasheet" "~"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Description" "ESP32-S3-DevKitC-1 44-pin socket"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(symbol "ESP32_S3_DevKitC_1_0_1"')
    a("\t\t\t(rectangle")
    a(f"\t\t\t\t(start {-body_x} {body_top})")
    a(f"\t\t\t\t(end {body_x} {body_bot})")
    a("\t\t\t\t(stroke (width 0.254) (type default))")
    a("\t\t\t\t(fill (type background))")
    a("\t\t\t)")
    a("\t\t)")
    a('\t\t(symbol "ESP32_S3_DevKitC_1_1_1"')
    for (num, name, etype), y in zip(LEFT_PINS, pin_ys):
        a(f"\t\t\t(pin {etype} line")
        a(f"\t\t\t\t(at {-body_x - 5.08} {y} 0)")
        a("\t\t\t\t(length 5.08)")
        a(f'\t\t\t\t(name "{name}" (effects (font (size 1.27 1.27))))')
        a(f'\t\t\t\t(number "{num}" (effects (font (size 1.27 1.27))))')
        a("\t\t\t)")
    for (num, name, etype), y in zip(RIGHT_PINS, pin_ys):
        a(f"\t\t\t(pin {etype} line")
        a(f"\t\t\t\t(at {body_x + 5.08} {y} 180)")
        a("\t\t\t\t(length 5.08)")
        a(f'\t\t\t\t(name "{name}" (effects (font (size 1.27 1.27))))')
        a(f'\t\t\t\t(number "{num}" (effects (font (size 1.27 1.27))))')
        a("\t\t\t)")
    a("\t\t)")
    a("\t)")

    # --- MP1584EN ---
    a('\t(symbol "MP1584_5V3A"')
    a("\t\t(exclude_from_sim no)")
    a("\t\t(in_bom yes)")
    a("\t\t(on_board yes)")
    a("\t\t(in_pos_files yes)")
    a('\t\t(property "Reference" "U"')
    a("\t\t\t(at 0 8.89 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Value" "MP1584_5V3A"')
    a("\t\t\t(at 0 -8.89 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Footprint" "ESP32_Carrier:MP1584_5V3A"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Datasheet" "~"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a(
        '\t\t(property "Description" '
        '"MP1584EN buck 12V to 5V (Shopee G178, prefer fixed 5V)"'
    )
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(symbol "MP1584_5V3A_0_1"')
    a("\t\t\t(rectangle")
    a("\t\t\t\t(start -7.62 6.35)")
    a("\t\t\t\t(end 7.62 -6.35)")
    a("\t\t\t\t(stroke (width 0.254) (type default))")
    a("\t\t\t\t(fill (type background))")
    a("\t\t\t)")
    a('\t\t\t(text "BUCK"')
    a("\t\t\t\t(at 0 0 0)")
    a("\t\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t\t)")
    a("\t\t)")
    a('\t\t(symbol "MP1584_5V3A_1_1"')
    for num, name, etype, x, y, rot in [
        ("1", "VIN+", "passive", -12.7, 2.54, 0),
        ("2", "VIN-", "passive", -12.7, -2.54, 0),
        ("3", "VOUT+", "power_out", 12.7, 2.54, 180),
        ("4", "VOUT-", "passive", 12.7, -2.54, 180),
    ]:
        a(f"\t\t\t(pin {etype} line")
        a(f"\t\t\t\t(at {x} {y} {rot})")
        a("\t\t\t\t(length 5.08)")
        a(f'\t\t\t\t(name "{name}" (effects (font (size 1.27 1.27))))')
        a(f'\t\t\t\t(number "{num}" (effects (font (size 1.27 1.27))))')
        a("\t\t\t)")
    a("\t\t)")
    a("\t)")

    # --- Screw terminal ---
    a('\t(symbol "TerminalBlock_2P"')
    a("\t\t(exclude_from_sim no)")
    a("\t\t(in_bom yes)")
    a("\t\t(on_board yes)")
    a("\t\t(in_pos_files yes)")
    a('\t\t(property "Reference" "J"')
    a("\t\t\t(at 0 5.08 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Value" "TerminalBlock_2P"')
    a("\t\t\t(at 0 -5.08 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Footprint" "ESP32_Carrier:TerminalBlock_2P_5.0mm"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Datasheet" "~"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Description" "Screw terminal 2P for 12V-3A PSU"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(symbol "TerminalBlock_2P_0_1"')
    a("\t\t\t(rectangle")
    a("\t\t\t\t(start -5.08 3.81)")
    a("\t\t\t\t(end 5.08 -3.81)")
    a("\t\t\t\t(stroke (width 0.254) (type default))")
    a("\t\t\t\t(fill (type background))")
    a("\t\t\t)")
    a('\t\t\t(text "SCREW"')
    a("\t\t\t\t(at 0 0 0)")
    a("\t\t\t\t(effects (font (size 1.016 1.016)))")
    a("\t\t\t)")
    a("\t\t)")
    a('\t\t(symbol "TerminalBlock_2P_1_1"')
    a("\t\t\t(pin passive line")
    a("\t\t\t\t(at -10.16 0 0)")
    a("\t\t\t\t(length 5.08)")
    a('\t\t\t\t(name "+12V" (effects (font (size 1.27 1.27))))')
    a('\t\t\t\t(number "1" (effects (font (size 1.27 1.27))))')
    a("\t\t\t)")
    a("\t\t\t(pin passive line")
    a("\t\t\t\t(at 10.16 0 180)")
    a("\t\t\t\t(length 5.08)")
    a('\t\t\t\t(name "GND" (effects (font (size 1.27 1.27))))')
    a('\t\t\t\t(number "2" (effects (font (size 1.27 1.27))))')
    a("\t\t\t)")
    a("\t\t)")
    a("\t)")

    # --- Top-side 1x4 motor header ---
    a('\t(symbol "Conn_1x04_Motor"')
    a("\t\t(exclude_from_sim no)")
    a("\t\t(in_bom yes)")
    a("\t\t(on_board yes)")
    a("\t\t(in_pos_files yes)")
    a('\t\t(property "Reference" "J"')
    a("\t\t\t(at 0 7.62 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Value" "Conn_1x04_Motor"')
    a("\t\t\t(at 0 -7.62 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Footprint" "ESP32_Carrier:PinHeader_1x04_Motor"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Description" "TOP: NEMA17 phases A2 A1 B1 B2"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(symbol "Conn_1x04_Motor_0_1"')
    a("\t\t\t(rectangle")
    a("\t\t\t\t(start -2.54 5.08)")
    a("\t\t\t\t(end 2.54 -5.08)")
    a("\t\t\t\t(stroke (width 0.254) (type default))")
    a("\t\t\t\t(fill (type background))")
    a("\t\t\t)")
    a('\t\t\t(text "NEMA17"')
    a("\t\t\t\t(at 0 0 0)")
    a("\t\t\t\t(effects (font (size 1.016 1.016)))")
    a("\t\t\t)")
    a("\t\t)")
    a('\t\t(symbol "Conn_1x04_Motor_1_1"')
    for num, name, y in [
        ("1", "A2", 3.81),
        ("2", "A1", 1.27),
        ("3", "B1", -1.27),
        ("4", "B2", -3.81),
    ]:
        a("\t\t\t(pin passive line")
        a(f"\t\t\t\t(at 0 {y} 90)")
        a("\t\t\t\t(length 2.54)")
        a(f'\t\t\t\t(name "{name}" (effects (font (size 1.27 1.27))))')
        a(f'\t\t\t\t(number "{num}" (effects (font (size 1.27 1.27))))')
        a("\t\t\t)")
    a("\t\t)")
    a("\t)")

    # --- TMC2209 stepstick (used pins only) ---
    a('\t(symbol "TMC2209_StepStick"')
    a("\t\t(exclude_from_sim no)")
    a("\t\t(in_bom yes)")
    a("\t\t(on_board yes)")
    a("\t\t(in_pos_files yes)")
    a('\t\t(property "Reference" "U"')
    a("\t\t\t(at 0 12.7 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Value" "TMC2209_StepStick"')
    a("\t\t\t(at 0 -12.7 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Footprint" "ESP32_Carrier:TMC2209_StepStick"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Description" "TMC2209 stepper driver for NEMA17 (Shopee)"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(symbol "TMC2209_StepStick_0_1"')
    a("\t\t\t(rectangle")
    a("\t\t\t\t(start -10.16 10.16)")
    a("\t\t\t\t(end 10.16 -10.16)")
    a("\t\t\t\t(stroke (width 0.254) (type default))")
    a("\t\t\t\t(fill (type background))")
    a("\t\t\t)")
    a('\t\t\t(text "TMC2209"')
    a("\t\t\t\t(at 0 0 0)")
    a("\t\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t\t)")
    a("\t\t)")
    a('\t\t(symbol "TMC2209_StepStick_1_1"')
    for num, name, etype, x, y, rot in [
        ("9", "VM", "power_in", -15.24, 7.62, 0),
        ("10", "GND", "passive", -15.24, 5.08, 0),
        ("15", "VIO", "power_in", -15.24, 2.54, 0),
        ("1", "EN", "input", -15.24, -2.54, 0),
        ("7", "STEP", "input", -15.24, -5.08, 0),
        ("8", "DIR", "input", -15.24, -7.62, 0),
        ("11", "A2", "passive", 15.24, 5.08, 180),
        ("12", "A1", "passive", 15.24, 2.54, 180),
        ("13", "B1", "passive", 15.24, -2.54, 180),
        ("14", "B2", "passive", 15.24, -5.08, 180),
        ("16", "GND2", "passive", 15.24, -7.62, 180),
    ]:
        a(f"\t\t\t(pin {etype} line")
        a(f"\t\t\t\t(at {x} {y} {rot})")
        a("\t\t\t\t(length 5.08)")
        a(f'\t\t\t\t(name "{name}" (effects (font (size 1.27 1.27))))')
        a(f'\t\t\t\t(number "{num}" (effects (font (size 1.27 1.27))))')
        a("\t\t\t)")
    a("\t\t)")
    a("\t)")




    # --- DRV8871 ---
    a('\t(symbol "DRV8871_Module"')
    a("\t\t(exclude_from_sim no)")
    a("\t\t(in_bom yes)")
    a("\t\t(on_board yes)")
    a("\t\t(in_pos_files yes)")
    a('\t\t(property "Reference" "U"')
    a("\t\t\t(at 0 10.16 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Value" "DRV8871_Module"')
    a("\t\t\t(at 0 -10.16 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Footprint" "ESP32_Carrier:DRV8871_Module"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Description" "DRV8871 for GA12-N20 @12V"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(symbol "DRV8871_Module_0_1"')
    a("\t\t\t(rectangle")
    a("\t\t\t\t(start -10.16 7.62)")
    a("\t\t\t\t(end 10.16 -7.62)")
    a("\t\t\t\t(stroke (width 0.254) (type default))")
    a("\t\t\t\t(fill (type background))")
    a("\t\t\t)")
    a('\t\t\t(text "DRV8871"')
    a("\t\t\t\t(at 0 0 0)")
    a("\t\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t\t)")
    a("\t\t)")
    a('\t\t(symbol "DRV8871_Module_1_1"')
    for num, name, etype, x, y, rot in [
        ("1", "VM", "power_in", -15.24, 5.08, 0),
        ("2", "GND", "passive", -15.24, 2.54, 0),
        ("3", "IN1", "input", -15.24, -2.54, 0),
        ("4", "IN2", "input", -15.24, -5.08, 0),
        ("5", "OUT1", "passive", 15.24, 2.54, 180),
        ("6", "OUT2", "passive", 15.24, -2.54, 180),
    ]:
        a(f"\t\t\t(pin {etype} line")
        a(f"\t\t\t\t(at {x} {y} {rot})")
        a("\t\t\t\t(length 5.08)")
        a(f'\t\t\t\t(name "{name}" (effects (font (size 1.016 1.016))))')
        a(f'\t\t\t\t(number "{num}" (effects (font (size 1.016 1.016))))')
        a("\t\t\t)")
    a("\t\t)")
    a("\t)")


    a('\t(symbol "Conn_1x02_MotorDC"')
    a("\t\t(exclude_from_sim no)")
    a("\t\t(in_bom yes)")
    a("\t\t(on_board yes)")
    a("\t\t(in_pos_files yes)")
    a('\t\t(property "Reference" "J"')
    a("\t\t\t(at 0 5.08 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Value" "Conn_1x02_MotorDC"')
    a("\t\t\t(at 0 -5.08 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Footprint" "ESP32_Carrier:PinHeader_1x02_MotorDC"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Description" "TOP: GA12-N20 2-pin M+ M-"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(symbol "Conn_1x02_MotorDC_0_1"')
    a("\t\t\t(rectangle")
    a("\t\t\t\t(start -2.54 3.81)")
    a("\t\t\t\t(end 2.54 -3.81)")
    a("\t\t\t\t(stroke (width 0.254) (type default))")
    a("\t\t\t\t(fill (type background))")
    a("\t\t\t)")
    a('\t\t\t(text "DC"')
    a("\t\t\t\t(at 0 0 0)")
    a("\t\t\t\t(effects (font (size 1.016 1.016)))")
    a("\t\t\t)")
    a("\t\t)")
    a('\t\t(symbol "Conn_1x02_MotorDC_1_1"')
    for num, name, y in [("1", "M+", 1.27), ("2", "M-", -1.27)]:
        a("\t\t\t(pin passive line")
        a(f"\t\t\t\t(at 0 {y} 90)")
        a("\t\t\t\t(length 2.54)")
        a(f'\t\t\t\t(name "{name}" (effects (font (size 1.27 1.27))))')
        a(f'\t\t\t\t(number "{num}" (effects (font (size 1.27 1.27))))')
        a("\t\t\t)")
    a("\t\t)")
    a("\t)")

    a('\t(symbol "Conn_1x02_LimitSW"')
    a("\t\t(exclude_from_sim no)")
    a("\t\t(in_bom yes)")
    a("\t\t(on_board yes)")
    a("\t\t(in_pos_files yes)")
    a('\t\t(property "Reference" "J"')
    a("\t\t\t(at 0 5.08 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Value" "Conn_1x02_LimitSW"')
    a("\t\t\t(at 0 -5.08 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Footprint" "ESP32_Carrier:PinHeader_1x02_LimitSW"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Description" "TOP: limit SW NC @12V to opto (+12V / SW)"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(symbol "Conn_1x02_LimitSW_0_1"')
    a("\t\t\t(rectangle")
    a("\t\t\t\t(start -2.54 3.81)")
    a("\t\t\t\t(end 2.54 -3.81)")
    a("\t\t\t\t(stroke (width 0.254) (type default))")
    a("\t\t\t\t(fill (type background))")
    a("\t\t\t)")
    a('\t\t\t(text "LIM"')
    a("\t\t\t\t(at 0 0 0)")
    a("\t\t\t\t(effects (font (size 1.016 1.016)))")
    a("\t\t\t)")
    a("\t\t)")
    a('\t\t(symbol "Conn_1x02_LimitSW_1_1"')
    for num, name, y in [("1", "+12V", 1.27), ("2", "SW", -1.27)]:
        a("\t\t\t(pin passive line")
        a(f"\t\t\t\t(at 0 {y} 90)")
        a("\t\t\t\t(length 2.54)")
        a(f'\t\t\t\t(name "{name}" (effects (font (size 1.27 1.27))))')
        a(f'\t\t\t\t(number "{num}" (effects (font (size 1.27 1.27))))')
        a("\t\t\t)")
    a("\t\t)")
    a("\t)")


    a('\t(symbol "Conn_1x04_BUP30S"')
    a("\t\t(exclude_from_sim no)")
    a("\t\t(in_bom yes)")
    a("\t\t(on_board yes)")
    a("\t\t(in_pos_files yes)")
    a('\t\t(property "Reference" "J"')
    a("\t\t\t(at 0 7.62 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Value" "Conn_1x04_BUP30S"')
    a("\t\t\t(at 0 -7.62 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Footprint" "ESP32_Carrier:PinHeader_1x04_BUP30S"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Description" "TOP: Autonics BUP-30S NPN 12V -> opto IN7"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(symbol "Conn_1x04_BUP30S_0_1"')
    a("\t\t\t(rectangle")
    a("\t\t\t\t(start -2.54 5.08)")
    a("\t\t\t\t(end 2.54 -5.08)")
    a("\t\t\t\t(stroke (width 0.254) (type default))")
    a("\t\t\t\t(fill (type background))")
    a("\t\t\t)")
    a('\t\t\t(text "BUP30S"')
    a("\t\t\t\t(at 0 0 0)")
    a("\t\t\t\t(effects (font (size 0.9 0.9)))")
    a("\t\t\t)")
    a("\t\t)")
    a('\t\t(symbol "Conn_1x04_BUP30S_1_1"')
    for num, name, y in [
        ("1", "+12V", 3.81),
        ("2", "GND", 1.27),
        ("3", "OUT", -1.27),
        ("4", "CTRL", -3.81),
    ]:
        a("\t\t\t(pin passive line")
        a(f"\t\t\t\t(at 0 {y} 90)")
        a("\t\t\t\t(length 2.54)")
        a(f'\t\t\t\t(name "{name}" (effects (font (size 1.016 1.016))))')
        a(f'\t\t\t\t(number "{num}" (effects (font (size 1.016 1.016))))')
        a("\t\t\t)")
    a("\t\t)")
    a("\t)")

    a('\t(symbol "R_BUP_Pullup"')
    a("\t\t(exclude_from_sim no)")
    a("\t\t(in_bom yes)")
    a("\t\t(on_board yes)")
    a("\t\t(in_pos_files yes)")
    a('\t\t(property "Reference" "R"')
    a("\t\t\t(at 0 2.54 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Value" "4k7"')
    a("\t\t\t(at 0 -2.54 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Footprint" "ESP32_Carrier:R_Axial_4k7_BUP"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(symbol "R_BUP_Pullup_0_1"')
    a("\t\t\t(rectangle")
    a("\t\t\t\t(start -1.016 2.54)")
    a("\t\t\t\t(end 1.016 -2.54)")
    a("\t\t\t\t(stroke (width 0.254) (type default))")
    a("\t\t\t\t(fill (type none))")
    a("\t\t\t)")
    a("\t\t)")
    a('\t\t(symbol "R_BUP_Pullup_1_1"')
    a("\t\t\t(pin passive line")
    a("\t\t\t\t(at 0 3.81 270)")
    a("\t\t\t\t(length 1.27)")
    a('\t\t\t\t(name "~" (effects (font (size 1.27 1.27))))')
    a('\t\t\t\t(number "1" (effects (font (size 1.27 1.27))))')
    a("\t\t\t)")
    a("\t\t\t(pin passive line")
    a("\t\t\t\t(at 0 -3.81 90)")
    a("\t\t\t\t(length 1.27)")
    a('\t\t\t\t(name "~" (effects (font (size 1.27 1.27))))')
    a('\t\t\t\t(number "2" (effects (font (size 1.27 1.27))))')
    a("\t\t\t)")
    a("\t\t)")
    a("\t)")

    # --- PC817 4CH opto (use 2 modules: U4=ch1-4, U9=ch5-8) ---
    a('\t(symbol "PC817_4CH_Opto"')
    a("\t\t(exclude_from_sim no)")
    a("\t\t(in_bom yes)")
    a("\t\t(on_board yes)")
    a("\t\t(in_pos_files yes)")
    a('\t\t(property "Reference" "U"')
    a("\t\t\t(at 0 12.7 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Value" "PC817_4CH_Opto"')
    a("\t\t\t(at 0 -12.7 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Footprint" "ESP32_Carrier:PC817_4CH_Opto"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Description" "PC817 4ch opto isolator ~48x38 (Shopee)"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(symbol "PC817_4CH_Opto_0_1"')
    a("\t\t\t(rectangle")
    a("\t\t\t\t(start -10.16 10.16)")
    a("\t\t\t\t(end 10.16 -10.16)")
    a("\t\t\t\t(stroke (width 0.254) (type default))")
    a("\t\t\t\t(fill (type background))")
    a("\t\t\t)")
    a('\t\t\t(text "OPTO4"')
    a("\t\t\t\t(at 0 0 0)")
    a("\t\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t\t)")
    a("\t\t)")
    a('\t\t(symbol "PC817_4CH_Opto_1_1"')
    pins = [
        ("1", "GND_I", "passive", -15.24, 7.62, 0),
        ("2", "VCC_I", "passive", -15.24, 5.08, 0),
        ("3", "IN1", "passive", -15.24, 2.54, 0),
        ("4", "IN2", "passive", -15.24, 0.0, 0),
        ("5", "IN3", "passive", -15.24, -2.54, 0),
        ("6", "IN4", "passive", -15.24, -5.08, 0),
        ("7", "GND_O", "passive", 15.24, 7.62, 180),
        ("8", "VCC_O", "power_in", 15.24, 5.08, 180),
        ("9", "OUT1", "passive", 15.24, 2.54, 180),
        ("10", "OUT2", "passive", 15.24, 0.0, 180),
        ("11", "OUT3", "passive", 15.24, -2.54, 180),
        ("12", "OUT4", "passive", 15.24, -5.08, 180),
    ]
    for num, name, etype, x, y, rot in pins:
        a(f"\t\t\t(pin {etype} line")
        a(f"\t\t\t\t(at {x} {y} {rot})")
        a("\t\t\t\t(length 5.08)")
        a(f'\t\t\t\t(name "{name}" (effects (font (size 1.016 1.016))))')
        a(f'\t\t\t\t(number "{num}" (effects (font (size 1.016 1.016))))')
        a("\t\t\t)")
    a("\t\t)")
    a("\t)")

    # --- Top field header for opto IN ---
    a('\t(symbol "Conn_1x10_OptoField"')
    a("\t\t(exclude_from_sim no)")
    a("\t\t(in_bom yes)")
    a("\t\t(on_board yes)")
    a("\t\t(in_pos_files yes)")
    a('\t\t(property "Reference" "J"')
    a("\t\t\t(at 0 15.24 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Value" "Conn_1x10_OptoField"')
    a("\t\t\t(at 0 -15.24 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Footprint" "ESP32_Carrier:PinHeader_1x10_OptoField"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Description" "TOP: opto field IN1-8 + GND/VCC isolated"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(symbol "Conn_1x10_OptoField_0_1"')
    a("\t\t\t(rectangle")
    a("\t\t\t\t(start -2.54 12.7)")
    a("\t\t\t\t(end 2.54 -12.7)")
    a("\t\t\t\t(stroke (width 0.254) (type default))")
    a("\t\t\t\t(fill (type background))")
    a("\t\t\t)")
    a('\t\t\t(text "OPTO_IN"')
    a("\t\t\t\t(at 0 0 0)")
    a("\t\t\t\t(effects (font (size 1.016 1.016)))")
    a("\t\t\t)")
    a("\t\t)")
    a('\t\t(symbol "Conn_1x10_OptoField_1_1"')
    for i, (num, name) in enumerate(OPTO_FIELD_HEADER):
        y = 11.43 - i * 2.54
        a("\t\t\t(pin passive line")
        a(f"\t\t\t\t(at 0 {y} 90)")
        a("\t\t\t\t(length 2.54)")
        a(f'\t\t\t\t(name "{name}" (effects (font (size 1.016 1.016))))')
        a(f'\t\t\t\t(number "{num}" (effects (font (size 1.016 1.016))))')
        a("\t\t\t)")
    a("\t\t)")
    a("\t)")

    # --- Top-side 1x12 TFT + touch header ---
    a(f'\t(symbol "{TFT_SYM}"')
    a("\t\t(exclude_from_sim no)")
    a("\t\t(in_bom yes)")
    a("\t\t(on_board yes)")
    a("\t\t(in_pos_files yes)")
    a('\t\t(property "Reference" "J"')
    a("\t\t\t(at 0 10.16 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a(f'\t\t(property "Value" "{TFT_SYM}"')
    a("\t\t\t(at 0 -10.16 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a(f'\t\t(property "Footprint" "ESP32_Carrier:{TFT_FP}"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Description" "TFT SPI + capacitive touch I2C (J17)"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    _sym_half = (TFT_PINS - 1) * 1.27 + 1.27
    a(f'\t\t(symbol "{TFT_SYM}_0_1"')
    a("\t\t\t(rectangle")
    a(f"\t\t\t\t(start -2.54 {_sym_half})")
    a(f"\t\t\t\t(end 2.54 {-_sym_half})")
    a("\t\t\t\t(stroke (width 0.254) (type default))")
    a("\t\t\t\t(fill (type background))")
    a("\t\t\t)")
    a('\t\t\t(text "TFT+TP"')
    a("\t\t\t\t(at 0 0 0)")
    a("\t\t\t\t(effects (font (size 1.016 1.016)))")
    a("\t\t\t)")
    a("\t\t)")
    a(f'\t\t(symbol "{TFT_SYM}_1_1"')
    for (num, name), y in zip(
        TFT_HEADER,
        [(TFT_PINS - 1) * 1.27 - i * 2.54 for i in range(TFT_PINS)],
    ):
        a("\t\t\t(pin passive line")
        a(f"\t\t\t\t(at 0 {y} 90)")
        a("\t\t\t\t(length 2.54)")
        a(f'\t\t\t\t(name "{name}" (effects (font (size 1.27 1.27))))')
        a(f'\t\t\t\t(number "{num}" (effects (font (size 1.27 1.27))))')
        a("\t\t\t)")
    a("\t\t)")
    a("\t)")

    a(")")
    out = LIB / "ESP32_Carrier.kicad_sym"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out



def write_lib_tables() -> None:
    (ROOT / "fp-lib-table").write_text(
        "(fp_lib_table\n"
        "  (version 7)\n"
        '  (lib (name "ESP32_Carrier")(type "KiCad")'
        '(uri "${KIPRJMOD}/libraries/ESP32_Carrier.pretty")'
        '(options "")(descr "ESP32 carrier footprints"))\n'
        ")\n",
        encoding="utf-8",
    )
    (ROOT / "sym-lib-table").write_text(
        "(sym_lib_table\n"
        "  (version 7)\n"
        '  (lib (name "ESP32_Carrier")(type "KiCad")'
        '(uri "${KIPRJMOD}/libraries/ESP32_Carrier.kicad_sym")'
        '(options "")(descr "ESP32 carrier symbols"))\n'
        ")\n",
        encoding="utf-8",
    )


def _embed_from_lib(sym_name: str) -> str:
    """Extract symbol block and rewrite name as Lib:Name for schematic embed."""
    text = (LIB / "ESP32_Carrier.kicad_sym").read_text(encoding="utf-8")
    key = f'(symbol "{sym_name}"'
    start = text.index(key)
    # Find matching close of this symbol at depth 1 inside lib
    i = start
    depth = 0
    end = None
    while i < len(text):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
        i += 1
    assert end is not None
    block = text[start:end]
    block = block.replace(f'(symbol "{sym_name}"', f'(symbol "ESP32_Carrier:{sym_name}"', 1)
    # indent one more tab for lib_symbols
    return "\n".join("\t" + ln if ln else ln for ln in block.splitlines())


def write_schematic() -> Path:
    sch_uuid = uid()
    j1_uuid = uid()
    u2_uuid = uid()
    u1_uuid = uid()

    emb_j = _embed_from_lib("TerminalBlock_2P")
    emb_m = _embed_from_lib("MP1584_5V3A")
    emb_e = _embed_from_lib("ESP32_S3_DevKitC_1")

    # Positions (mm): left = power in, middle = buck, right = ESP32
    # J1 at (40, 50), U2 at (95, 50), U1 at (170, 70)
    lines = [
        "(kicad_sch",
        "\t(version 20250114)",
        '\t(generator "gen_power_carrier.py")',
        '\t(generator_version "1.0")',
        f'\t(uuid "{sch_uuid}")',
        '\t(paper "A4")',
        "\t(title_block",
        '\t\t(title "ESP32 Baseboard - 12V->5V MP1584EN")',
        '\t\t(comment 1 "J1 screw 12V-3A -> U2 MP1584EN -> U1 ESP32-S3 5V")',
        '\t\t(comment 2 "Ready-made modules on carrier PCB")',
        "\t)",
        "\t(lib_symbols",
        emb_j,
        emb_m,
        emb_e,
        "\t)",
        # --- J1 Terminal ---
        f'\t(symbol (lib_id "ESP32_Carrier:TerminalBlock_2P") (at 38.1 50.8 0) (unit 1)',
        f'\t\t(uuid "{j1_uuid}")',
        '\t\t(property "Reference" "J1" (at 38.1 43.18 0)',
        "\t\t\t(effects (font (size 1.27 1.27)))",
        "\t\t)",
        '\t\t(property "Value" "Screw_12V_IN" (at 38.1 58.42 0)',
        "\t\t\t(effects (font (size 1.27 1.27)))",
        "\t\t)",
        '\t\t(property "Footprint" "ESP32_Carrier:TerminalBlock_2P_5.0mm" (at 38.1 50.8 0)',
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\t\t)",
        '\t\t(property "Datasheet" "~" (at 38.1 50.8 0)',
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\t\t)",
        "\t\t(pin \"1\" (uuid \"" + uid() + "\"))",
        "\t\t(pin \"2\" (uuid \"" + uid() + "\"))",
        "\t\t(instances",
        f'\t\t\t(project "esp32_baseboard" (path "/{sch_uuid}" (reference "J1") (unit 1)))',
        "\t\t)",
        "\t)",
        # --- U2 MP1584EN ---
        f'\t(symbol (lib_id "ESP32_Carrier:MP1584_5V3A") (at 88.9 50.8 0) (unit 1)',
        f'\t\t(uuid "{u2_uuid}")',
        '\t\t(property "Reference" "U2" (at 88.9 40.64 0)',
        "\t\t\t(effects (font (size 1.27 1.27)))",
        "\t\t)",
        '\t\t(property "Value" "MP1584_5V3A" (at 88.9 60.96 0)',
        "\t\t\t(effects (font (size 1.27 1.27)))",
        "\t\t)",
        '\t\t(property "Footprint" "ESP32_Carrier:MP1584_5V3A" (at 88.9 50.8 0)',
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\t\t)",
        '\t\t(property "Datasheet" "~" (at 88.9 50.8 0)',
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\t\t)",
        "\t\t(pin \"1\" (uuid \"" + uid() + "\"))",
        "\t\t(pin \"2\" (uuid \"" + uid() + "\"))",
        "\t\t(pin \"3\" (uuid \"" + uid() + "\"))",
        "\t\t(pin \"4\" (uuid \"" + uid() + "\"))",
        "\t\t(instances",
        f'\t\t\t(project "esp32_baseboard" (path "/{sch_uuid}" (reference "U2") (unit 1)))',
        "\t\t)",
        "\t)",
        # --- U1 ESP32 ---
        f'\t(symbol (lib_id "ESP32_Carrier:ESP32_S3_DevKitC_1") (at 165.1 76.2 0) (unit 1)',
        f'\t\t(uuid "{u1_uuid}")',
        '\t\t(property "Reference" "U1" (at 165.1 50.8 0)',
        "\t\t\t(effects (font (size 1.27 1.27)))",
        "\t\t)",
        '\t\t(property "Value" "ESP32_S3_DevKitC_1" (at 165.1 101.6 0)',
        "\t\t\t(effects (font (size 1.27 1.27)))",
        "\t\t)",
        '\t\t(property "Footprint" "ESP32_Carrier:ESP32_S3_DevKitC_44Pin_Socket" (at 165.1 76.2 0)',
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\t\t)",
        '\t\t(property "Datasheet" "~" (at 165.1 76.2 0)',
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\t\t)",
    ]
    for n in range(1, 31):
        lines.append(f'\t\t(pin "{n}" (uuid "{uid()}"))')
    lines += [
        "\t\t(instances",
        f'\t\t\t(project "esp32_baseboard" (path "/{sch_uuid}" (reference "U1") (unit 1)))',
        "\t\t)",
        "\t)",
        # Labels / wires: J1.1 -> +12V -> U2.1 ; J1.2/U2.2/U2.4/U1.17 -> GND ; U2.3 -> +5V -> U1.16
        # Wire J1 pin1 (27.94, 50.8) to U2 pin1 (76.2, 53.34)
        '\t(wire (pts (xy 27.94 50.8) (xy 27.94 40.64) (xy 76.2 40.64) (xy 76.2 53.34))',
        f'\t\t(stroke (width 0) (type default)) (uuid "{uid()}"))',
        '\t(label "+12V" (at 50.8 40.64 0) (fields_autoplaced)',
        f'\t\t(effects (font (size 1.27 1.27)) (justify left bottom)) (uuid "{uid()}"))',
        # GND from J1.2
        '\t(wire (pts (xy 48.26 50.8) (xy 55.88 50.8) (xy 55.88 66.04) (xy 76.2 66.04) (xy 76.2 53.34))',
        f'\t\t(stroke (width 0) (type default)) (uuid "{uid()}"))',
        # Wait - U2 VIN- is at (76.2, 48.26) for pin2: symbol at 88.9, pin2 at x-12.7 = 76.2, y-2.54 = 48.26
        # Fix GND wire to pin2 and pin4
    ]
    # Recalculate pin positions carefully:
    # J1 at (38.1, 50.8): pin1 at 38.1-10.16=27.94, pin2 at 38.1+10.16=48.26, both y=50.8
    # U2 at (88.9, 50.8):
    #   pin1 VIN+ (-12.7, +2.54) -> (76.2, 53.34)
    #   pin2 VIN- (-12.7, -2.54) -> (76.2, 48.26)
    #   pin3 VOUT+ (+12.7, +2.54) -> (101.6, 53.34)
    #   pin4 VOUT- (+12.7, -2.54) -> (101.6, 48.26)
    # U1 at (165.1, 76.2):
    #   VIN pin16 at (+12.7+5.08, +17.78) = (182.88, 93.98)
    #   GND pin17 at (+12.7+5.08, +15.24) = (182.88, 91.44)
    # Actually pin positions are relative to symbol center:
    # RIGHT pins at body_x+5.08 = 17.78 from center
    # pin16 VIN at y = +17.78 -> (165.1+17.78, 76.2-17.78)? 
    # In KiCad, +Y is up in schematic... Actually in KiCad schematic Y increases downward!
    # Symbol pin at (at 17.78 17.78 180) means local coords; when symbol at (165.1, 76.2),
    # pin world = (165.1+17.78, 76.2-17.78) if Y flipped... 
    # KiCad: local +Y of pin goes UP on screen which is DECREASING global Y.
    # Global pin = (at_x + local_x, at_y - local_y) for rotation 0.
    # U1 pin16: local (17.78, 17.78) -> (182.88, 58.42)
    # U1 pin17: local (17.78, 15.24) -> (182.88, 60.96)
    # U1 pin2 GND left: local (-17.78, 15.24) -> (147.32, 60.96)

    # Rebuild wires section properly - replace the broken wire section
    # We'll rewrite the whole file more carefully instead of appending broken wires.

    # Actually the code above already started writing bad wires. Let me rewrite write_schematic completely.
    raise RuntimeError("internal: use write_schematic_v2")


def write_schematic_v2() -> Path:
    sch_uuid = uid()
    j1_uuid, u2_uuid, u1_uuid = uid(), uid(), uid()
    j2_uuid, j3_uuid, u3_uuid = uid(), uid(), uid()

    emb = "\n".join(
        [
            _embed_from_lib("TerminalBlock_2P"),
            _embed_from_lib("MP1584_5V3A"),
            _embed_from_lib("ESP32_S3_DevKitC_1"),
            _embed_from_lib("Conn_1x04_Motor"),
            _embed_from_lib(TFT_SYM),
            _embed_from_lib("TMC2209_StepStick"),
            _embed_from_lib("PC817_4CH_Opto"),
            _embed_from_lib("Conn_1x10_OptoField"),
            _embed_from_lib("DRV8871_Module"),
            _embed_from_lib("Conn_1x02_MotorDC"),
            _embed_from_lib("Conn_1x02_LimitSW"),
            _embed_from_lib("Conn_1x04_BUP30S"),
            _embed_from_lib("R_BUP_Pullup"),
        ]
    )

    # Symbol placements
    j1 = (38.1, 63.5)
    u2 = (95.25, 63.5)
    u1 = (165.1, 88.9)
    u3 = (95.25, 139.7)
    j2 = (165.1, 139.7)
    j3 = (215.9, 139.7)

    # Pin absolute positions (KiCad: world_y = at_y - local_y)
    j1_p1 = (j1[0] - 10.16, j1[1])  # +12V
    j1_p2 = (j1[0] + 10.16, j1[1])  # GND
    u2_vinp = (u2[0] - 12.7, u2[1] - 2.54)  # VIN+
    u2_ving = (u2[0] - 12.7, u2[1] + 2.54)  # VIN-
    u2_voutp = (u2[0] + 12.7, u2[1] - 2.54)  # VOUT+
    u2_voutg = (u2[0] + 12.7, u2[1] + 2.54)  # VOUT-
    u1_gnd_r = None  # set after u1_pin
    u1_gnd_l = None

    def u1_pin(num: int) -> tuple[float, float]:
        top = 26.67  # (22-1)*1.27
        if num <= 22:
            ly = top - (num - 1) * 2.54
            return (u1[0] - 17.78, u1[1] - ly)
        ly = top - (num - 23) * 2.54
        return (u1[0] + 17.78, u1[1] - ly)

    u1_3v3 = u1_pin(1)
    u1_5v = u1_pin(21)  # 5V power in
    u1_io_step = u1_pin(PIN_BY_NAME["IO16"])  # STEP
    u1_io_dir = u1_pin(PIN_BY_NAME["IO17"])  # DIR
    u1_io_en = u1_pin(PIN_BY_NAME["IO18"])  # EN
    u1_io25 = u1_io_step
    u1_io26 = u1_io_dir
    u1_io27 = u1_io_en
    u1_vin = u1_pin(21)
    u1_gnd_r = u1_pin(22)
    u1_gnd_l = u1_pin(22)

    # U3 TMC pins (local from symbol)
    u3_vm = (u3[0] - 15.24, u3[1] - 7.62)
    u3_gnd = (u3[0] - 15.24, u3[1] - 5.08)
    u3_vio = (u3[0] - 15.24, u3[1] - 2.54)
    u3_en = (u3[0] - 15.24, u3[1] + 2.54)
    u3_step = (u3[0] - 15.24, u3[1] + 5.08)
    u3_dir = (u3[0] - 15.24, u3[1] + 7.62)
    u3_a2 = (u3[0] + 15.24, u3[1] - 5.08)
    u3_a1 = (u3[0] + 15.24, u3[1] - 2.54)
    u3_b1 = (u3[0] + 15.24, u3[1] + 2.54)
    u3_b2 = (u3[0] + 15.24, u3[1] + 5.08)
    u3_gnd2 = (u3[0] + 15.24, u3[1] + 7.62)

    def j2_pin(n: int) -> tuple[float, float]:
        ys = {1: 3.81, 2: 1.27, 3: -1.27, 4: -3.81}
        return (j2[0], j2[1] - ys[n])

    def j3_pin(n: int) -> tuple[float, float]:
        ys = {1: 6.35, 2: 3.81, 3: 1.27, 4: -1.27, 5: -3.81, 6: -6.35}
        return (j3[0], j3[1] - ys[n])

    def wire(a: tuple[float, float], b: tuple[float, float]) -> str:
        pts = [(round(a[0], 2), round(a[1], 2)), (round(b[0], 2), round(b[1], 2))]
        return (
            "\t(wire\n"
            f"\t\t(pts (xy {pts[0][0]} {pts[0][1]}) (xy {pts[1][0]} {pts[1][1]}))\n"
            "\t\t(stroke (width 0) (type default))\n"
            f'\t\t(uuid "{uid()}")\n'
            "\t)"
        )

    def wire_path(*pts: tuple[float, float]) -> list[str]:
        return [wire(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]

    def label(name: str, x: float, y: float) -> str:
        return (
            f'\t(label "{name}"\n'
            f"\t\t(at {x} {y} 0)\n"
            "\t\t(effects (font (size 1.27 1.27)) (justify left bottom))\n"
            f'\t\t(uuid "{uid()}")\n'
            "\t)"
        )

    def text(txt: str, x: float, y: float, size: float = 1.27) -> str:
        return (
            f'\t(text "{txt}"\n'
            f"\t\t(at {x} {y} 0)\n"
            f"\t\t(effects (font (size {size} {size})) (justify left))\n"
            f'\t\t(uuid "{uid()}")\n'
            "\t)"
        )

    y12 = 45.72
    y5 = 40.64
    ygnd = 73.66
    y3v3 = 35.56

    parts: list[str] = [
        "(kicad_sch",
        "\t(version 20250114)",
        '\t(generator "gen_power_carrier.py")',
        '\t(generator_version "1.0")',
        f'\t(uuid "{sch_uuid}")',
        '\t(paper "A3")',
        "\t(title_block",
        '\t\t(title "ESP32-S3 Baseboard - MP1584 + TMC + Opto + 3x DRV8871")',
        '\t\t(comment 1 "BOTTOM: J1 U2 U3 U4 U5-7 U1 | TOP: J2 J3 J4 J5-7")',
        '\t\t(comment 2 "TMC2209 VM=12V VIO=3V3 STEP/DIR/EN from ESP32")',
        "\t)",
        "\t(lib_symbols",
        emb,
        "\t)",
        text("BOTTOM: J1 12V + MP1584EN + TMC2209 + ESP32", 20.32, 22.86, 1.27),
        text("TOP: J2 NEMA17 phases / J17 TFT / J15 buzzer / J16 MOSFET", 20.32, 120.65, 1.27),
        # J1
        f'\t(symbol (lib_id "ESP32_Carrier:TerminalBlock_2P") (at {j1[0]} {j1[1]} 0) (unit 1)',
        f'\t\t(uuid "{j1_uuid}")',
        f'\t\t(property "Reference" "J1" (at {j1[0]} {j1[1] - 7.62} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)))",
        "\t\t)",
        f'\t\t(property "Value" "Screw_12V_IN" (at {j1[0]} {j1[1] + 7.62} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)))",
        "\t\t)",
        f'\t\t(property "Footprint" "ESP32_Carrier:TerminalBlock_2P_5.0mm" (at {j1[0]} {j1[1]} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\t\t)",
        f'\t\t(property "Datasheet" "~" (at {j1[0]} {j1[1]} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\t\t)",
        f'\t\t(pin "1" (uuid "{uid()}"))',
        f'\t\t(pin "2" (uuid "{uid()}"))',
        "\t\t(instances",
        f'\t\t\t(project "esp32_baseboard" (path "/{sch_uuid}" (reference "J1") (unit 1)))',
        "\t\t)",
        "\t)",
        # U2
        f'\t(symbol (lib_id "ESP32_Carrier:MP1584_5V3A") (at {u2[0]} {u2[1]} 0) (unit 1)',
        f'\t\t(uuid "{u2_uuid}")',
        f'\t\t(property "Reference" "U2" (at {u2[0]} {u2[1] - 10.16} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)))",
        "\t\t)",
        f'\t\t(property "Value" "MP1584_5V3A" (at {u2[0]} {u2[1] + 10.16} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)))",
        "\t\t)",
        f'\t\t(property "Footprint" "ESP32_Carrier:MP1584_5V3A" (at {u2[0]} {u2[1]} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\t\t)",
        f'\t\t(property "Datasheet" "~" (at {u2[0]} {u2[1]} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\t\t)",
        f'\t\t(pin "1" (uuid "{uid()}"))',
        f'\t\t(pin "2" (uuid "{uid()}"))',
        f'\t\t(pin "3" (uuid "{uid()}"))',
        f'\t\t(pin "4" (uuid "{uid()}"))',
        "\t\t(instances",
        f'\t\t\t(project "esp32_baseboard" (path "/{sch_uuid}" (reference "U2") (unit 1)))',
        "\t\t)",
        "\t)",
        # U1
        f'\t(symbol (lib_id "ESP32_Carrier:ESP32_S3_DevKitC_1") (at {u1[0]} {u1[1]} 0) (unit 1)',
        f'\t\t(uuid "{u1_uuid}")',
        f'\t\t(property "Reference" "U1" (at {u1[0]} {u1[1] - 25.4} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)))",
        "\t\t)",
        f'\t\t(property "Value" "ESP32_S3_DevKitC_1" (at {u1[0]} {u1[1] + 25.4} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)))",
        "\t\t)",
        f'\t\t(property "Footprint" "ESP32_Carrier:ESP32_S3_DevKitC_44Pin_Socket" (at {u1[0]} {u1[1]} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\t\t)",
        f'\t\t(property "Datasheet" "~" (at {u1[0]} {u1[1]} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\t\t)",
    ]
    for n in range(1, 31):
        parts.append(f'\t\t(pin "{n}" (uuid "{uid()}"))')
    parts += [
        "\t\t(instances",
        f'\t\t\t(project "esp32_baseboard" (path "/{sch_uuid}" (reference "U1") (unit 1)))',
        "\t\t)",
        "\t)",
        # U3 TMC2209
        f'\t(symbol (lib_id "ESP32_Carrier:TMC2209_StepStick") (at {u3[0]} {u3[1]} 0) (unit 1)',
        f'\t\t(uuid "{u3_uuid}")',
        f'\t\t(property "Reference" "U3" (at {u3[0]} {u3[1] - 13.97} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)))",
        "\t\t)",
        f'\t\t(property "Value" "TMC2209_StepStick" (at {u3[0]} {u3[1] + 13.97} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)))",
        "\t\t)",
        f'\t\t(property "Footprint" "ESP32_Carrier:TMC2209_StepStick" (at {u3[0]} {u3[1]} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\t\t)",
        f'\t\t(property "Datasheet" "~" (at {u3[0]} {u3[1]} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\t\t)",
    ]
    for n in ["1", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16"]:
        parts.append(f'\t\t(pin "{n}" (uuid "{uid()}"))')
    parts += [
        "\t\t(instances",
        f'\t\t\t(project "esp32_baseboard" (path "/{sch_uuid}" (reference "U3") (unit 1)))',
        "\t\t)",
        "\t)",
        # J2 NEMA17 (TOP)
        f'\t(symbol (lib_id "ESP32_Carrier:Conn_1x04_Motor") (at {j2[0]} {j2[1]} 0) (unit 1)',
        f'\t\t(uuid "{j2_uuid}")',
        f'\t\t(property "Reference" "J2" (at {j2[0]} {j2[1] - 10.16} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)))",
        "\t\t)",
        f'\t\t(property "Value" "NEMA17_OUT" (at {j2[0]} {j2[1] + 10.16} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)))",
        "\t\t)",
        f'\t\t(property "Footprint" "ESP32_Carrier:PinHeader_1x04_Motor" (at {j2[0]} {j2[1]} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\t\t)",
        f'\t\t(property "Datasheet" "~" (at {j2[0]} {j2[1]} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\t\t)",
        f'\t\t(pin "1" (uuid "{uid()}"))',
        f'\t\t(pin "2" (uuid "{uid()}"))',
        f'\t\t(pin "3" (uuid "{uid()}"))',
        f'\t\t(pin "4" (uuid "{uid()}"))',
        "\t\t(instances",
        f'\t\t\t(project "esp32_baseboard" (path "/{sch_uuid}" (reference "J2") (unit 1)))',
        "\t\t)",
        "\t)",
        # J17 TFT (TOP)
        f'\t(symbol (lib_id "ESP32_Carrier:{TFT_SYM}") (at {j3[0]} {j3[1]} 0) (unit 1)',
        f'\t\t(uuid "{j3_uuid}")',
        f'\t\t(property "Reference" "J17" (at {j3[0]} {j3[1] - 12.7} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)))",
        "\t\t)",
        f'\t\t(property "Value" "TFT_TOUCH" (at {j3[0]} {j3[1] + 17.78} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)))",
        "\t\t)",
        f'\t\t(property "Footprint" "ESP32_Carrier:{TFT_FP}" (at {j3[0]} {j3[1]} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\t\t)",
        f'\t\t(property "Datasheet" "~" (at {j3[0]} {j3[1]} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\t\t)",
        *[f'\t\t(pin "{n}" (uuid "{uid()}"))' for n in range(1, TFT_PINS + 1)],
        "\t\t(instances",
        f'\t\t\t(project "esp32_baseboard" (path "/{sch_uuid}" (reference "J17") (unit 1)))',
        "\t\t)",
        "\t)",
        # Power
        *wire_path(j1_p1, (j1_p1[0], y12), (u2_vinp[0], y12), u2_vinp),
        *wire_path((u2_vinp[0], y12), (u3_vm[0], y12), u3_vm),
        label("+12V", 55.88, y12),
        *wire_path(u2_voutp, (u2_voutp[0], y5), (u1_vin[0], y5), u1_vin),
        label("+5V", 120.65, y5),
        *wire_path(j1_p2, (j1_p2[0], ygnd)),
        *wire_path((j1_p2[0], ygnd), (u2_ving[0], ygnd), u2_ving),
        *wire_path((u2_ving[0], ygnd), (u2_voutg[0], ygnd), u2_voutg),
        *wire_path((u2_voutg[0], ygnd), (u1_gnd_r[0], ygnd), u1_gnd_r),
        *wire_path((u1_gnd_r[0], ygnd), (u1_gnd_l[0], ygnd), u1_gnd_l),
        *wire_path((u1_gnd_l[0], ygnd), (u3_gnd[0], ygnd), u3_gnd),
        *wire_path(u3_gnd2, (u3_gnd2[0], ygnd + 2.54), (u3_gnd[0], ygnd + 2.54), (u3_gnd[0], ygnd)),
        label("GND", 55.88, ygnd),
        # VIO 3V3
        *wire_path(u1_3v3, (u1_3v3[0], y3v3), (u3_vio[0], y3v3), u3_vio),
        label("+3V3", 120.65, y3v3),
        # TMC control
        *wire_path(u1_io25, (150.0, u1_io25[1]), (150.0, u3_step[1]), u3_step),
        *wire_path(u1_io26, (147.5, u1_io26[1]), (147.5, u3_dir[1]), u3_dir),
        *wire_path(u1_io27, (145.0, u1_io27[1]), (145.0, u3_en[1]), u3_en),
        label("STEP", 140.0, u3_step[1]),
        label("DIR", 140.0, u3_dir[1]),
        label("EN", 140.0, u3_en[1]),
        # Motor phases U3 -> J2
        *wire_path(u3_a2, (u3_a2[0] + 10, u3_a2[1]), (j2_pin(1)[0], u3_a2[1]), j2_pin(1)),
        *wire_path(u3_a1, (u3_a1[0] + 12, u3_a1[1]), (j2_pin(2)[0], u3_a1[1]), j2_pin(2)),
        *wire_path(u3_b1, (u3_b1[0] + 14, u3_b1[1]), (j2_pin(3)[0], u3_b1[1]), j2_pin(3)),
        *wire_path(u3_b2, (u3_b2[0] + 16, u3_b2[1]), (j2_pin(4)[0], u3_b2[1]), j2_pin(4)),
        # J3 legacy sensor removed — TFT/buzzer/MOSFET on separate jacks (PCB)
    ]

    # --- PC817 opto U4+U9 (2x 4CH) + J4 field header ---
    u4 = (240.0, 88.9)
    u9 = (290.0, 88.9)
    j4 = (265.0, 165.1)
    u4_uuid, u9_uuid, j4_uuid = uid(), uid(), uid()

    def _opto4_sym(ref: str, at: tuple[float, float], suuid: str) -> list[str]:
        pl = [
            f'\t(symbol (lib_id "ESP32_Carrier:PC817_4CH_Opto") (at {at[0]} {at[1]} 0) (unit 1)',
            f'\t\t(uuid "{suuid}")',
            f'\t\t(property "Reference" "{ref}" (at {at[0]} {at[1] - 15.24} 0)',
            "\t\t\t(effects (font (size 1.27 1.27)))",
            "\t\t)",
            f'\t\t(property "Value" "PC817_4CH" (at {at[0]} {at[1] + 15.24} 0)',
            "\t\t\t(effects (font (size 1.27 1.27)))",
            "\t\t)",
            f'\t\t(property "Footprint" "ESP32_Carrier:PC817_4CH_Opto" (at {at[0]} {at[1]} 0)',
            "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
            "\t\t)",
            f'\t\t(property "Datasheet" "~" (at {at[0]} {at[1]} 0)',
            "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
            "\t\t)",
        ]
        for n in range(1, 13):
            pl.append(f'\t\t(pin "{n}" (uuid "{uid()}"))')
        pl += [
            "\t\t(instances",
            f'\t\t\t(project "esp32_baseboard" (path "/{sch_uuid}" (reference "{ref}") (unit 1)))',
            "\t\t)",
            "\t)",
        ]
        return pl

    parts += _opto4_sym("U4", u4, u4_uuid)
    parts += _opto4_sym("U9", u9, u9_uuid)
    parts += [
        f'\t(symbol (lib_id "ESP32_Carrier:Conn_1x10_OptoField") (at {j4[0]} {j4[1]} 0) (unit 1)',
        f'\t\t(uuid "{j4_uuid}")',
        f'\t\t(property "Reference" "J4" (at {j4[0]} {j4[1] - 16.51} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)))",
        "\t\t)",
        f'\t\t(property "Value" "OPTO_FIELD_IN" (at {j4[0]} {j4[1] + 16.51} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)))",
        "\t\t)",
        f'\t\t(property "Footprint" "ESP32_Carrier:PinHeader_1x10_OptoField" (at {j4[0]} {j4[1]} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\t\t)",
        f'\t\t(property "Datasheet" "~" (at {j4[0]} {j4[1]} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\t\t)",
    ]
    for n in range(1, 11):
        parts.append(f'\t\t(pin "{n}" (uuid "{uid()}"))')
    parts += [
        "\t\t(instances",
        f'\t\t\t(project "esp32_baseboard" (path "/{sch_uuid}" (reference "J4") (unit 1)))',
        "\t\t)",
        "\t)",
        text("U4+U9 PC817 4ch x2 + J4 field IN (TOP)", 210.0, 55.88, 1.27),
    ]

    def opto4_pin(at: tuple[float, float], num: int) -> tuple[float, float]:
        # pins 1-6 left, 7-12 right (matches symbol)
        if num <= 6:
            ly = 7.62 - (num - 1) * 2.54
            return (at[0] - 15.24, at[1] - ly)
        ly = 7.62 - (num - 7) * 2.54
        return (at[0] + 15.24, at[1] - ly)

    def j4_pin(n: int) -> tuple[float, float]:
        ly = 11.43 - (n - 1) * 2.54
        return (j4[0], j4[1] - ly)

    # J4.1-6 -> U4.1-6 ; J4.1-2 also to U9 ; J4.7-10 -> U9.3-6
    for n in range(1, 7):
        parts += wire_path(j4_pin(n), (j4_pin(n)[0] - 12.7, j4_pin(n)[1]), opto4_pin(u4, n))
    for n in (1, 2):
        parts += wire_path(
            opto4_pin(u4, n),
            (opto4_pin(u4, n)[0] - 5.08, opto4_pin(u4, n)[1]),
            (opto4_pin(u9, n)[0] - 5.08, opto4_pin(u9, n)[1]),
            opto4_pin(u9, n),
        )
    for i, jn in enumerate(range(7, 11)):
        parts += wire_path(
            j4_pin(jn),
            (j4_pin(jn)[0] + 12.7, j4_pin(jn)[1]),
            opto4_pin(u9, 3 + i),
        )
    for n in range(3, 11):
        jp = j4_pin(n)
        parts.append(label(f"OPTO_IN{n - 2}", jp[0] - 7.62, jp[1]))
    # MCU power OUT side
    for at, ref_note in ((u4, "U4"), (u9, "U9")):
        parts += wire_path(
            opto4_pin(at, 8),
            (opto4_pin(at, 8)[0] + 8, opto4_pin(at, 8)[1]),
            (opto4_pin(at, 8)[0] + 8, y3v3),
            (u1_3v3[0], y3v3),
        )
        parts += wire_path(
            opto4_pin(at, 7),
            (opto4_pin(at, 7)[0] + 10, opto4_pin(at, 7)[1]),
            (opto4_pin(at, 7)[0] + 10, ygnd),
            (u1_gnd_l[0], ygnd),
        )
    parts.append(text("GND_I=GND (limit SW @12V shared)", 210.0, 63.5, 1.0))
    # OUT1-4 on U4 -> IO1,2,4,5 ; OUT1-4 on U9 -> IO6,7,8,9
    opto_map = [
        (u4, 9, 26),
        (u4, 10, 27),
        (u4, 11, 4),
        (u4, 12, 5),
        (u9, 9, 6),
        (u9, 10, 7),
        (u9, 11, 12),
        (u9, 12, 15),
    ]
    for i, (at, pn, esp_pin) in enumerate(opto_map):
        u_out = opto4_pin(at, pn)
        e_pt = u1_pin(esp_pin)
        xbus = u_out[0] + 5.08 + i * 2.0
        parts += wire_path(u_out, (xbus, u_out[1]), (xbus, e_pt[1]), e_pt)
        parts.append(label(f"OPTO_OUT{i + 1}", xbus, u_out[1]))

    # --- 3x DRV8871 (U5/U6/U7) + GA12-N20 jacks J5/J6/J7 ---
    parts.append(text("BOTTOM: U5/U6/U7 DRV8871 @12V | TOP: J5/J6/J7 GA12-N20", 20.32, 185.0, 1.27))
    l298n_place = [
        # motor + 2x limit NC @12V -> opto IN1..IN6
        # (U, Jmot, Jmin, Jmax, xu, yu, xj, yj, in1, in2, u4_in_min, u4_in_max, label)
        ("U5", "J5", "J8", "J9", 95.25, 203.2, 165.1, 203.2, 16, 17, 3, 4, "TRUC1 MOT+LIM"),
        ("U6", "J6", "J10", "J11", 95.25, 241.3, 165.1, 241.3, 18, 19, 5, 6, "TRUC2 MOT+LIM"),
        ("U7", "J7", "J12", "J13", 95.25, 279.4, 165.1, 279.4, 20, 8, 7, 8, "TRUC3 MOT+LIM"),
    ]
    for mi, (ref_u, ref_j, jmin, jmax, xu, yu, xj, yj, pin_in1, pin_in2, u4min, u4max, lab) in enumerate(l298n_place):
        uu, ju = uid(), uid()
        # Pin world pos: world_y = at_y - local_y (symbol locals above)
        vs = (xu - 15.24, yu - 5.08)
        gndp = (xu - 15.24, yu - 2.54)
        in1 = (xu - 15.24, yu + 2.54)
        in2 = (xu - 15.24, yu + 5.08)
        out1 = (xu + 15.24, yu - 2.54)
        out2 = (xu + 15.24, yu + 2.54)
        jmp = (xj, yj - 1.27)  # M+
        jmm = (xj, yj + 1.27)  # M-
        parts += [
            f'\t(symbol (lib_id "ESP32_Carrier:DRV8871_Module") (at {xu} {yu} 0) (unit 1)',
            f'\t\t(uuid "{uu}")',
            f'\t\t(property "Reference" "{ref_u}" (at {xu} {yu - 13.97} 0)',
            "\t\t\t(effects (font (size 1.27 1.27)))",
            "\t\t)",
            f'\t\t(property "Value" "DRV8871_Module" (at {xu} {yu + 13.97} 0)',
            "\t\t\t(effects (font (size 1.27 1.27)))",
            "\t\t)",
            f'\t\t(property "Footprint" "ESP32_Carrier:DRV8871_Module" (at {xu} {yu} 0)',
            "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
            "\t\t)",
            f'\t\t(property "Datasheet" "~" (at {xu} {yu} 0)',
            "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
            "\t\t)",
        ]
        for n in ["1", "2", "3", "4", "5", "6"]:
            parts.append(f'\t\t(pin "{n}" (uuid "{uid()}"))')
        parts += [
            "\t\t(instances",
            f'\t\t\t(project "esp32_baseboard" (path "/{sch_uuid}" (reference "{ref_u}") (unit 1)))',
            "\t\t)",
            "\t)",
            f'\t(symbol (lib_id "ESP32_Carrier:Conn_1x02_MotorDC") (at {xj} {yj} 0) (unit 1)',
            f'\t\t(uuid "{ju}")',
            f'\t\t(property "Reference" "{ref_j}" (at {xj} {yj - 7.62} 0)',
            "\t\t\t(effects (font (size 1.27 1.27)))",
            "\t\t)",
            f'\t\t(property "Value" "GA12_N20" (at {xj} {yj + 7.62} 0)',
            "\t\t\t(effects (font (size 1.27 1.27)))",
            "\t\t)",
            f'\t\t(property "Footprint" "ESP32_Carrier:PinHeader_1x02_MotorDC" (at {xj} {yj} 0)',
            "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
            "\t\t)",
            f'\t\t(property "Datasheet" "~" (at {xj} {yj} 0)',
            "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
            "\t\t)",
            f'\t\t(pin "1" (uuid "{uid()}"))',
            f'\t\t(pin "2" (uuid "{uid()}"))',
            "\t\t(instances",
            f'\t\t\t(project "esp32_baseboard" (path "/{sch_uuid}" (reference "{ref_j}") (unit 1)))',
            "\t\t)",
            "\t)",
            text(lab, xu - 25.4, yu - 15.24, 1.0),
        ]
        # +12V / GND
        parts += wire_path(vs, (vs[0], y12), (u3_vm[0], y12))
        parts += wire_path(gndp, (gndp[0], ygnd), (u3_gnd[0], ygnd))
        # Motor outs
        parts += wire_path(out1, (out1[0] + 8, out1[1]), (jmp[0], out1[1]), jmp)
        parts += wire_path(out2, (out2[0] + 10, out2[1]), (jmm[0], out2[1]), jmm)
        # IN1 / IN2 from ESP32 — unique vertical lanes (grid 1.27)
        e1 = u1_pin(pin_in1)
        e2 = u1_pin(pin_in2)
        xbus1 = 50.8 + mi * 5.08
        xbus2 = 53.34 + mi * 5.08
        parts += wire_path(e1, (xbus1, e1[1]), (xbus1, in1[1]), in1)
        parts += wire_path(e2, (xbus2, e2[1]), (xbus2, in2[1]), in2)
        parts.append(label(f"{ref_u}_IN1", xbus1, in1[1]))
        parts.append(label(f"{ref_u}_IN2", xbus2, in2[1]))

        # Limit MIN/MAX jacks (NC): +12V --[NC SW]-- OPTO_INx (net label, no shared bus wires)
        xj_min, xj_max = xj + 25.4, xj + 50.8
        for jref_l, xjl, u4p, tag in [
            (jmin, xj_min, u4min, "MIN"),
            (jmax, xj_max, u4max, "MAX"),
        ]:
            ju = uid()
            p12 = (xjl, yj - 1.27)
            psw = (xjl, yj + 1.27)
            ch = u4p - 2  # U4 pin3 -> IN1
            parts += [
                f'\t(symbol (lib_id "ESP32_Carrier:Conn_1x02_LimitSW") (at {xjl} {yj} 0) (unit 1)',
                f'\t\t(uuid "{ju}")',
                f'\t\t(property "Reference" "{jref_l}" (at {xjl} {yj - 7.62} 0)',
                "\t\t\t(effects (font (size 1.27 1.27)))",
                "\t\t)",
                f'\t\t(property "Value" "LIM_{tag}_NC" (at {xjl} {yj + 7.62} 0)',
                "\t\t\t(effects (font (size 1.27 1.27)))",
                "\t\t)",
                f'\t\t(property "Footprint" "ESP32_Carrier:PinHeader_1x02_LimitSW" (at {xjl} {yj} 0)',
                "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
                "\t\t)",
                f'\t\t(property "Datasheet" "~" (at {xjl} {yj} 0)',
                "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
                "\t\t)",
                f'\t\t(pin "1" (uuid "{uid()}"))',
                f'\t\t(pin "2" (uuid "{uid()}"))',
                "\t\t(instances",
                f'\t\t\t(project "esp32_baseboard" (path "/{sch_uuid}" (reference "{jref_l}") (unit 1)))',
                "\t\t)",
                "\t)",
            ]
            # Short stubs + net labels only (no long wires that cross the sheet)
            parts += wire_path(p12, (p12[0], p12[1] - 2.54))
            parts.append(label("+12V_SNS", p12[0], p12[1] - 2.54))
            parts += wire_path(psw, (psw[0] + 5.08, psw[1]))
            parts.append(label(f"OPTO_IN{ch}", psw[0] + 5.08, psw[1]))

        # DRV8871: no ENA/5V pads (unlike L298N)

    # --- Autonics BUP-30S (NPN) @12V -> OPTO_IN7 ---
    j14 = (95.25, 320.04)
    r1 = (120.65, 320.04)
    j14_uuid, r1_uuid = uid(), uid()
    parts.append(text("BUP-30S NPN: Nau=+12 Xanh=GND Den=OUT Trang=CTRL", 70.0, 304.8, 1.0))
    parts += [
        f'\t(symbol (lib_id "ESP32_Carrier:Conn_1x04_BUP30S") (at {j14[0]} {j14[1]} 0) (unit 1)',
        f'\t\t(uuid "{j14_uuid}")',
        f'\t\t(property "Reference" "J14" (at {j14[0]} {j14[1] - 10.16} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)))",
        "\t\t)",
        f'\t\t(property "Value" "BUP_30S" (at {j14[0]} {j14[1] + 10.16} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)))",
        "\t\t)",
        f'\t\t(property "Footprint" "ESP32_Carrier:PinHeader_1x04_BUP30S" (at {j14[0]} {j14[1]} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\t\t)",
        f'\t\t(property "Datasheet" "~" (at {j14[0]} {j14[1]} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\t\t)",
    ]
    for n in range(1, 5):
        parts.append(f'\t\t(pin "{n}" (uuid "{uid()}"))')
    parts += [
        "\t\t(instances",
        f'\t\t\t(project "esp32_baseboard" (path "/{sch_uuid}" (reference "J14") (unit 1)))',
        "\t\t)",
        "\t)",
        f'\t(symbol (lib_id "ESP32_Carrier:R_BUP_Pullup") (at {r1[0]} {r1[1]} 0) (unit 1)',
        f'\t\t(uuid "{r1_uuid}")',
        f'\t\t(property "Reference" "R1" (at {r1[0] + 5.08} {r1[1]} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)))",
        "\t\t)",
        f'\t\t(property "Value" "4k7" (at {r1[0] + 5.08} {r1[1] + 2.54} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)))",
        "\t\t)",
        f'\t\t(property "Footprint" "ESP32_Carrier:R_Axial_4k7_BUP" (at {r1[0]} {r1[1]} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\t\t)",
        f'\t\t(pin "1" (uuid "{uid()}"))',
        f'\t\t(pin "2" (uuid "{uid()}"))',
        "\t\t(instances",
        f'\t\t\t(project "esp32_baseboard" (path "/{sch_uuid}" (reference "R1") (unit 1)))',
        "\t\t)",
        "\t)",
    ]
    j14_12 = (j14[0], j14[1] - 3.81)
    j14_gnd = (j14[0], j14[1] - 1.27)
    j14_out = (j14[0], j14[1] + 1.27)
    j14_ctrl = (j14[0], j14[1] + 3.81)
    r1_a = (r1[0], r1[1] - 3.81)
    r1_b = (r1[0], r1[1] + 3.81)
    # Stubs + net labels only (avoid long wires crossing sheet)
    parts += wire_path(j14_12, (j14_12[0] - 5.08, j14_12[1]))
    parts.append(label("+12V_SNS", j14_12[0] - 5.08, j14_12[1]))
    parts += wire_path(j14_gnd, (j14_gnd[0] - 5.08, j14_gnd[1]))
    parts.append(label("GND", j14_gnd[0] - 5.08, j14_gnd[1]))
    parts += wire_path(j14_out, (j14_out[0] + 5.08, j14_out[1]))
    parts.append(label("OPTO_IN7", j14_out[0] + 5.08, j14_out[1]))
    parts += wire_path(r1_a, (r1_a[0], r1_a[1] - 2.54))
    parts.append(label("+12V_SNS", r1_a[0], r1_a[1] - 2.54))
    parts += wire_path(r1_b, (r1_b[0], r1_b[1] + 2.54))
    parts.append(label("OPTO_IN7", r1_b[0], r1_b[1] + 2.54))
    parts.append(f'\t(no_connect (at {j14_ctrl[0]} {j14_ctrl[1]}) (uuid "{uid()}"))')
    parts.append(text("CTRL: LightON->+12V / DarkON->GND", j14[0] - 5, j14[1] + 12.7, 1.0))


    # --- STAR POWER: RC filter +12V -> +12V_SNS ---
    parts.append(text("STAR: +12V_MOT (rong) / +12V_SNS qua R10=10R + C47u||100n", 20.32, 304.8, 1.0))
    # Net labels only: document filter (R10 C_SNS placed on PCB)
    parts.append(label("+12V", 38.1, 312.42))
    parts.append(label("+12V_SNS", 63.5, 312.42))
    parts.append(text("R10 10R + C10 47u + C11 100n (tren PCB)", 38.1, 317.5, 1.0))
    parts.append(text("Bulk 470u tai moi DRV8871/TMC (tren PCB)", 38.1, 322.58, 1.0))

    used = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27}

    pin_ys_nc = [17.78 - i * 2.54 for i in range(15)]
    for num in range(1, 31):
        if num in used:
            continue
        if num <= 15:
            px = u1[0] - 17.78
            py = u1[1] - pin_ys_nc[num - 1]
        else:
            px = u1[0] + 17.78
            py = u1[1] - pin_ys_nc[num - 16]
        parts.append(f'\t(no_connect (at {px} {py}) (uuid "{uid()}"))')

    parts += [
        f'\t(junction (at 66.04 {y12}) (diameter 0) (color 0 0 0 0)',
        f'\t\t(uuid "{uid()}"))',
        f'\t(symbol (lib_id "ESP32_Carrier:PWR_FLAG") (at 66.04 {y12} 0) (unit 1)',
        f'\t\t(uuid "{uid()}")',
        f'\t\t(property "Reference" "#FLG1" (at 66.04 {y12 - 5.08} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\t\t)",
        f'\t\t(property "Value" "PWR_FLAG" (at 66.04 {y12 - 3.81} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)))",
        "\t\t)",
        f'\t\t(pin "1" (uuid "{uid()}"))',
        "\t\t(instances",
        f'\t\t\t(project "esp32_baseboard" (path "/{sch_uuid}" (reference "#FLG1") (unit 1)))',
        "\t\t)",
        "\t)",
        '\t(sheet_instances (path "/" (page "1")))',
        ")",
    ]

    emb_pf = _pwr_flag_embedded()
    text_out = "\n".join(parts) + "\n"
    text_out = text_out.replace(
        "\t(lib_symbols\n" + emb + "\n\t)",
        "\t(lib_symbols\n" + emb + "\n" + emb_pf + "\n\t)",
        1,
    )
    out = ROOT / "esp32_baseboard.kicad_sch"
    out.write_text(text_out, encoding="utf-8")
    return out


def _pwr_flag_embedded() -> str:
    return """\t\t(symbol "ESP32_Carrier:PWR_FLAG"
\t\t\t(exclude_from_sim no)
\t\t\t(in_bom no)
\t\t\t(on_board no)
\t\t\t(property "Reference" "#FLG"
\t\t\t\t(at 0 5.08 0)
\t\t\t\t(effects (font (size 1.27 1.27)) (hide yes))
\t\t\t)
\t\t\t(property "Value" "PWR_FLAG"
\t\t\t\t(at 0 3.81 0)
\t\t\t\t(effects (font (size 1.27 1.27)))
\t\t\t)
\t\t\t(property "Footprint" ""
\t\t\t\t(at 0 0 0)
\t\t\t\t(hide yes)
\t\t\t\t(effects (font (size 1.27 1.27)))
\t\t\t)
\t\t\t(property "Datasheet" ""
\t\t\t\t(at 0 0 0)
\t\t\t\t(hide yes)
\t\t\t\t(effects (font (size 1.27 1.27)))
\t\t\t)
\t\t\t(property "Description" "Power flag for ERC"
\t\t\t\t(at 0 0 0)
\t\t\t\t(hide yes)
\t\t\t\t(effects (font (size 1.27 1.27)))
\t\t\t)
\t\t\t(symbol "PWR_FLAG_0_1"
\t\t\t\t(pin power_out line
\t\t\t\t\t(at 0 0 0)
\t\t\t\t\t(length 0)
\t\t\t\t\t(name "pwr" (effects (font (size 1.27 1.27))))
\t\t\t\t\t(number "1" (effects (font (size 1.27 1.27))))
\t\t\t\t)
\t\t\t)
\t\t)"""


def write_pcb() -> Path:
    """BOTTOM: J1/U2/U3/U1 | TOP: J2 NEMA17 + J17 TFT | +12V 3A via farm."""
    y_last = (S3_PINS_PER_SIDE - 1) * PITCH
    lines: list[str] = []
    a = lines.append

    nets = {
        0: "",
        1: "+12V",
        2: "GND",
        3: "+5V",
        4: "+3V3",
        5: "/STEP",
        6: "/DIR",
        # 7-10: legacy /IO32../IO35 from the pre-S3 DevKit V1 design - removed.
        # (IO35 is not even usable on N16R8; a net by that name only misleads.)
        11: "/EN_TMC",
        12: "/MotA2",
        13: "/MotA1",
        14: "/MotB1",
        15: "/MotB2",
        16: "/OPTO_OUT1",
        17: "/OPTO_OUT2",
        18: "/OPTO_OUT3",
        19: "/OPTO_OUT4",
        20: "/OPTO_OUT5",
        21: "/OPTO_OUT6",
        22: "/OPTO_OUT7",
        23: "/OPTO_OUT8",
        24: "/OPTO_VCC_I",
        25: "/OPTO_IN1",
        26: "/OPTO_IN2",
        27: "/OPTO_IN3",
        28: "/OPTO_IN4",
        29: "/OPTO_IN5",
        30: "/OPTO_IN6",
        31: "/OPTO_IN7",
        32: "/OPTO_IN8",
        33: "/OPTO_GND_I",
        34: "/MotDC1_A",
        35: "/MotDC1_B",
        36: "/MotDC2_A",
        37: "/MotDC2_B",
        38: "/MotDC3_A",
        39: "/MotDC3_B",
        40: "/DC1_IN1",
        41: "/DC1_IN2",
        42: "/DC2_IN1",
        43: "/DC2_IN2",
        44: "/DC3_IN1",
        45: "/DC3_IN2",
        46: "+12V_SNS",
        47: "/TFT_SCK",
        48: "/TFT_MOSI",
        50: "/TFT_CS",
        51: "/TFT_DC",
        52: "/I2C_SDA",
        53: "/I2C_SCL",
        54: "/BUZZER",
        55: "/BLOWER",
        56: "+5V_BLW",
        57: "+12V_RAW",
        58: "/TFT_RST",
        59: "/TFT_BL",
        60: "/TP_INT",
        61: "/BLW_RET",
    }

    def track(x1, y1, x2, y2, net, layer, w=0.25):
        a("\t(segment")
        a(f"\t\t(start {x1} {y1})")
        a(f"\t\t(end {x2} {y2})")
        a(f"\t\t(width {w})")
        a(f'\t\t(layer "{layer}")')
        a(f"\t\t(net {net})")
        a(f'\t\t(uuid "{uid()}")')
        a("\t)")

    def via(x, y, net, drill=VIA12_DRILL, dia=VIA12_DIA):
        a("\t(via")
        a(f"\t\t(at {x} {y})")
        a(f"\t\t(size {dia})")
        a(f"\t\t(drill {drill})")
        a('\t\t(layers "F.Cu" "B.Cu")')
        a(f"\t\t(net {net})")
        a(f'\t\t(uuid "{uid()}")')
        a("\t)")

    def gr_text(txt, x, y, layer, size=1.0, rot=0):
        a(f'\t(gr_text "{txt}"')
        a(f"\t\t(at {x} {y} {rot})")
        a(f'\t\t(layer "{layer}")')
        a(f"\t\t(effects (font (size {size} {size}) (thickness {max(0.12, size * 0.15)})))")
        a(f'\t\t(uuid "{uid()}")')
        a("\t)")

    def gr_box(x0, y0, x1, y1, layer):
        a("\t(gr_rect")
        a(f"\t\t(start {x0} {y0})")
        a(f"\t\t(end {x1} {y1})")
        a("\t\t(stroke (width 0.12) (type default))")
        a("\t\t(fill none)")
        a(f'\t\t(layer "{layer}")')
        a(f'\t\t(uuid "{uid()}")')
        a("\t)")

    a("(kicad_pcb")
    a("\t(version 20241229)")
    a('\t(generator "gen_power_carrier.py")')
    a('\t(generator_version "1.0")')
    a("\t(general (thickness 1.6) (legacy_teardrops no))")
    a('\t(paper "A4")')
    a("\t(layers")
    a('\t\t(0 "F.Cu" signal)')
    a('\t\t(2 "B.Cu" signal)')
    a('\t\t(9 "F.Adhes" user "F.Adhesive")')
    a('\t\t(11 "B.Adhes" user "B.Adhesive")')
    a('\t\t(13 "F.Paste" user)')
    a('\t\t(15 "B.Paste" user)')
    a('\t\t(17 "F.SilkS" user "F.Silkscreen")')
    a('\t\t(19 "B.SilkS" user "B.Silkscreen")')
    a('\t\t(21 "F.Mask" user)')
    a('\t\t(23 "B.Mask" user)')
    a('\t\t(25 "Dwgs.User" user "User.Drawings")')
    a('\t\t(27 "Cmts.User" user "User.Comments")')
    a('\t\t(29 "Eco1.User" user "User.Eco1")')
    a('\t\t(31 "Eco2.User" user "User.Eco2")')
    a('\t\t(33 "Edge.Cuts" user)')
    a('\t\t(35 "Margin" user)')
    a('\t\t(37 "F.CrtYd" user "F.Courtyard")')
    a('\t\t(39 "B.CrtYd" user "B.Courtyard")')
    a('\t\t(41 "F.Fab" user "F.Fabrication")')
    a('\t\t(43 "B.Fab" user "B.Fabrication")')
    a("\t)")
    a("\t(setup")
    a("\t\t(pad_to_mask_clearance 0)")
    a("\t\t(allow_soldermask_bridges_in_footprints no)")
    a("\t\t(pcbplotparams")
    a("\t\t\t(layerselection 0x00010fc_ffffffff)")
    a("\t\t\t(plot_on_all_layers_selection 0x0000000_00000000)")
    a("\t\t\t(disableapertmacros no)")
    a("\t\t\t(usegerberextensions no)")
    a("\t\t\t(usegerberattributes yes)")
    a("\t\t\t(usegerberadvancedattributes yes)")
    a("\t\t\t(creategerberjobfile yes)")
    a("\t\t\t(svgprecision 4)")
    a("\t\t\t(outputformat 1)")
    a('\t\t\t(outputdirectory "")')
    a("\t\t)")
    a("\t)")

    for i, name in nets.items():
        a(f'\t(net {i} "{name}")')

    a('\t(net_class "Default" ""')
    a("\t\t(clearance 0.2)")
    a("\t\t(trace_width 0.25)")
    a("\t\t(via_dia 0.6)")
    a("\t\t(via_drill 0.3)")
    a("\t)")
    a('\t(net_class "Power" "12V/5V/GND/motor"')
    a("\t\t(clearance 0.25)")
    a("\t\t(trace_width 1.5)")
    a("\t\t(via_dia 1.1)")
    a("\t\t(via_drill 0.6)")
    a('\t\t(add_net "+12V")')
    a('\t\t(add_net "+12V_RAW")')
    a('\t\t(add_net "+12V_SNS")')
    a('\t\t(add_net "+5V")')
    a('\t\t(add_net "+5V_BLW")')
    a('\t\t(add_net "GND")')
    a('\t\t(add_net "+3V3")')
    a('\t\t(add_net "/MotA2")')
    a('\t\t(add_net "/MotA1")')
    a('\t\t(add_net "/MotB1")')
    a('\t\t(add_net "/MotB2")')
    a('\t\t(add_net "/MotDC1_A")')
    a('\t\t(add_net "/MotDC1_B")')
    a('\t\t(add_net "/MotDC2_A")')
    a('\t\t(add_net "/MotDC2_B")')
    a('\t\t(add_net "/MotDC3_A")')
    a('\t\t(add_net "/MotDC3_B")')
    a("\t)")

    ox, oy = 35.0, 30.0
    bw, bh = 175.0, 175.0
    a("\t(gr_rect")
    a(f"\t\t(start {ox} {oy})")
    a(f"\t\t(end {ox + bw} {oy + bh})")
    a("\t\t(stroke (width 0.1) (type default))")
    a("\t\t(fill none)")
    a('\t\t(layer "Edge.Cuts")')
    a(f'\t\t(uuid "{uid()}")')
    a("\t)")

    # TOP silk
    gr_text("MAT TREN / TOP - NEMA17 & CAM BIEN", ox + 60, oy + 4.5, "F.SilkS", 1.0)
    gr_box(ox + 6, oy + 8, ox + 34, oy + 26, "F.SilkS")
    gr_text("J2 NEMA17 STEPPER", ox + 8, oy + 27.5, "F.SilkS", 0.9)
    gr_text("A2 | A1 | B1 | B2", ox + 8, oy + 22.5, "F.SilkS", 0.75)
    gr_box(ox + 40, oy + 8, ox + 74, oy + 30, "F.SilkS")
    gr_text("J17 TFT + TOUCH", ox + 42, oy + 31.5, "F.SilkS", 0.9)
    gr_text(" | ".join(p[1] for p in TFT_HEADER), ox + 42, oy + 26.5, "F.SilkS", 0.55)

    # BOTTOM silk
    gr_text("MAT DUOI / BOTTOM - MODULE ROI", ox + 60, oy + bh - 4.0, "B.SilkS", 1.0)
    gr_box(ox + 4, oy + 48, ox + 22, oy + 68, "B.SilkS")
    gr_text("J1 NGUON 12V-3A", ox + 5, oy + 69.5, "B.SilkS", 0.9)
    gr_text("via farm 6x0.6mm >=3A", ox + 5, oy + 66.5, "B.SilkS", 0.7)
    gr_box(ox + 26, oy + 48, ox + 56, oy + 68, "B.SilkS")
    gr_text("U2 MP1584EN LOGIC 5V", ox + 27, oy + 69.5, "B.SilkS", 0.85)
    gr_text("12V -> 5V logic", ox + 27, oy + 66.5, "B.SilkS", 0.75)
    gr_box(ox + 88, oy + 82, ox + 116, oy + 110, "B.SilkS")
    gr_text("U3 TMC2209", ox + 89, oy + 111.5, "B.SilkS", 0.9)
    gr_text("stepstick NEMA17", ox + 89, oy + 108.5, "B.SilkS", 0.75)
    gr_box(ox + 62, oy + 48, ox + 100, oy + 78, "B.SilkS")
    gr_text("U1 ESP32 DevKit V1", ox + 63, oy + 79.5, "B.SilkS", 0.9)

    rot = BOTTOM_ROT
    hx = MINI560_PAD_SPAN_X / 2
    hy = MINI560_PAD_SPAN_Y / 2

    # --- J1 BOTTOM ---
    jx, jy = ox + 12.0, oy + 58.0
    a('\t(footprint "ESP32_Carrier:TerminalBlock_2P_5.0mm"')
    a('\t\t(layer "B.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {jx} {jy} {rot})")
    a('\t\t(property "Reference" "J1"')
    a(f"\t\t\t(at 0 -5.5 {rot})")
    a('\t\t\t(layer "B.SilkS")')
    a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "Screw_12V_IN"')
    a(f"\t\t\t(at 0 6.2 {rot})")
    a('\t\t\t(layer "B.Fab")')
    a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")
    for layer, w in (("B.CrtYd", 0.05), ("B.Fab", 0.1), ("B.SilkS", 0.12)):
        a("\t\t(fp_rect")
        a("\t\t\t(start -5.1 -4)")
        a("\t\t\t(end 5.1 4)")
        a(f"\t\t\t(stroke (width {w}) (type solid))")
        a("\t\t\t(fill none)")
        a(f'\t\t\t(layer "{layer}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
    a('\t\t(pad "1" thru_hole rect')
    a(f"\t\t\t(at {-TB_PITCH / 2} 0)")
    a("\t\t\t(size 2.8 2.8)")
    a("\t\t\t(drill 1.5)")
    a('\t\t\t(layers "*.Cu" "*.Mask")')
    a('\t\t\t(net 57 "+12V_RAW")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(pad "2" thru_hole circle')
    a(f"\t\t\t(at {TB_PITCH / 2} 0)")
    a("\t\t\t(size 2.8 2.8)")
    a("\t\t\t(drill 1.5)")
    a('\t\t\t(layers "*.Cu" "*.Mask")')
    a('\t\t\t(net 2 "GND")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t)")

    # --- F1 PTC (series) + D1 TVS (shunt) after J1 ---
    # Path: J1.+12V_RAW -> F1 -> +12V ; D1 across +12V-GND
    f1x, f1y = ox + 26.0, oy + 58.0
    a('\t(footprint "ESP32_Carrier:Fuse_PTC_Radial_5.1mm"')
    a('\t\t(layer "B.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {f1x} {f1y} {rot})")
    a('\t\t(property "Reference" "F1"')
    a(f"\t\t\t(at 0 -5.2 {rot})")
    a('\t\t\t(layer "B.SilkS")')
    a("\t\t\t(effects (font (size 0.9 0.9) (thickness 0.12)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "PTC_3A_30V"')
    a(f"\t\t\t(at 0 5.2 {rot})")
    a('\t\t\t(layer "B.Fab")')
    a("\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")
    a('\t\t(pad "1" thru_hole rect')
    a("\t\t\t(at -2.55 0)")
    a("\t\t\t(size 1.8 1.8)")
    a("\t\t\t(drill 1.0)")
    a('\t\t\t(layers "*.Cu" "*.Mask")')
    a('\t\t\t(net 57 "+12V_RAW")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(pad "2" thru_hole circle')
    a("\t\t\t(at 2.55 0)")
    a("\t\t\t(size 1.8 1.8)")
    a("\t\t\t(drill 1.0)")
    a('\t\t\t(layers "*.Cu" "*.Mask")')
    a('\t\t\t(net 1 "+12V")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t)")
    d1x, d1y = ox + 26.0, oy + 68.0
    a('\t(footprint "ESP32_Carrier:Diode_TVS_DO41"')
    a('\t\t(layer "B.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {d1x} {d1y} {rot})")
    a('\t\t(property "Reference" "D1"')
    a(f"\t\t\t(at 0 -3.2 {rot})")
    a('\t\t\t(layer "B.SilkS")')
    a("\t\t\t(effects (font (size 0.9 0.9) (thickness 0.12)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "P6KE15A"')
    a(f"\t\t\t(at 0 3.2 {rot})")
    a('\t\t\t(layer "B.Fab")')
    a("\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")
    # pad1 anode -> GND; pad2 cathode band -> +12V (uni TVS)
    a('\t\t(pad "1" thru_hole rect')
    a("\t\t\t(at -3.75 0)")
    a("\t\t\t(size 1.7 1.7)")
    a("\t\t\t(drill 0.9)")
    a('\t\t\t(layers "*.Cu" "*.Mask")')
    a('\t\t\t(net 2 "GND")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(pad "2" thru_hole circle')
    a("\t\t\t(at 3.75 0)")
    a("\t\t\t(size 1.7 1.7)")
    a("\t\t\t(drill 0.9)")
    a('\t\t\t(layers "*.Cu" "*.Mask")')
    a('\t\t\t(net 1 "+12V")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t)")
    gr_text("F1 PTC + D1 TVS", ox + 20, oy + 73.5, "B.SilkS", 0.7)

    # --- U2 MP1584EN BOTTOM ---
    mx, my = ox + 42.0, oy + 58.0
    a('\t(footprint "ESP32_Carrier:MP1584_5V3A"')
    a('\t\t(layer "B.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {mx} {my} {rot})")
    a('\t\t(property "Reference" "U2"')
    a(f'\t\t\t(at 0 {-MINI560_H / 2 - 1.8} {rot})')
    a('\t\t\t(layer "B.SilkS")')
    a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "MP1584_5V3A"')
    a(f'\t\t\t(at 0 {MINI560_H / 2 + 1.8} {rot})')
    a('\t\t\t(layer "B.Fab")')
    a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")
    for layer, w in (("B.CrtYd", 0.05), ("B.Fab", 0.1), ("B.SilkS", 0.12)):
        a("\t\t(fp_rect")
        a(f"\t\t\t(start {-MINI560_W / 2} {-MINI560_H / 2})")
        a(f"\t\t\t(end {MINI560_W / 2} {MINI560_H / 2})")
        a(f"\t\t\t(stroke (width {w}) (type solid))")
        a("\t\t\t(fill none)")
        a(f'\t\t\t(layer "{layer}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
    for num, name, x, y, net_i, net_n in [
        ("1", "VIN+", -hx, -hy, 1, "+12V"),
        ("2", "VIN-", -hx, hy, 2, "GND"),
        ("3", "VOUT+", hx, -hy, 3, "+5V"),
        ("4", "VOUT-", hx, hy, 2, "GND"),
    ]:
        shape = "rect" if num == "1" else "circle"
        a(f'\t\t(pad "{num}" thru_hole {shape}')
        a(f"\t\t\t(at {x} {y})")
        a("\t\t\t(size 2.0 2.0)")
        a("\t\t\t(drill 1.0)")
        a('\t\t\t(layers "*.Cu" "*.Mask")')
        a(f'\t\t\t(net {net_i} "{net_n}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
    a("\t)")

    # --- U8 MP1584EN BOTTOM — blower-only 5V rail ---
    mx8, my8 = ox + 20.0, oy + 95.0
    gr_box(mx8 - 14, my8 - 12, mx8 + 14, my8 + 12, "B.SilkS")
    gr_text("U8 MP1584 +5V_BLW", mx8 - 13, my8 + 14, "B.SilkS", 0.8)
    gr_text("AOD4184 / blower only", mx8 - 13, my8 + 11.5, "B.SilkS", 0.65)
    a('\t(footprint "ESP32_Carrier:MP1584_5V3A"')
    a('\t\t(layer "B.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {mx8} {my8} {rot})")
    a('\t\t(property "Reference" "U8"')
    a(f'\t\t\t(at 0 {-MINI560_H / 2 - 1.8} {rot})')
    a('\t\t\t(layer "B.SilkS")')
    a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "MP1584_BLW"')
    a(f'\t\t\t(at 0 {MINI560_H / 2 + 1.8} {rot})')
    a('\t\t\t(layer "B.Fab")')
    a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")
    for layer, w in (("B.CrtYd", 0.05), ("B.Fab", 0.1), ("B.SilkS", 0.12)):
        a("\t\t(fp_rect")
        a(f"\t\t\t(start {-MINI560_W / 2} {-MINI560_H / 2})")
        a(f"\t\t\t(end {MINI560_W / 2} {MINI560_H / 2})")
        a(f"\t\t\t(stroke (width {w}) (type solid))")
        a("\t\t\t(fill none)")
        a(f'\t\t\t(layer "{layer}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
    for num, name, x, y, net_i, net_n in [
        ("1", "VIN+", -hx, -hy, 1, "+12V"),
        ("2", "VIN-", -hx, hy, 2, "GND"),
        ("3", "VOUT+", hx, -hy, 56, "+5V_BLW"),
        ("4", "VOUT-", hx, hy, 2, "GND"),
    ]:
        shape = "rect" if num == "1" else "circle"
        a(f'\t\t(pad "{num}" thru_hole {shape}')
        a(f"\t\t\t(at {x} {y})")
        a("\t\t\t(size 2.0 2.0)")
        a("\t\t\t(drill 1.0)")
        a('\t\t\t(layers "*.Cu" "*.Mask")')
        a(f'\t\t\t(net {net_i} "{net_n}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
    a("\t)")

    # --- U3 TMC2209 BOTTOM (right of power column, clear of J1 via farm) ---
    tx, ty = ox + 100.0, oy + 95.0
    t_hx = TMC_ROW / 2
    t_y0 = -3.5 * PITCH
    a('\t(footprint "ESP32_Carrier:TMC2209_StepStick"')
    a('\t\t(layer "B.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {tx} {ty} {rot})")
    a('\t\t(property "Reference" "U3"')
    a(f'\t\t\t(at 0 {-TMC_H / 2 - 1.8} {rot})')
    a('\t\t\t(layer "B.SilkS")')
    a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "TMC2209"')
    a(f'\t\t\t(at 0 {TMC_H / 2 + 1.8} {rot})')
    a('\t\t\t(layer "B.Fab")')
    a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")
    for layer, w in (("B.CrtYd", 0.05), ("B.Fab", 0.1), ("B.SilkS", 0.12)):
        a("\t\t(fp_rect")
        a(f"\t\t\t(start {-TMC_W / 2} {-TMC_H / 2})")
        a(f"\t\t\t(end {TMC_W / 2} {TMC_H / 2})")
        a(f"\t\t\t(stroke (width {w}) (type solid))")
        a("\t\t\t(fill none)")
        a(f'\t\t\t(layer "{layer}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
    tmc_ctrl_nets = {
        1: (11, "/EN_TMC"),
        7: (5, "/STEP"),
        8: (6, "/DIR"),
    }
    tmc_pwr_nets = {
        9: (1, "+12V"),
        10: (2, "GND"),
        11: (12, "/MotA2"),
        12: (13, "/MotA1"),
        13: (14, "/MotB1"),
        14: (15, "/MotB2"),
        15: (4, "+3V3"),
        16: (2, "GND"),
    }
    for i in range(8):
        num = i + 1
        y = t_y0 + i * PITCH
        shape = "rect" if i == 0 else "circle"
        a(f'\t\t(pad "{num}" thru_hole {shape}')
        a(f"\t\t\t(at {-t_hx} {y})")
        a("\t\t\t(size 1.7 1.7)")
        a("\t\t\t(drill 1.0)")
        a('\t\t\t(layers "*.Cu" "*.Mask")')
        if num in tmc_ctrl_nets:
            ni, nn = tmc_ctrl_nets[num]
            a(f'\t\t\t(net {ni} "{nn}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
    for i in range(8):
        num = i + 9
        y = t_y0 + i * PITCH
        a(f'\t\t(pad "{num}" thru_hole circle')
        a(f"\t\t\t(at {t_hx} {y})")
        a("\t\t\t(size 1.7 1.7)")
        a("\t\t\t(drill 1.0)")
        a('\t\t\t(layers "*.Cu" "*.Mask")')
        if num in tmc_pwr_nets:
            ni, nn = tmc_pwr_nets[num]
            a(f'\t\t\t(net {ni} "{nn}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
    a("\t)")

    # --- U1 ESP32 BOTTOM ---
    fx, fy = ox + 78.0, oy + 55.0

    def esp_net(name: str):
        # Map silk pin name -> (net_id, net_name)
        m = {
            "GND": (2, "GND"),
            "GNDb": (2, "GND"),
            "GNDc": (2, "GND"),
            "3V3": (4, "+3V3"),
            "3V3b": (4, "+3V3"),
            "5V": (3, "+5V"),
            "IO16": (5, "/STEP"),
            "IO17": (6, "/DIR"),
            "IO18": (11, "/EN_TMC"),
            "IO1": (16, "/OPTO_OUT1"),
            "IO2": (17, "/OPTO_OUT2"),
            "IO4": (18, "/OPTO_OUT3"),
            "IO5": (19, "/OPTO_OUT4"),
            "IO6": (20, "/OPTO_OUT5"),
            "IO7": (21, "/OPTO_OUT6"),
            "IO8": (22, "/OPTO_OUT7"),
            "IO9": (23, "/OPTO_OUT8"),
            "IO10": (40, "/DC1_IN1"),
            "IO11": (41, "/DC1_IN2"),
            "IO12": (42, "/DC2_IN1"),
            "IO13": (43, "/DC2_IN2"),
            "IO14": (44, "/DC3_IN1"),
            "IO15": (45, "/DC3_IN2"),
            "IO39": (47, "/TFT_SCK"),
            "IO40": (48, "/TFT_MOSI"),
            "IO42": (50, "/TFT_CS"),
            "IO21": (51, "/TFT_DC"),
            "IO47": (52, "/I2C_SDA"),
            "IO48": (53, "/I2C_SCL"),
            "IO38": (54, "/BUZZER"),
            "IO3": (55, "/BLOWER"),
            "IO46": (58, "/TFT_RST"),
            "IO45": (59, "/TFT_BL"),
            "IO41": (60, "/TP_INT"),
        }
        return m.get(name)

    a('\t(footprint "ESP32_Carrier:ESP32_S3_DevKitC_44Pin_Socket"')
    a('\t\t(layer "B.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {fx} {fy} {rot})")
    a('\t\t(property "Reference" "U1"')
    a(f"\t\t\t(at 12.7 -10.5 {rot})")
    a('\t\t\t(layer "B.SilkS")')
    a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "ESP32_S3_DevKitC_1"')
    a(f"\t\t\t(at 12.7 {y_last + 5.0} {rot})")
    a('\t\t\t(layer "B.Fab")')
    a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")
    x0, x1 = -1.8, ROW_SPACING + 1.8
    y0e, y1e = -8.0, y_last + 3.0
    for layer, w in (("B.CrtYd", 0.05), ("B.Fab", 0.1), ("B.SilkS", 0.12)):
        a("\t\t(fp_rect")
        a(f"\t\t\t(start {x0} {y0e})")
        a(f"\t\t\t(end {x1} {y1e})")
        a(f"\t\t\t(stroke (width {w}) (type solid))")
        a("\t\t\t(fill none)")
        a(f'\t\t\t(layer "{layer}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
    for num, name, _ in LEFT_PINS:
        y = (num - 1) * PITCH
        shape = "rect" if num == 1 else "circle"
        a(f'\t\t(pad "{num}" thru_hole {shape}')
        a(f"\t\t\t(at 0 {y})")
        a(f"\t\t\t(size {PAD_SIZE} {PAD_SIZE})")
        a(f"\t\t\t(drill {PAD_DRILL})")
        a('\t\t\t(layers "*.Cu" "*.Mask")')
        ni = esp_net(name)
        if ni:
            a(f'\t\t\t(net {ni[0]} "{ni[1]}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
    for num, name, _ in RIGHT_PINS:
        y = (num - 23) * PITCH
        a(f'\t\t(pad "{num}" thru_hole circle')
        a(f"\t\t\t(at {ROW_SPACING} {y})")
        a(f"\t\t\t(size {PAD_SIZE} {PAD_SIZE})")
        a(f"\t\t\t(drill {PAD_DRILL})")
        a('\t\t\t(layers "*.Cu" "*.Mask")')
        ni = esp_net(name)
        if ni:
            a(f'\t\t\t(net {ni[0]} "{ni[1]}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
    a("\t)")

    # --- J2 NEMA17 TOP ---
    j2x, j2y = ox + 15.0, oy + 12.0
    a('\t(footprint "ESP32_Carrier:PinHeader_1x04_Motor"')
    a('\t\t(layer "F.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {j2x} {j2y})")
    a('\t\t(property "Reference" "J2"')
    a("\t\t\t(at 0 -3.8 0)")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "NEMA17_OUT"')
    a(f"\t\t\t(at 0 {3 * PITCH + 3.8} 0)")
    a('\t\t\t(layer "F.Fab")')
    a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")
    span = 3 * PITCH
    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
        a("\t\t(fp_rect")
        a("\t\t\t(start -1.8 -1.8)")
        a(f"\t\t\t(end 1.8 {span + 1.8})")
        a(f"\t\t\t(stroke (width {w}) (type solid))")
        a("\t\t\t(fill none)")
        a(f'\t\t\t(layer "{layer}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
    j2_nets = [(12, "/MotA2"), (13, "/MotA1"), (14, "/MotB1"), (15, "/MotB2")]
    for i, label in enumerate([p[1] for p in MOTOR_HEADER]):
        y = i * PITCH
        a(f'\t\t(fp_text user "{label}"')
        a(f"\t\t\t(at 3.8 {y} 0)")
        a('\t\t\t(layer "F.SilkS")')
        a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.12)) (justify left))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        shape = "rect" if i == 0 else "circle"
        ni, nn = j2_nets[i]
        a(f'\t\t(pad "{i + 1}" thru_hole {shape}')
        a(f"\t\t\t(at 0 {y})")
        a("\t\t\t(size 1.7 1.7)")
        a("\t\t\t(drill 1.0)")
        a('\t\t\t(layers "*.Cu" "*.Mask")')
        a(f'\t\t\t(net {ni} "{nn}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
    a("\t)")

    # --- J17 TFT TOP (12-pin) ---
    j3x, j3y = ox + 48.0, oy + 12.0
    a(f'\t(footprint "ESP32_Carrier:{TFT_FP}"')
    a('\t\t(layer "F.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {j3x} {j3y})")
    a('\t\t(property "Reference" "J17"')
    a("\t\t\t(at 0 -3.8 0)")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "TFT_TOUCH"')
    a(f"\t\t\t(at 0 {(TFT_PINS - 1) * PITCH + 3.8} 0)")
    a('\t\t\t(layer "F.Fab")')
    a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")
    span3 = (TFT_PINS - 1) * PITCH
    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
        a("\t\t(fp_rect")
        a("\t\t\t(start -1.8 -1.8)")
        a(f"\t\t\t(end 1.8 {span3 + 1.8})")
        a(f"\t\t\t(stroke (width {w}) (type solid))")
        a("\t\t\t(fill none)")
        a(f'\t\t\t(layer "{layer}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
    j3_nets = [
        (2, "GND"),
        (4, "+3V3"),
        (47, "/TFT_SCK"),
        (48, "/TFT_MOSI"),
        (50, "/TFT_CS"),
        (51, "/TFT_DC"),
        (58, "/TFT_RST"),
        (59, "/TFT_BL"),
        (52, "/I2C_SDA"),
        (53, "/I2C_SCL"),
        (60, "/TP_INT"),
    ]
    for i, label in enumerate([p[1] for p in TFT_HEADER]):
        y = i * PITCH
        a(f'\t\t(fp_text user "{label}"')
        a(f"\t\t\t(at 3.8 {y} 0)")
        a('\t\t\t(layer "F.SilkS")')
        a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.12)) (justify left))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        shape = "rect" if i == 0 else "circle"
        ni, nn = j3_nets[i]
        a(f'\t\t(pad "{i + 1}" thru_hole {shape}')
        a(f"\t\t\t(at 0 {y})")
        a("\t\t\t(size 1.7 1.7)")
        a("\t\t\t(drill 1.0)")
        a('\t\t\t(layers "*.Cu" "*.Mask")')
        a(f'\t\t\t(net {ni} "{nn}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
    a("\t)")

    # --- J15 Buzzer TOP ---
    j15x, j15y = ox + 75.0, oy + 12.0
    a('\t(footprint "ESP32_Carrier:PinHeader_1x03_Buzzer"')
    a('\t\t(layer "F.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {j15x} {j15y})")
    a('\t\t(property "Reference" "J15"')
    a("\t\t\t(at 0 -3.8 0)")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "BUZZER_5V"')
    a(f"\t\t\t(at 0 {2 * PITCH + 3.8} 0)")
    a('\t\t\t(layer "F.Fab")')
    a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.1)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")
    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
        a("\t\t(fp_rect")
        a("\t\t\t(start -1.8 -1.8)")
        a(f"\t\t\t(end 1.8 {2 * PITCH + 1.8})")
        a(f"\t\t\t(stroke (width {w}) (type solid))")
        a("\t\t\t(fill none)")
        a(f'\t\t\t(layer "{layer}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
    for i, (ni, nn, lab) in enumerate(
        [(3, "+5V", "VCC5"), (2, "GND", "GND"), (54, "/BUZZER", "SIG")]
    ):
        y = i * PITCH
        a(f'\t\t(fp_text user "{lab}"')
        a(f"\t\t\t(at 3.8 {y} 0)")
        a('\t\t\t(layer "F.SilkS")')
        a("\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1)) (justify left))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        shape = "rect" if i == 0 else "circle"
        a(f'\t\t(pad "{i + 1}" thru_hole {shape}')
        a(f"\t\t\t(at 0 {y})")
        a("\t\t\t(size 1.7 1.7)")
        a("\t\t\t(drill 1.0)")
        a('\t\t\t(layers "*.Cu" "*.Mask")')
        a(f'\t\t\t(net {ni} "{nn}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
    a("\t)")

    # --- J16 MOSFET blower TOP ---
    # ox+115: ox+95 put J16 inside the J4 opto-field header (8 pad clashes)
    j16x, j16y = ox + 115.0, oy + 12.0
    a('\t(footprint "ESP32_Carrier:PinHeader_1x04_MOSFET"')
    a('\t\t(layer "F.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {j16x} {j16y})")
    a('\t\t(property "Reference" "J16"')
    a("\t\t\t(at 0 -3.8 0)")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "AOD4184"')
    a(f"\t\t\t(at 0 {3 * PITCH + 3.8} 0)")
    a('\t\t\t(layer "F.Fab")')
    a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.1)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")
    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
        a("\t\t(fp_rect")
        a("\t\t\t(start -1.8 -1.8)")
        a(f"\t\t\t(end 1.8 {3 * PITCH + 1.8})")
        a(f"\t\t\t(stroke (width {w}) (type solid))")
        a("\t\t\t(fill none)")
        a(f'\t\t\t(layer "{layer}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
    for i, (ni, nn, lab) in enumerate(
        [
            (55, "/BLOWER", "PWM"),
            (2, "GND", "GND"),
            (56, "+5V_BLW", "+5V_BLW"),
            (61, "/BLW_RET", "FAN-"),
        ]
    ):
        y = i * PITCH
        a(f'\t\t(fp_text user "{lab}"')
        a(f"\t\t\t(at 3.8 {y} 0)")
        a('\t\t\t(layer "F.SilkS")')
        a("\t\t\t(effects (font (size 0.65 0.65) (thickness 0.1)) (justify left))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        shape = "rect" if i == 0 else "circle"
        a(f'\t\t(pad "{i + 1}" thru_hole {shape}')
        a(f"\t\t\t(at 0 {y})")
        a("\t\t\t(size 1.7 1.7)")
        a("\t\t\t(drill 1.0)")
        a('\t\t\t(layers "*.Cu" "*.Mask")')
        if ni:
            a(f'\t\t\t(net {ni} "{nn}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
    a("\t)")
    gr_text("J16 AOD4184 +5V_BLW", j16x - 8, j16y - 5.5, "F.SilkS", 0.7)

    # Pad world coords (ESP32-S3 DevKitC)
    j1_raw = pad_world(jx, jy, rot, -TB_PITCH / 2, 0)
    j1_12 = pad_world(f1x, f1y, rot, 2.55, 0)  # +12V after F1 PTC (alias for farm/star)
    j1_gnd = pad_world(jx, jy, rot, TB_PITCH / 2, 0)
    f1_in = pad_world(f1x, f1y, rot, -2.55, 0)
    d1_gnd = pad_world(d1x, d1y, rot, -3.75, 0)
    d1_12v = pad_world(d1x, d1y, rot, 3.75, 0)
    u2_vinp = pad_world(mx, my, rot, -hx, -hy)
    u2_ving = pad_world(mx, my, rot, -hx, hy)
    u2_voutp = pad_world(mx, my, rot, hx, -hy)
    u2_voutg = pad_world(mx, my, rot, hx, hy)
    u8_vin = pad_world(mx8, my8, rot, -hx, -hy)
    u8_gnd = pad_world(mx8, my8, rot, -hx, hy)
    u8_out = pad_world(mx8, my8, rot, hx, -hy)
    u8_outg = pad_world(mx8, my8, rot, hx, hy)
    j16_pwm = (j16x, j16y)
    j16_gnd = (j16x, j16y + PITCH)
    j16_5v = (j16x, j16y + 2 * PITCH)

    # 5V = pad 21 left, GND = pad 22 left, 3V3 = pad 1 left
    u1_vin = pad_world(fx, fy, rot, *pad_local(21))
    u1_gnd_r = pad_world(fx, fy, rot, *pad_local(22))
    u1_gnd_l = pad_world(fx, fy, rot, *pad_local(23))
    u1_3v3 = pad_world(fx, fy, rot, *pad_local(1))
    u1_io25 = pad_world(fx, fy, rot, *pad_local(PIN_BY_NAME["IO16"]))
    u1_io26 = pad_world(fx, fy, rot, *pad_local(PIN_BY_NAME["IO17"]))
    u1_io27 = pad_world(fx, fy, rot, *pad_local(PIN_BY_NAME["IO18"]))

    # TMC pads world (rot 180)
    t_en = pad_world(tx, ty, rot, -t_hx, t_y0 + 0 * PITCH)
    t_step = pad_world(tx, ty, rot, -t_hx, t_y0 + 6 * PITCH)
    t_dir = pad_world(tx, ty, rot, -t_hx, t_y0 + 7 * PITCH)
    t_vm = pad_world(tx, ty, rot, t_hx, t_y0 + 0 * PITCH)
    t_gnd = pad_world(tx, ty, rot, t_hx, t_y0 + 1 * PITCH)
    t_a2 = pad_world(tx, ty, rot, t_hx, t_y0 + 2 * PITCH)
    t_a1 = pad_world(tx, ty, rot, t_hx, t_y0 + 3 * PITCH)
    t_b1 = pad_world(tx, ty, rot, t_hx, t_y0 + 4 * PITCH)
    t_b2 = pad_world(tx, ty, rot, t_hx, t_y0 + 5 * PITCH)
    t_vio = pad_world(tx, ty, rot, t_hx, t_y0 + 6 * PITCH)
    t_gnd2 = pad_world(tx, ty, rot, t_hx, t_y0 + 7 * PITCH)

    j2_a2 = (j2x, j2y)
    j2_a1 = (j2x, j2y + PITCH)
    j2_b1 = (j2x, j2y + 2 * PITCH)
    j2_b2 = (j2x, j2y + 3 * PITCH)
    j3_gnd = (j3x, j3y)
    j3_3v3 = (j3x, j3y + PITCH)

    # === +12V 3A via farm: AFTER F1 PTC (not raw J1) ===
    # J1 RAW -> F1 -> +12V farm; D1 TVS on +12V
    track(j1_raw[0], j1_raw[1], f1_in[0], f1_in[1], 57, "B.Cu", 1.5)
    track(d1_12v[0], d1_12v[1], j1_12[0], d1_12v[1], 1, "B.Cu", 0.8)
    track(j1_12[0], d1_12v[1], j1_12[0], j1_12[1], 1, "B.Cu", 0.8)
    track(d1_gnd[0], d1_gnd[1], j1_gnd[0], d1_gnd[1], 2, "B.Cu", 0.8)
    track(j1_gnd[0], d1_gnd[1], j1_gnd[0], j1_gnd[1], 2, "B.Cu", 0.8)

    farm_cx = j1_12[0] + 6.0
    farm_cy = j1_12[1] - 6.0
    gr_text("+12V VIA 3A", farm_cx - 3, farm_cy - 4, "F.SilkS", 0.7)
    gr_text("+12V VIA 3A", farm_cx - 3, farm_cy - 4, "B.SilkS", 0.7)
    for ix in range(VIA12_COUNT_X):
        for iy in range(VIA12_COUNT_Y):
            vx = farm_cx + (ix - 1) * VIA12_PITCH
            vy = farm_cy + (iy - 0.5) * VIA12_PITCH
            via(vx, vy, 1)
    pw = 1.5
    # Stitch F1 out <-> farm on both layers
    track(j1_12[0], j1_12[1], j1_12[0], farm_cy, 1, "B.Cu", pw)
    track(j1_12[0], farm_cy, farm_cx, farm_cy, 1, "B.Cu", pw)
    track(j1_12[0], j1_12[1], j1_12[0], farm_cy, 1, "F.Cu", pw)
    track(j1_12[0], farm_cy, farm_cx, farm_cy, 1, "F.Cu", pw)
    track(farm_cx - VIA12_PITCH, farm_cy, farm_cx + VIA12_PITCH, farm_cy, 1, "F.Cu", pw)
    track(farm_cx - VIA12_PITCH, farm_cy, farm_cx + VIA12_PITCH, farm_cy, 1, "B.Cu", pw)

    # +12V B.Cu bus ABOVE modules (clear of MP1584 pad column)
    y12 = min(u2_vinp[1], t_vm[1], farm_cy) - 4.0
    x12_bus = farm_cx
    track(farm_cx, farm_cy, x12_bus, y12, 1, "B.Cu", pw)
    # Approach MP1584 VIN+ from ABOVE (not along pad column shared with GND)
    track(x12_bus, y12, u2_vinp[0], y12, 1, "B.Cu", pw)
    track(u2_vinp[0], y12, u2_vinp[0], u2_vinp[1], 1, "B.Cu", pw)
    # TMC VM
    track(x12_bus, y12, t_vm[0], y12, 1, "B.Cu", pw)
    track(t_vm[0], y12, t_vm[0], t_vm[1], 1, "B.Cu", pw)
    # F.Cu stub for top-layer current share
    track(farm_cx, farm_cy, farm_cx, farm_cy - 4, 1, "F.Cu", pw)

    # GND: leave J1 downward, clear of +12V farm; approach MP1584 GND from BELOW
    yg = max(j1_gnd[1], u2_ving[1], u2_voutg[1], t_gnd[1]) + 8.0
    track(j1_gnd[0], j1_gnd[1], j1_gnd[0], yg, 2, "B.Cu", pw)
    track(j1_gnd[0], yg, u2_ving[0] - 4.0, yg, 2, "B.Cu", pw)
    track(u2_ving[0] - 4.0, yg, u2_ving[0] - 4.0, u2_ving[1], 2, "B.Cu", pw)
    track(u2_ving[0] - 4.0, u2_ving[1], u2_ving[0], u2_ving[1], 2, "B.Cu", pw)
    track(u2_ving[0] - 4.0, yg, u2_voutg[0] + 4.0, yg, 2, "B.Cu", pw)
    track(u2_voutg[0] + 4.0, yg, u2_voutg[0] + 4.0, u2_voutg[1], 2, "B.Cu", pw)
    track(u2_voutg[0] + 4.0, u2_voutg[1], u2_voutg[0], u2_voutg[1], 2, "B.Cu", pw)
    track(u2_voutg[0] + 4.0, yg, t_gnd[0], yg, 2, "B.Cu", pw)
    track(t_gnd[0], yg, t_gnd[0], t_gnd[1], 2, "B.Cu", pw)
    track(t_gnd2[0], t_gnd2[1], t_gnd2[0], yg, 2, "B.Cu", pw)
    xg = 58.0
    track(u2_voutg[0] + 4.0, yg, xg, yg, 2, "B.Cu", pw)
    track(xg, yg, xg, u1_gnd_r[1], 2, "B.Cu", pw)
    track(xg, u1_gnd_r[1], u1_gnd_r[0], u1_gnd_r[1], 2, "B.Cu", pw)
    track(xg, u1_gnd_r[1], xg, u1_gnd_l[1], 2, "B.Cu", pw)
    track(xg, u1_gnd_l[1], u1_gnd_l[0], u1_gnd_l[1], 2, "B.Cu", pw)
    # GND vias west of J1 GND (away from +12V)
    for i in range(4):
        via(j1_gnd[0] - 5.0 - i * 1.8, j1_gnd[1], 2)
        track(j1_gnd[0], j1_gnd[1], j1_gnd[0] - 5.0 - i * 1.8, j1_gnd[1], 2, "B.Cu", 1.0)

    # +5V B.Cu MP1584 -> ESP32 5V (outside pad columns)
    y5 = min(u2_voutp[1], u1_vin[1]) - 6.0
    track(u2_voutp[0], u2_voutp[1], u2_voutp[0] + 6, u2_voutp[1], 3, "B.Cu", 1.0)
    track(u2_voutp[0] + 6, u2_voutp[1], u2_voutp[0] + 6, y5, 3, "B.Cu", 1.0)
    track(u2_voutp[0] + 6, y5, u1_vin[0] - 6, y5, 3, "B.Cu", 1.0)
    track(u1_vin[0] - 6, y5, u1_vin[0] - 6, u1_vin[1], 3, "B.Cu", 1.0)
    track(u1_vin[0] - 6, u1_vin[1], u1_vin[0], u1_vin[1], 3, "B.Cu", 1.0)

    # U8 MP1584 blower: +12V/GND from U2 rail; +5V_BLW -> J16 pin3
    track(u2_vinp[0], u2_vinp[1], u2_vinp[0], u8_vin[1], 1, "B.Cu", 1.0)
    track(u2_vinp[0], u8_vin[1], u8_vin[0], u8_vin[1], 1, "B.Cu", 1.0)
    track(u2_ving[0], u2_ving[1], u2_ving[0], u8_gnd[1], 2, "B.Cu", 1.0)
    track(u2_ving[0], u8_gnd[1], u8_gnd[0], u8_gnd[1], 2, "B.Cu", 1.0)
    track(u8_outg[0], u8_outg[1], u8_outg[0], yg, 2, "B.Cu", 0.8)
    track(u8_outg[0], yg, u2_voutg[0] + 4.0, yg, 2, "B.Cu", 0.8)
    yblw = u8_out[1] - 3.0
    track(u8_out[0], u8_out[1], u8_out[0], yblw, 56, "B.Cu", 1.0)
    track(u8_out[0], yblw, j16_5v[0] - 3.0, yblw, 56, "B.Cu", 1.0)
    via(j16_5v[0] - 3.0, yblw, 56, 0.5, 1.0)
    track(j16_5v[0] - 3.0, yblw, j16_5v[0] - 3.0, j16_5v[1], 56, "F.Cu", 0.8)
    track(j16_5v[0] - 3.0, j16_5v[1], j16_5v[0], j16_5v[1], 56, "F.Cu", 0.8)
    track(j16_gnd[0], j16_gnd[1], j16_gnd[0] - 4.0, j16_gnd[1], 2, "F.Cu", 0.5)
    via(j16_gnd[0] - 4.0, j16_gnd[1], 2, 0.4, 0.8)

    # +3V3 B.Cu ESP32 -> TMC VIO; F.Cu to J3
    track(u1_3v3[0], u1_3v3[1], u1_3v3[0], t_vio[1], 4, "B.Cu", 0.5)
    track(u1_3v3[0], t_vio[1], t_vio[0], t_vio[1], 4, "B.Cu", 0.5)
    track(u1_3v3[0], u1_3v3[1], u1_3v3[0], 38.0, 4, "F.Cu", 0.35)
    track(u1_3v3[0], 38.0, j3_3v3[0], 38.0, 4, "F.Cu", 0.35)
    track(j3_3v3[0], 38.0, j3_3v3[0], j3_3v3[1], 4, "F.Cu", 0.35)

    # Motor phases: TMC (right) -> top edge bus -> J2 (left) — wide spacing
    mw = 1.0
    for net_i, src, dst, ylane in [
        (12, t_a2, j2_a2, 36.0),
        (13, t_a1, j2_a1, 37.5),
        (14, t_b1, j2_b1, 39.0),
        (15, t_b2, j2_b2, 40.5),
    ]:
        track(src[0], src[1], src[0], ylane, net_i, "F.Cu", mw)
        track(src[0], ylane, dst[0], ylane, net_i, "F.Cu", mw)
        track(dst[0], ylane, dst[0], dst[1], net_i, "F.Cu", mw)

    # Control B.Cu ESP32 -> TMC (east of ESP32)
    def route_sig(net_i, src, dst, xlane):
        track(src[0], src[1], xlane, src[1], net_i, "B.Cu", 0.35)
        track(xlane, src[1], xlane, dst[1], net_i, "B.Cu", 0.35)
        track(xlane, dst[1], dst[0], dst[1], net_i, "B.Cu", 0.35)

    route_sig(5, u1_io25, t_step, ox + bw - 4)
    route_sig(6, u1_io26, t_dir, ox + bw - 6)
    route_sig(11, u1_io27, t_en, ox + bw - 8)

    # J17 TFT / J15 buzzer / J16 MOSFET — power + signals (coarse auto-route)
    track(u1_gnd_l[0], u1_gnd_l[1], u1_gnd_l[0], 40.5, 2, "F.Cu", 0.35)
    track(u1_gnd_l[0], 40.5, j3_gnd[0], 40.5, 2, "F.Cu", 0.35)
    track(j3_gnd[0], 40.5, j3_gnd[0], j3_gnd[1], 2, "F.Cu", 0.35)
    tft_sigs = [
        (47, "IO39", 2),
        (48, "IO40", 3),
        (49, "IO41", 4),
        (50, "IO42", 5),
        (51, "IO21", 6),
        (52, "IO47", 7),
        (53, "IO48", 8),
    ]
    for ni, gname, pin_i in tft_sigs:
        src = pad_world(fx, fy, rot, *pad_local(PIN_BY_NAME[gname]))
        dst = (j3x, j3y + pin_i * PITCH)
        xl = ox + 8 + pin_i * 1.2
        track(src[0], src[1], xl, src[1], ni, "B.Cu", 0.3)
        track(xl, src[1], xl, dst[1], ni, "B.Cu", 0.3)
        via(xl, dst[1], ni, 0.4, 0.8)
        track(xl, dst[1], dst[0], dst[1], ni, "F.Cu", 0.3)
    # Buzzer SIG
    bz = pad_world(fx, fy, rot, *pad_local(PIN_BY_NAME["IO38"]))
    track(bz[0], bz[1], j15x - 2, bz[1], 54, "B.Cu", 0.3)
    via(j15x - 2, j15y + 2 * PITCH, 54, 0.4, 0.8)
    track(j15x - 2, j15y + 2 * PITCH, j15x, j15y + 2 * PITCH, 54, "F.Cu", 0.3)
    # MOSFET SIG
    bl = pad_world(fx, fy, rot, *pad_local(PIN_BY_NAME["IO3"]))
    track(bl[0], bl[1], j16x - 2, bl[1], 55, "B.Cu", 0.3)
    via(j16x - 2, j16y, 55, 0.4, 0.8)
    track(j16x - 2, j16y, j16x, j16y, 55, "F.Cu", 0.3)

    # ===== U4 + U9 PC817 4CH x2 BOTTOM + J4 TOP field =====
    rot4 = BOTTOM_ROT
    xs4 = [(i - 2.5) * PITCH for i in range(6)]
    hx4 = PC817_4CH_ROW / 2
    # U4 = ch1-4 (limits), U9 = ch5-8 (limits+BUP+spare)
    u4_at = (ox + 42.0, oy + 130.0)
    u9_at = (ox + 98.0, oy + 130.0)

    def _emit_pc817_4ch(ref: str, atxy: tuple[float, float], in_nets: list, out_nets: list):
        ax, ay = atxy
        gr_box(
            ax - PC817_4CH_W / 2 - 1,
            ay - PC817_4CH_H / 2 - 1,
            ax + PC817_4CH_W / 2 + 1,
            ay + PC817_4CH_H / 2 + 1,
            "B.SilkS",
        )
        gr_text(f"{ref} PC817 4CH", ax - 20, ay + PC817_4CH_H / 2 + 3.5, "B.SilkS", 0.75)
        a('\t(footprint "ESP32_Carrier:PC817_4CH_Opto"')
        a('\t\t(layer "B.Cu")')
        a(f'\t\t(uuid "{uid()}")')
        a(f"\t\t(at {ax} {ay} {rot4})")
        a(f'\t\t(property "Reference" "{ref}"')
        a(f'\t\t\t(at 0 {-PC817_4CH_H / 2 - 1.8} {rot4})')
        a('\t\t\t(layer "B.SilkS")')
        a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a('\t\t(property "Value" "PC817_4CH"')
        a(f'\t\t\t(at 0 {PC817_4CH_H / 2 + 1.8} {rot4})')
        a('\t\t\t(layer "B.Fab")')
        a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.1)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a("\t\t(attr through_hole)")
        for layer, w in (("B.CrtYd", 0.05), ("B.Fab", 0.1), ("B.SilkS", 0.12)):
            a("\t\t(fp_rect")
            a(f"\t\t\t(start {-PC817_4CH_W / 2} {-PC817_4CH_H / 2})")
            a(f"\t\t\t(end {PC817_4CH_W / 2} {PC817_4CH_H / 2})")
            a(f"\t\t\t(stroke (width {w}) (type solid))")
            a("\t\t\t(fill none)")
            a(f'\t\t\t(layer "{layer}")')
            a(f'\t\t\t(uuid "{uid()}")')
            a("\t\t)")
        for i, (ni, nn) in enumerate(in_nets):
            shape = "rect" if i == 0 else "circle"
            a(f'\t\t(pad "{i + 1}" thru_hole {shape}')
            a(f"\t\t\t(at {xs4[i]} {-hx4})")
            a("\t\t\t(size 1.7 1.7)")
            a("\t\t\t(drill 1.0)")
            a('\t\t\t(layers "*.Cu" "*.Mask")')
            a(f'\t\t\t(net {ni} "{nn}")')
            a(f'\t\t\t(uuid "{uid()}")')
            a("\t\t)")
        for i, (ni, nn) in enumerate(out_nets):
            a(f'\t\t(pad "{i + 7}" thru_hole circle')
            a(f"\t\t\t(at {xs4[i]} {hx4})")
            a("\t\t\t(size 1.7 1.7)")
            a("\t\t\t(drill 1.0)")
            a('\t\t\t(layers "*.Cu" "*.Mask")')
            a(f'\t\t\t(net {ni} "{nn}")')
            a(f'\t\t\t(uuid "{uid()}")')
            a("\t\t)")
        a("\t)")

    in_nets_all = [
        (2, "GND"),
        (24, "/OPTO_VCC_I"),
        (25, "/OPTO_IN1"),
        (26, "/OPTO_IN2"),
        (27, "/OPTO_IN3"),
        (28, "/OPTO_IN4"),
        (29, "/OPTO_IN5"),
        (30, "/OPTO_IN6"),
        (31, "/OPTO_IN7"),
        (32, "/OPTO_IN8"),
    ]
    _emit_pc817_4ch(
        "U4",
        u4_at,
        in_nets_all[:6],
        [
            (2, "GND"),
            (4, "+3V3"),
            (16, "/OPTO_OUT1"),
            (17, "/OPTO_OUT2"),
            (18, "/OPTO_OUT3"),
            (19, "/OPTO_OUT4"),
        ],
    )
    _emit_pc817_4ch(
        "U9",
        u9_at,
        [
            (2, "GND"),
            (24, "/OPTO_VCC_I"),
            (29, "/OPTO_IN5"),
            (30, "/OPTO_IN6"),
            (31, "/OPTO_IN7"),
            (32, "/OPTO_IN8"),
        ],
        [
            (2, "GND"),
            (4, "+3V3"),
            (20, "/OPTO_OUT5"),
            (21, "/OPTO_OUT6"),
            (22, "/OPTO_OUT7"),
            (23, "/OPTO_OUT8"),
        ],
    )
    gr_text("2x PC817 4CH | OUT=MCU  IN=J4 field", ox + 35, oy + 152, "B.SilkS", 0.7)

    j4x, j4y = ox + 95.0, oy + 8.0
    gr_box(j4x - 3, j4y - 3, j4x + 6, j4y + 9 * PITCH + 3, "F.SilkS")
    gr_text("J4 OPTO FIELD IN", j4x + 8, j4y - 1.5, "F.SilkS", 0.85)
    gr_text("IN1-6=lim; IN7=BUP30S; IN8 free", j4x + 8, j4y + 1.2, "F.SilkS", 0.65)
    a('\t(footprint "ESP32_Carrier:PinHeader_1x10_OptoField"')
    a('\t\t(layer "F.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {j4x} {j4y})")
    a('\t\t(property "Reference" "J4"')
    a("\t\t\t(at 0 -3.8 0)")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "OPTO_FIELD_IN"')
    a(f"\t\t\t(at 0 {9 * PITCH + 3.8} 0)")
    a('\t\t\t(layer "F.Fab")')
    a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")
    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
        a("\t\t(fp_rect")
        a("\t\t\t(start -1.8 -1.8)")
        a(f"\t\t\t(end 1.8 {9 * PITCH + 1.8})")
        a(f"\t\t\t(stroke (width {w}) (type solid))")
        a("\t\t\t(fill none)")
        a(f'\t\t\t(layer "{layer}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
    for i, (ni, nn) in enumerate(in_nets_all):
        y = i * PITCH
        lab = OPTO_FIELD_HEADER[i][1]
        a(f'\t\t(fp_text user "{lab}"')
        a(f"\t\t\t(at 3.8 {y} 0)")
        a('\t\t\t(layer "F.SilkS")')
        a("\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1)) (justify left))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        shape = "rect" if i == 0 else "circle"
        a(f'\t\t(pad "{i + 1}" thru_hole {shape}')
        a(f"\t\t\t(at 0 {y})")
        a("\t\t\t(size 1.7 1.7)")
        a("\t\t\t(drill 1.0)")
        a('\t\t\t(layers "*.Cu" "*.Mask")')
        a(f'\t\t\t(net {ni} "{nn}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
    a("\t)")

    # Field routes: J4.1-6 -> U4 IN; J4.1-2 + J4.7-10 -> U9
    def _opto_in_pad(atxy, local_i):
        return pad_world(atxy[0], atxy[1], rot4, xs4[local_i], -hx4)

    def _opto_out_pad(atxy, local_i):
        return pad_world(atxy[0], atxy[1], rot4, xs4[local_i], hx4)

    for i in range(6):
        jpt = (j4x, j4y + i * PITCH)
        upt = _opto_in_pad(u4_at, i)
        ni = in_nets_all[i][0]
        xlane = ox + bw - 2.5 - i * 1.0
        track(jpt[0], jpt[1], xlane, jpt[1], ni, "F.Cu", 0.3)
        track(xlane, jpt[1], xlane, upt[1], ni, "F.Cu", 0.3)
        track(xlane, upt[1], upt[0], upt[1], ni, "F.Cu", 0.3)
    # Share GND/VCC_I to U9
    for i in (0, 1):
        a_pt = _opto_in_pad(u4_at, i)
        b_pt = _opto_in_pad(u9_at, i)
        ni = in_nets_all[i][0]
        track(a_pt[0], a_pt[1], b_pt[0], a_pt[1], ni, "B.Cu", 0.4)
        track(b_pt[0], a_pt[1], b_pt[0], b_pt[1], ni, "B.Cu", 0.4)
    for i, j_i in enumerate(range(6, 10)):
        jpt = (j4x, j4y + j_i * PITCH)
        upt = _opto_in_pad(u9_at, i + 2)
        ni = in_nets_all[j_i][0]
        xlane = ox + bw - 8.5 - i * 1.0
        track(jpt[0], jpt[1], xlane, jpt[1], ni, "F.Cu", 0.3)
        track(xlane, jpt[1], xlane, upt[1], ni, "F.Cu", 0.3)
        track(xlane, upt[1], upt[0], upt[1], ni, "F.Cu", 0.3)

    # MCU OUT -> ESP32
    gpio_local = {
        1: (25.4, 7.62),
        2: (25.4, 10.16),
        4: (0.0, 7.62),
        5: (0.0, 10.16),
        6: (0.0, 12.7),
        7: (0.0, 15.24),
        8: (0.0, 27.94),
        9: (0.0, 35.56),
    }
    out_map = [
        (u4_at, 2, 16, 1),
        (u4_at, 3, 17, 2),
        (u4_at, 4, 18, 4),
        (u4_at, 5, 19, 5),
        (u9_at, 2, 20, 6),
        (u9_at, 3, 21, 7),
        (u9_at, 4, 22, 8),
        (u9_at, 5, 23, 9),
    ]
    for i, (atxy, pad_i, ni, gpio) in enumerate(out_map):
        src = _opto_out_pad(atxy, pad_i)
        lx, ly = gpio_local[gpio]
        dst = pad_world(fx, fy, rot, lx, ly)
        xlane = ox + 6 + i * 1.4
        track(src[0], src[1], xlane, src[1], ni, "B.Cu", 0.3)
        track(xlane, src[1], xlane, dst[1], ni, "B.Cu", 0.3)
        track(xlane, dst[1], dst[0], dst[1], ni, "B.Cu", 0.3)

    # VCC_O / GND_O stitch
    for atxy in (u4_at, u9_at):
        vccio = _opto_out_pad(atxy, 1)
        gndo = _opto_out_pad(atxy, 0)
        track(vccio[0], vccio[1], u1_3v3[0], vccio[1], 4, "B.Cu", 0.5)
        track(u1_3v3[0], vccio[1], u1_3v3[0], u1_3v3[1], 4, "B.Cu", 0.5)
        track(gndo[0], gndo[1], u1_gnd_l[0], gndo[1], 2, "B.Cu", 0.5)
        track(u1_gnd_l[0], gndo[1], u1_gnd_l[0], u1_gnd_l[1], 2, "B.Cu", 0.5)

    # --- 3x DRV8871 BOTTOM + 3x GA12-N20 TOP ---
    # Pad locals: Vs(-8,-16) GND(0,-16) 5V(8,-16) ENA(-18,-6) IN1(-18,0) IN2(-18,6) OUT1(18,-4) OUT2(18,4)
    l298n_pcb = [
        # (U, Jmot, Jmin, Jmax, ux, uy, jx, jy, ni1, ni2, nma, nmb, g1, g2, nmin, nmax)
        # opto nets IN1=25 .. IN6=30
        # xj ox+56: ox+70 put J8 on U1's right pad column.
        # yu oy+65: oy+50 put U5 under the J7/J13 header row.
        ("U5", "J5", "J8", "J9", ox + 148.0, oy + 65.0, ox + 56.0, oy + 42.0, 40, 41, 34, 35, "IO10", "IO11", 25, 26),
        ("U6", "J6", "J10", "J11", ox + 148.0, oy + 100.0, ox + 105.0, oy + 42.0, 42, 43, 36, 37, "IO12", "IO13", 27, 28),
        ("U7", "J7", "J12", "J13", ox + 148.0, oy + 150.0, ox + 140.0, oy + 42.0, 44, 45, 38, 39, "IO14", "IO15", 29, 30),
    ]
    esp_gpio_local = {
        "IO10": (0.0, 38.1),
        "IO11": (0.0, 40.64),
        "IO12": (0.0, 43.18),
        "IO13": (0.0, 45.72),
        "IO14": (0.0, 48.26),
        "IO15": (0.0, 17.78),
    }

    def _hdr_1x2(fp, ref, val, atx, aty, pads):
        a(f'\t(footprint "ESP32_Carrier:{fp}"')
        a('\t\t(layer "F.Cu")')
        a(f'\t\t(uuid "{uid()}")')
        a(f"\t\t(at {atx} {aty})")
        a(f'\t\t(property "Reference" "{ref}"')
        a("\t\t\t(at 0 -3.8 0)")
        a('\t\t\t(layer "F.SilkS")')
        a("\t\t\t(effects (font (size 0.9 0.9) (thickness 0.12)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a(f'\t\t(property "Value" "{val}"')
        a(f"\t\t\t(at 0 {PITCH + 3.8} 0)")
        a('\t\t\t(layer "F.Fab")')
        a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.1)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a("\t\t(attr through_hole)")
        for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
            a("\t\t(fp_rect")
            a("\t\t\t(start -1.8 -1.8)")
            a(f"\t\t\t(end 1.8 {PITCH + 1.8})")
            a(f"\t\t\t(stroke (width {w}) (type solid))")
            a("\t\t\t(fill none)")
            a(f'\t\t\t(layer "{layer}")')
            a(f'\t\t\t(uuid "{uid()}")')
            a("\t\t)")
        for pi, (neti, netn, lab) in enumerate(pads):
            y = pi * PITCH
            a(f'\t\t(fp_text user "{lab}"')
            a(f"\t\t\t(at 3.2 {y} 0)")
            a('\t\t\t(layer "F.SilkS")')
            a("\t\t\t(effects (font (size 0.65 0.65) (thickness 0.1)) (justify left))")
            a(f'\t\t\t(uuid "{uid()}")')
            a("\t\t)")
            shape = "rect" if pi == 0 else "circle"
            a(f'\t\t(pad "{pi + 1}" thru_hole {shape}')
            a(f"\t\t\t(at 0 {y})")
            a("\t\t\t(size 1.7 1.7)")
            a("\t\t\t(drill 1.0)")
            a('\t\t\t(layers "*.Cu" "*.Mask")')
            a(f'\t\t\t(net {neti} "{netn}")')
            a(f'\t\t\t(uuid "{uid()}")')
            a("\t\t)")
        a("\t)")

    for mi, (uref, jref, jmin, jmax, ux, uy, jx, jy, ni1, ni2, nma, nmb, g1, g2, nmin, nmax) in enumerate(l298n_pcb):
        gr_box(ux - 22, uy - 22, ux + 22, uy + 22, "B.SilkS")
        gr_text(f"{uref} DRV8871 GA12", ux - 20, uy + 24, "B.SilkS", 0.85)
        gr_text("VM=12V", ux - 14, uy + 14, "B.SilkS", 0.7)
        a('\t(footprint "ESP32_Carrier:DRV8871_Module"')
        a('\t\t(layer "B.Cu")')
        a(f'\t\t(uuid "{uid()}")')
        a(f"\t\t(at {ux} {uy} {rot})")
        a(f'\t\t(property "Reference" "{uref}"')
        a(f"\t\t\t(at 0 {-L298N_H / 2 - 1.8} {rot})")
        a('\t\t\t(layer "B.SilkS")')
        a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a('\t\t(property "Value" "DRV8871_Module"')
        a(f"\t\t\t(at 0 {L298N_H / 2 + 1.8} {rot})")
        a('\t\t\t(layer "B.Fab")')
        a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a("\t\t(attr through_hole)")
        for layer, w in (("B.CrtYd", 0.05), ("B.Fab", 0.1), ("B.SilkS", 0.12)):
            a("\t\t(fp_rect")
            a(f"\t\t\t(start {-L298N_W / 2} {-L298N_H / 2})")
            a(f"\t\t\t(end {L298N_W / 2} {L298N_H / 2})")
            a(f"\t\t\t(stroke (width {w}) (type solid))")
            a("\t\t\t(fill none)")
            a(f'\t\t\t(layer "{layer}")')
            a(f'\t\t\t(uuid "{uid()}")')
            a("\t\t)")
        l298_pads = [
            ("1", -8.0, -8.0, 1, "+12V"),
            ("2", 0.0, -8.0, 2, "GND"),
            ("3", -10.0, 0.0, ni1, f"/DC{mi + 1}_IN1"),
            ("4", -10.0, 6.0, ni2, f"/DC{mi + 1}_IN2"),
            ("5", 10.0, -4.0, nma, f"/MotDC{mi + 1}_A"),
            ("6", 10.0, 4.0, nmb, f"/MotDC{mi + 1}_B"),
        ]
        for i, (num, lx, ly, neti, netn) in enumerate(l298_pads):
            shape = "rect" if i == 0 else "circle"
            a(f'\t\t(pad "{num}" thru_hole {shape}')
            a(f"\t\t\t(at {lx} {ly})")
            a("\t\t\t(size 2.0 2.0)")
            a("\t\t\t(drill 1.1)")
            a('\t\t\t(layers "*.Cu" "*.Mask")')
            if neti:
                a(f'\t\t\t(net {neti} "{netn}")')
            a(f'\t\t\t(uuid "{uid()}")')
            a("\t\t)")
        a("\t)")

        # TOP group: MOT + LIM_MIN + LIM_MAX (NC @12V -> opto)
        jx_min, jx_max = jx + 8.0, jx + 16.0
        gr_box(jx - 4, jy - 5, jx_max + 6, jy + PITCH + 5, "F.SilkS")
        gr_text(f"TRUC{mi + 1} MOT+LIM NC", jx - 3, jy - 6.5, "F.SilkS", 0.85)
        gr_text(f"{jref} MOT  {jmin} MIN  {jmax} MAX", jx - 3, jy + PITCH + 6.5, "F.SilkS", 0.7)
        _hdr_1x2(
            "PinHeader_1x02_MotorDC",
            jref,
            "GA12_N20",
            jx,
            jy,
            [(nma, f"/MotDC{mi + 1}_A", "M+"), (nmb, f"/MotDC{mi + 1}_B", "M-")],
        )
        _hdr_1x2(
            "PinHeader_1x02_LimitSW",
            jmin,
            "LIM_MIN_NC",
            jx_min,
            jy,
            [(46, "+12V_SNS", "+12S"), (nmin, f"/OPTO_IN{2 * mi + 1}", "SW")],
        )
        _hdr_1x2(
            "PinHeader_1x02_LimitSW",
            jmax,
            "LIM_MAX_NC",
            jx_max,
            jy,
            [(46, "+12V_SNS", "+12S"), (nmax, f"/OPTO_IN{2 * mi + 2}", "SW")],
        )

        p_vs = pad_world(ux, uy, rot, -8.0, -8.0)
        p_gnd = pad_world(ux, uy, rot, 0.0, -8.0)
        p_in1 = pad_world(ux, uy, rot, -10.0, 0.0)
        p_in2 = pad_world(ux, uy, rot, -10.0, 6.0)
        p_o1 = pad_world(ux, uy, rot, 10.0, -4.0)
        p_o2 = pad_world(ux, uy, rot, 10.0, 4.0)
        track(p_vs[0], p_vs[1], t_vm[0], p_vs[1], 1, "B.Cu", 2.5)
        track(t_vm[0], p_vs[1], t_vm[0], t_vm[1], 1, "B.Cu", 2.5)
        track(p_gnd[0], p_gnd[1], u1_gnd_l[0], p_gnd[1], 2, "B.Cu", 2.5)
        track(u1_gnd_l[0], p_gnd[1], u1_gnd_l[0], u1_gnd_l[1], 2, "B.Cu", 2.5)
        lx1, ly1 = esp_gpio_local[g1]
        lx2, ly2 = esp_gpio_local[g2]
        e1 = pad_world(fx, fy, rot, lx1, ly1)
        e2 = pad_world(fx, fy, rot, lx2, ly2)
        xlane = ox + 110 + mi * 2.0
        track(e1[0], e1[1], xlane, e1[1], ni1, "B.Cu", 0.3)
        track(xlane, e1[1], xlane, p_in1[1], ni1, "B.Cu", 0.3)
        track(xlane, p_in1[1], p_in1[0], p_in1[1], ni1, "B.Cu", 0.3)
        xlane2 = ox + 112 + mi * 2.0
        track(e2[0], e2[1], xlane2, e2[1], ni2, "B.Cu", 0.3)
        track(xlane2, e2[1], xlane2, p_in2[1], ni2, "B.Cu", 0.3)
        track(xlane2, p_in2[1], p_in2[0], p_in2[1], ni2, "B.Cu", 0.3)
        via(p_o1[0], p_o1[1], nma, 0.4, 0.8)
        via(p_o2[0], p_o2[1], nmb, 0.4, 0.8)
        jmp = (jx, jy)
        jmm = (jx, jy + PITCH)
        track(p_o1[0], p_o1[1], jmp[0], p_o1[1], nma, "F.Cu", 0.6)
        track(jmp[0], p_o1[1], jmp[0], jmp[1], nma, "F.Cu", 0.6)
        track(p_o2[0], p_o2[1], jmm[0] + 2.0, p_o2[1], nmb, "F.Cu", 0.6)
        track(jmm[0] + 2.0, p_o2[1], jmm[0] + 2.0, jmm[1], nmb, "F.Cu", 0.6)
        track(jmm[0] + 2.0, jmm[1], jmm[0], jmm[1], nmb, "F.Cu", 0.6)
        for atx, neti, ch in [(jx_min, nmin, 2 * mi), (jx_max, nmax, 2 * mi + 1)]:
            p12 = (atx, jy)
            psw = (atx, jy + PITCH)
            pass  # +12V_SNS fed from star SNS rail below
            if ch < 4:
                upt = _opto_in_pad(u4_at, ch + 2)
            else:
                upt = _opto_in_pad(u9_at, (ch - 4) + 2)
            via(psw[0], psw[1], neti, 0.4, 0.8)
            xl = ox + bw - 4.0 - ch * 1.2
            track(psw[0], psw[1], xl, psw[1], neti, "F.Cu", 0.35)
            track(xl, psw[1], xl, upt[1], neti, "F.Cu", 0.35)
            track(xl, upt[1], upt[0], upt[1], neti, "F.Cu", 0.35)



    # --- J14 BUP-30S + R1 4k7 pull-up (TOP) ---
    # ox+4: ox+8 overlapped the J1 terminal block
    j14x, j14y = ox + 4.0, oy + 55.0
    # y +3.2*PITCH: at 1.5*PITCH R1 straddled both J1 and F1
    r1x, r1y = j14x + 16.0, j14y + 3.2 * PITCH
    gr_box(j14x - 3, j14y - 5, j14x + 22, j14y + 4 * PITCH + 3, "F.SilkS")
    gr_text("J14 BUP-30S NPN", j14x - 3, j14y - 6.5, "F.SilkS", 0.85)
    gr_text("Brn +12 Blu GND Blk OUT Wht CTRL", j14x - 3, j14y + 3 * PITCH + 6.5, "F.SilkS", 0.65)
    gr_text("R1 4k7 pullup NPN", r1x - 2, r1y - 4, "F.SilkS", 0.7)
    bup_pads = [
        (1, "+12V", 46, "+12V_SNS"),
        (2, "GND", 2, "GND"),
        (3, "OUT", 31, "/OPTO_IN7"),
        (4, "CTRL", 0, ""),  # jumper to +12V or GND by user
    ]
    a('\t(footprint "ESP32_Carrier:PinHeader_1x04_BUP30S"')
    a('\t\t(layer "F.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {j14x} {j14y})")
    a('\t\t(property "Reference" "J14"')
    a("\t\t\t(at 0 -3.8 0)")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "BUP_30S"')
    a(f"\t\t\t(at 0 {3 * PITCH + 3.8} 0)")
    a('\t\t\t(layer "F.Fab")')
    a("\t\t\t(effects (font (size 0.9 0.9) (thickness 0.12)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")
    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
        a("\t\t(fp_rect")
        a("\t\t\t(start -1.8 -1.8)")
        a(f"\t\t\t(end 1.8 {3 * PITCH + 1.8})")
        a(f"\t\t\t(stroke (width {w}) (type solid))")
        a("\t\t\t(fill none)")
        a(f'\t\t\t(layer "{layer}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
    for i, (num, lab, neti, netn) in enumerate(bup_pads):
        y = i * PITCH
        a(f'\t\t(fp_text user "{lab}"')
        a(f"\t\t\t(at 3.5 {y} 0)")
        a('\t\t\t(layer "F.SilkS")')
        a("\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1)) (justify left))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        shape = "rect" if i == 0 else "circle"
        a(f'\t\t(pad "{num}" thru_hole {shape}')
        a(f"\t\t\t(at 0 {y})")
        a("\t\t\t(size 1.7 1.7)")
        a("\t\t\t(drill 1.0)")
        a('\t\t\t(layers "*.Cu" "*.Mask")')
        if neti:
            a(f'\t\t\t(net {neti} "{netn}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
    a("\t)")
    # R1 between +12V and OPTO_IN7
    a('\t(footprint "ESP32_Carrier:R_Axial_4k7_BUP"')
    a('\t\t(layer "F.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {r1x} {r1y})")
    a('\t\t(property "Reference" "R1"')
    a("\t\t\t(at 0 -2.8 0)")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "4k7"')
    a("\t\t\t(at 0 2.8 0)")
    a('\t\t\t(layer "F.Fab")')
    a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")
    a('\t\t(pad "1" thru_hole circle')
    a("\t\t\t(at -3.75 0)")
    a("\t\t\t(size 1.6 1.6)")
    a("\t\t\t(drill 0.8)")
    a('\t\t\t(layers "*.Cu" "*.Mask")')
    a('\t\t\t(net 46 "+12V_SNS")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(pad "2" thru_hole circle')
    a("\t\t\t(at 3.75 0)")
    a("\t\t\t(size 1.6 1.6)")
    a("\t\t\t(drill 0.8)")
    a('\t\t\t(layers "*.Cu" "*.Mask")')
    a('\t\t\t(net 31 "/OPTO_IN7")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t)")
    # --- Boot-state passives: R2 (TMC EN pull-up), R3 (BLOWER pull-down),
    # D2 (pump flyback). PCB-only, same as F1 / D1 / the star-power passives.
    def _axial2(fp, ref, val, ax, ay, na, nb, drill, psz, note=""):
        a(f'\t(footprint "ESP32_Carrier:{fp}"')
        a('\t\t(layer "F.Cu")')
        a(f'\t\t(uuid "{uid()}")')
        a(f"\t\t(at {ax} {ay})")
        a(f'\t\t(property "Reference" "{ref}"')
        a("\t\t\t(at 0 -2.8 0)")
        a('\t\t\t(layer "F.SilkS")')
        a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a(f'\t\t(property "Value" "{val}"')
        a("\t\t\t(at 0 2.8 0)")
        a('\t\t\t(layer "F.Fab")')
        a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a("\t\t(attr through_hole)")
        for pnum, (ni, nn), px in ((1, na, -3.75), (2, nb, 3.75)):
            a(f'\t\t(pad "{pnum}" thru_hole {"rect" if pnum == 1 else "circle"}')
            a(f"\t\t\t(at {px} 0)")
            a(f"\t\t\t(size {psz} {psz})")
            a(f"\t\t\t(drill {drill})")
            a('\t\t\t(layers "*.Cu" "*.Mask")')
            a(f'\t\t\t(net {ni} "{nn}")')
            a(f'\t\t\t(uuid "{uid()}")')
            a("\t\t)")
        a("\t)")
        if note:
            gr_text(note, ax - 7, ay + 4.6, "F.SilkS", 0.6)

    # TMC2209 EN is active low and floats at reset -> without this the stepper
    # is energised from power-on until firmware drives IO18 high.
    _axial2("R_Axial_4k7_BUP", "R2", "10k", ox + 60.0, oy + 85.0,
            (11, "/EN_TMC"), (4, "+3V3"), 0.8, 1.6, "R2 EN_TMC pull-up 10k")
    # GPIO3 is a strapping pin with NO internal pull -> pump could run at boot.
    _axial2("R_Axial_4k7_BUP", "R3", "10k", ox + 125.0, oy + 30.0,
            (55, "/BLOWER"), (2, "GND"), 0.8, 1.6, "R3 BLOWER pull-down 10k")
    # Freewheel diode across the diaphragm pump (inductive load, the opto
    # AOD4184 modules do not carry one). Band/cathode = pad 1 = +5V_BLW.
    _axial2("Diode_TVS_DO41", "D2", "1N5819", ox + 127.0, oy + 25.0,
            (56, "+5V_BLW"), (61, "/BLW_RET"), 0.9, 1.7, "D2 K(band)->+5V_BLW")

    # Routes: +12V/GND from power; OUT to U4 IN7
    p12 = (j14x, j14y)
    pg = (j14x, j14y + PITCH)
    po = (j14x, j14y + 2 * PITCH)
    # BUP +12V_SNS from star rail (see STAR block)
    # BUP GND: SNS path toward J1- (not through ESP32 / motor GND spine)
    track(pg[0], pg[1], pg[0] - 6, pg[1], 2, "F.Cu", 0.5)
    track(pg[0] - 6, pg[1], pg[0] - 6, oy + 70.0, 2, "F.Cu", 0.5)
    # route to J1 GND pad area (star meet)
    _jg = pad_world(jx, jy, rot, TB_PITCH / 2, 0)
    track(pg[0] - 6, oy + 70.0, _jg[0], oy + 70.0, 2, "F.Cu", 0.5)
    track(_jg[0], oy + 70.0, _jg[0], _jg[1], 2, "F.Cu", 0.5)
    upt7 = _opto_in_pad(u9_at, 4)  # U9 IN3 = OPTO_IN7 (BUP)
    via(po[0], po[1], 31, 0.4, 0.8)
    xl = ox + bw - 3.0
    track(po[0], po[1], xl, po[1], 31, "F.Cu", 0.35)
    track(xl, po[1], xl, upt7[1], 31, "F.Cu", 0.35)
    track(xl, upt7[1], upt7[0], upt7[1], 31, "F.Cu", 0.35)
    # R1 already netted on pads; short stitches to nearby +12V / OUT pads
    track(r1x - 3.75, r1y, p12[0], r1y, 1, "F.Cu", 0.4)
    track(p12[0], r1y, p12[0], p12[1], 1, "F.Cu", 0.4)
    track(r1x + 3.75, r1y, po[0] + 4, r1y, 31, "F.Cu", 0.4)
    track(po[0] + 4, r1y, po[0] + 4, po[1], 31, "F.Cu", 0.4)
    track(po[0] + 4, po[1], po[0], po[1], 31, "F.Cu", 0.4)



    # ========== STAR POWER ISOLATION ==========
    # J1 = star hub. Branch MOT 2.5mm / Branch SNS 0.5mm + RC. GND star separately.
    W_MOT = 2.5
    W_SNS = 0.5
    gr_text("STAR +12V: MOT 2.5mm | SNS 0.5mm+RC", ox + 4, oy + 44, "B.SilkS", 0.75)
    gr_text("GND star gap chi gap tai J1-", ox + 4, oy + 46.5, "B.SilkS", 0.7)

    # --- RC filter near J1 (F.Cu): R10 10R -> +12V_SNS, C10 47u + C11 100n to GND ---
    r10x, r10y = j1_12[0] + 10.0, j1_12[1] + 8.0
    c10x, c10y = r10x + 8.0, r10y
    c11x, c11y = r10x + 8.0, r10y + 4.0
    gr_box(r10x - 4, r10y - 4, c10x + 6, c11y + 4, "F.SilkS")
    gr_text("RC SNS FILTER", r10x - 3, r10y - 5, "F.SilkS", 0.75)
    a('\t(footprint "ESP32_Carrier:R_1206_10R"')
    a('\t\t(layer "F.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {r10x} {r10y})")
    a('\t\t(property "Reference" "R10"')
    a("\t\t\t(at 0 -2 0)")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "10R"')
    a("\t\t\t(at 0 2 0)")
    a('\t\t\t(layer "F.Fab")')
    a("\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr smd)")
    a('\t\t(pad "1" smd roundrect')
    a("\t\t\t(at -1.4 0)")
    a("\t\t\t(size 1.0 1.5)")
    a('\t\t\t(layers "F.Cu" "F.Paste" "F.Mask")')
    a('\t\t\t(net 1 "+12V")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(pad "2" smd roundrect')
    a("\t\t\t(at 1.4 0)")
    a("\t\t\t(size 1.0 1.5)")
    a('\t\t\t(layers "F.Cu" "F.Paste" "F.Mask")')
    a('\t\t\t(net 46 "+12V_SNS")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t)")
    a('\t(footprint "ESP32_Carrier:CP_Radial_D6_47u_25V"')
    a('\t\t(layer "F.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {c10x} {c10y})")
    a('\t\t(property "Reference" "C10"')
    a("\t\t\t(at 0 -4.5 0)")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "47u/25V"')
    a("\t\t\t(at 0 4.5 0)")
    a('\t\t\t(layer "F.Fab")')
    a("\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")
    a('\t\t(pad "1" thru_hole rect')
    a("\t\t\t(at -1.25 0)")
    a("\t\t\t(size 1.8 1.8)")
    a("\t\t\t(drill 0.9)")
    a('\t\t\t(layers "*.Cu" "*.Mask")')
    a('\t\t\t(net 46 "+12V_SNS")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(pad "2" thru_hole circle')
    a("\t\t\t(at 1.25 0)")
    a("\t\t\t(size 1.8 1.8)")
    a("\t\t\t(drill 0.9)")
    a('\t\t\t(layers "*.Cu" "*.Mask")')
    a('\t\t\t(net 2 "GND")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t)")
    a('\t(footprint "ESP32_Carrier:C_0805_100n"')
    a('\t\t(layer "F.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {c11x} {c11y})")
    a('\t\t(property "Reference" "C11"')
    a("\t\t\t(at 0 -1.8 0)")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.6 0.6) (thickness 0.1)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "100n"')
    a("\t\t\t(at 0 1.8 0)")
    a('\t\t\t(layer "F.Fab")')
    a("\t\t\t(effects (font (size 0.6 0.6) (thickness 0.1)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr smd)")
    a('\t\t(pad "1" smd roundrect')
    a("\t\t\t(at -0.95 0)")
    a("\t\t\t(size 0.8 1.2)")
    a('\t\t\t(layers "F.Cu" "F.Paste" "F.Mask")')
    a('\t\t\t(net 46 "+12V_SNS")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(pad "2" smd roundrect')
    a("\t\t\t(at 0.95 0)")
    a("\t\t\t(size 0.8 1.2)")
    a('\t\t\t(layers "F.Cu" "F.Paste" "F.Mask")')
    a('\t\t\t(net 2 "GND")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t)")
    # Star spur: J1+ -> R10 pin1 (F.Cu 0.5mm SNS entry)
    track(j1_12[0], j1_12[1], r10x - 1.4, j1_12[1], 1, "F.Cu", W_SNS)
    track(r10x - 1.4, j1_12[1], r10x - 1.4, r10y, 1, "F.Cu", W_SNS)
    # SNS rail stub after filter
    sns_x = c10x + 4.0
    track(r10x + 1.4, r10y, sns_x, r10y, 46, "F.Cu", W_SNS)
    track(c10x - 1.25, c10y, sns_x, c10y, 46, "F.Cu", W_SNS)
    track(c11x - 0.95, c11y, sns_x, c11y, 46, "F.Cu", W_SNS)
    track(sns_x, r10y, sns_x, oy + 42.0, 46, "F.Cu", W_SNS)
    # SNS GND back to J1- only (do not share motor GND path)
    j1_gnd = pad_world(jx, jy, rot, TB_PITCH / 2, 0)
    track(c10x + 1.25, c10y, c10x + 1.25, j1_gnd[1] + 6, 2, "F.Cu", W_SNS)
    track(c10x + 1.25, j1_gnd[1] + 6, j1_gnd[0], j1_gnd[1] + 6, 2, "F.Cu", W_SNS)
    track(j1_gnd[0], j1_gnd[1] + 6, j1_gnd[0], j1_gnd[1], 2, "F.Cu", W_SNS)
    track(c11x + 0.95, c11y, c10x + 1.25, c11y, 2, "F.Cu", W_SNS)

    # Feed limit groups + BUP from SNS rail (F.Cu)
    for mi, (_, _, _, _, _, _, jx_g, jy_g, *_) in enumerate(l298n_pcb):
        # jx is motor jack; +12V_SNS on min/max at jx+8 / jx+16
        for dx in (8.0, 16.0):
            px = jx_g + dx
            track(sns_x, jy_g, px, jy_g, 46, "F.Cu", W_SNS)
    # BUP J14 +12V_SNS
    track(sns_x, j14y, j14x, j14y, 46, "F.Cu", W_SNS)

    # --- Bulk 470u near TMC + each L298N (B.Cu) ---
    bulk_places = [
        ("C20", t_vm[0] + 8, t_vm[1], "TMC"),
        ("C21", ox + 148.0 - 28, oy + 65.0, "U5"),
        ("C22", ox + 148.0 - 28, oy + 100.0, "U6"),
        ("C23", ox + 148.0 - 28, oy + 150.0, "U7"),
    ]
    for ref, bx, by, tag in bulk_places:
        gr_text(f"{ref} 470u {tag}", bx - 4, by - 6, "B.SilkS", 0.65)
        a('\t(footprint "ESP32_Carrier:CP_Radial_D8_470u_25V"')
        a('\t\t(layer "B.Cu")')
        a(f'\t\t(uuid "{uid()}")')
        a(f"\t\t(at {bx} {by} {rot})")
        a(f'\t\t(property "Reference" "{ref}"')
        a(f"\t\t\t(at 0 -5.5 {rot})")
        a('\t\t\t(layer "B.SilkS")')
        a("\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a('\t\t(property "Value" "470u/25V"')
        a(f"\t\t\t(at 0 5.5 {rot})")
        a('\t\t\t(layer "B.Fab")')
        a("\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a("\t\t(attr through_hole)")
        a('\t\t(pad "1" thru_hole rect')
        a("\t\t\t(at -1.75 0)")
        a("\t\t\t(size 1.8 1.8)")
        a("\t\t\t(drill 0.9)")
        a('\t\t\t(layers "*.Cu" "*.Mask")')
        a('\t\t\t(net 1 "+12V")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a('\t\t(pad "2" thru_hole circle')
        a("\t\t\t(at 1.75 0)")
        a("\t\t\t(size 1.8 1.8)")
        a("\t\t\t(drill 0.9)")
        a('\t\t\t(layers "*.Cu" "*.Mask")')
        a('\t\t\t(net 2 "GND")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a("\t)")
        # stitch bulk to nearby +12V/GND (motor star)
        track(bx - 1.75, by, t_vm[0], by, 1, "B.Cu", W_MOT)
        track(t_vm[0], by, t_vm[0], t_vm[1], 1, "B.Cu", W_MOT)
        track(bx + 1.75, by, j1_gnd[0] + 4, by, 2, "B.Cu", W_MOT)

    # Reinforce MOT branch from J1+ to TMC bus at 2.5mm (star, not daisy from sensors)
    track(j1_12[0], j1_12[1], j1_12[0], t_vm[1], 1, "B.Cu", W_MOT)
    track(j1_12[0], t_vm[1], t_vm[0], t_vm[1], 1, "B.Cu", W_MOT)
    # MOT GND: drivers -> J1- wide, separate from SNS GND path above
    track(t_gnd[0], t_gnd[1], j1_gnd[0] + 4, t_gnd[1], 2, "B.Cu", W_MOT)
    track(j1_gnd[0] + 4, t_gnd[1], j1_gnd[0] + 4, j1_gnd[1], 2, "B.Cu", W_MOT)
    track(j1_gnd[0] + 4, j1_gnd[1], j1_gnd[0], j1_gnd[1], 2, "B.Cu", W_MOT)


    a(")")
    out = ROOT / "esp32_baseboard.kicad_pcb"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def write_readme() -> Path:
    text = """# ESP32-S3 Baseboard — BOM + do ben >3 nam

**Danh sach module day du (ghi nho):** xem [`MODULES.md`](MODULES.md).

May van phong ~20 cm. PSU ngoai **Mean Well 12V/3A**. Limit = **co khi** (ngoai board); board chi co **chan cam**.

## 1) Linh kien TREN board (module / jack)

| Ref | Linh kien | Vai tro | Trang thai do ben |
|-----|-----------|---------|-------------------|
| J1 | Terminal 2P 5.0 mm | +12V_RAW / GND tu PSU | OK |
| **F1** | PTC radial ~3A 30V | Bao ve ngan mach | **Da them** (re) |
| **D1** | TVS P6KE15A (DO-41) | Clamp surge 12V | **Da them** (re) |
| **U1** | **ESP32-S3-DevKitC-1** (44-pin, N8R2/N16R8) | MCU | **Da doi** (bo DevKit V1 + MCP23017) |
| **U2** | **MP1584EN** 5V | +5V logic / TFT / buzzer | **Da doi** (bo Mini560) |
| **U8** | **MP1584EN** 5V | +5V_BLW rieng bom khi | **Da them** |
| **U3** | **TMC2209** stepstick | NEMA17 | Giu — chon hang tot (BTT), heatsink, I_run hop ly |
| **U4 / U9** | **PC817 4CH ×2** | Cach ly limit + BUP | **Da doi** (bo 8CH dai ~100mm) |
| **U5–U7** | **DRV8871** x3 | 3x GA12-N20 | **Da doi** (bo L298N) |
| C* / R10 | Bulk 470u @ driver; R10=10R + C10=47u + C11=100n SNS | Star power | Chon tu 105°C long-life |
| R1 | 4k7 axial | Pull-up BUP NPN | OK |
| J2 | Header 1x04 | NEMA17 A+/A−/B+/B− | Chi jack |
| J4 | Header 1x10 | OPTO field (limit + BUP IN) | Chi jack |
| J5–J7 | Header 1x02 | Motor DC 1..3 | Chi jack |
| **J8–J13** | Header 1x02 x6 | **Limit MIN/MAX** (co khi, day ra) | Chi jack — **khong** cam bien tren PCB |
| J14 | Header 1x04 | BUP-30S | Chi jack |
| J15 | Header 1x03 | Buzzer 5V | Chi jack |
| J16 | Header 1x04 | AOD4184 PWM/GND/+5V_BLW/FAN− | Chi jack (+ module AOD4184) |
| J17 | Header 1x12 | TFT SPI + touch I2C (+ RST / BL / T_INT) | Chi jack |

J3: **khong dung**.

## 2) Linh kien NGOAI board (day / module roi)

| Linh kien | SL | Ghi chu |
|-----------|----|---------|
| Mean Well **12V/3A** (hoac tuong duong cong nghiep) | 1 | PSU chinh — **da chot** (bo DDR-rail qua to) |
| NEMA17 stepper | 1 | Qua J2 |
| GA12-N20 12V | 3 | Qua J5–J7 |
| **Limit switch co khi** (NO/NC, Omron-style / KW11 / ME-8108…) | **6** | Qua **J8–J13**; day 2 loi +12V_SNS / COM; **khong** dung cam bien quang hanh trinh |
| Autonics **BUP-30S** | 1 | Qua J14; thoi bui dinh ky |
| Buzzer active 5V | 1 | Qua J15 |
| Module **AOD4184** (logic-level MOSFET) | 1 | Cam J16 |
| **Bom mang mini 5V** (diaphragm) | 1 | Ap cao / Q thap; ong silicone + tee 2 voi → BUP TX/RX |
| TFT + touch (SPI + I2C) | 1 | Qua J17 |
| Ong silicone Ø4 + tee + 2 voi phun | 1 bo | Co khi |

## 3) GPIO (tom tat)

| Chuc nang | GPIO |
|-----------|------|
| Limit OUT1..6 (qua opto) | IO1,2,4,5,6,7 |
| BUP OUT7 | IO8 |
| Spare OUT8 | IO9 |
| Motor1..3 IN1/IN2 | IO10/11, 12/13, 14/15 |
| TMC STEP/DIR/EN | IO16/17/18 |
| TFT SCK/MOSI/CS/DC (khong MISO) | IO39/40/42/21 |
| TFT RST (chung LCD+touch) / BL PWM | IO46 / IO45 |
| Touch SDA/SCL / INT | IO47/48 / IO41 |
| Buzzer | IO38 |
| AOD4184 / bom | IO3 |
| IO35 / IO36 / IO37 | **KHONG dung** - octal PSRAM (N16R8) |

### Passive trang thai boot (DA co tren PCB)

| Ref | Gia tri | Noi | Vi sao |
|-----|---------|-----|--------|
| R2 | 10k pull-**up** -> +3V3 | /EN_TMC (IO18) | EN active-low + float luc reset -> stepper bi cap dien truoc khi firmware chay |
| R3 | 10k pull-**down** -> GND | /BLOWER (IO3) | IO3 la strapping pin, KHONG co pull noi bo -> bom mang co the chay luc boot |
| D2 | 1N5819 (DO-41) | +5V_BLW <-> /BLW_RET | Freewheel cho bom mang (tai cam); module AOD4184 opto khong co san |

D2: vach tren than diode (cathode) = pad 1 = **+5V_BLW**. Lap nguoc la chap nguon.

IO45 / IO46 **khong** can dien tro: ca hai la strapping pin, co pull-down noi
bo giu suot reset -> BL tat va man giu trong reset ngay tu luc cap nguon.

### Canh bao mua module

- **Chot DevKitC-1 v1.1**: v1.1 dat WS2812 onboard tren GPIO38 (trung buzzer,
  vo hai - LED nhap nhay theo coi). v1.0 dat no tren GPIO48 = **trung I2C SCL**.
- **KHONG mua ban hau to V** (N16R8V / N32R16V): VDD_SPI = 1.8V keo GPIO47/48
  xuong muc logic 1.8V -> hong bus touch.
- IO35/36 chi trong tren **N8R2** (quad PSRAM). Voi N16R8 (octal) thi bo trong
  J17.12 (T_INT) va poll touch controller.

## 4) Da doi theo goi y do ben (OK)

- MCU: ESP32-S3, du GPIO, **khong MCP23017**
- Motor DC: **DRV8871** thay L298N (nong / de chet)
- Buck logic: **MP1584EN** thay Mini560; **U8** tach bom khi
- PSU: Mean Well 12V/3A (khong DIN-rail qua lon)
- Star power SNS / MOT; thoi BUP = bom mang + AOD4184

## 5) Do ben >3 nam — chi doi khi gia tang it

| Muc | Quyet dinh | Chi phi |
|-----|------------|---------|
| **F1 PTC + D1 TVS @ J1** | **Da them tren PCB** (RXE030/~3A + P6KE15A) | +~5–15k VND |
| **MP1584** | Giu module re; chon **ban 5V co dinh** (khong ADJ) | ~0 (cung gia) |
| **Buck cong nghiep** | **Khong doi** (Mean Well/Recom dat) | — |
| **TMC2209** | Mua **BTT that** + heatsink nho (cung form stepstick) | +~20–40k vs clone |
| **PC817** | **2× 4CH** (~48×38) thay 8CH | ~0–10k |
| **Header** | Pin **ma vang** / header chat (khong doi sang JST dat) | +~10–20k |
| **GA12-N20 / bom mang** | **Khong doi** loai; duty thap + du phong | ~0 |
| **TFT** | Chon **2.8\" IPS** cung phan khuc (tranh man sieu re) | +0–30k |
| **Socket ESP32** | Header ma vang; han that sau thu neu can | it |

Limit **co khi** Omron-class neu gia gan KW12; board **chi jack**.

## 6) Bom / thoi BUP

```
U8 +5V_BLW → AOD4184 (J16) → bom mang 5V → ong → tee → 2 voi (TX/RX BUP)
```

Khong dung quat 5015 (ap thap).

## 7) Kich thuoc module — chon gon + chat luong

Carrier PCB hien ~**175×175 mm**. Opto: **U4+U9 PC817 4CH ×2** (~48×38 moi cai).

| Ref | Footprint board | Kich thuoc that (typ.) | Chon gon + chat luong | Bo / tranh |
|-----|-----------------|------------------------|------------------------|------------|
| U1 | Socket 2×22, row 25.4 | DevKitC-1 **~63×25.4×13** | **DevKitC-1 N8R2** (Espressif) — gon hop ly, USB-C, du GPIO | Module bare WROOM (mat USB debug); DevKit V1 30-pin |
| U2/U8 | 22×17 | MP1584 **22×17×4** | **MP1584EN fixed 5V** (khong bien tro) — nho hon Mini560 (29×18), du 1–1.5A derate | Mini560; buck “5A” sieu re; ADJ de lech 5V |
| U3 | ~20×20 | BTT **15.24×20.32** | **BigTreeTech TMC2209 V1.3** + heatsink nho | Clone vo ten; driver lon SPI |
| U4/U9 | ~48×38 ×2 | Module 4ch | **2× PC817 4CH** (Shopee) — do pad truoc fab | 8ch dai ~100mm |
| U5–U7 | 28×20 ×3 | Adafruit **~24×20**; Shopee ~25–30×20 | Module **DRV8871** ~25×20, chip that, heatsink; I_lim ~1–1.5A (N20) | L298N (~43×43); TB6612 yeu 12V |
| J16 mod | Header 1×04 | AOD4184 **~23×16** (co ban ~33×16) | Module **~23×16** opto+AOD4184 | MOSFET khong heatsink / khong opto neu nhieu nhieu |
| Bom khi | Off-board | 030 ~**38 mm**; 370 ~**55–60 mm** | **Bom mang 5V “030”** neu ap du; else **370** — burst ngan | Quat 5015; bom AC 220V |
| Limit | Chi jack | Micro **~20×6×10** (Omron SS/D2F) | **Omron SS-5 / D2F / KW12** co khi, day 2 loi | Cam bien quang hanh trinh; limit sieu re vo nhua mong |
| BUP | Chi jack | BUP-30S **~50×25×40** (khoang) | Autonics **BUP-30S** giu | Clone quang |
| TFT | Chi jack | 2.8\" ~**70×50**; 3.5\" ~**85×55** | **2.8\" IPS + capacitive** (SPI+I2C) — du HMI, gon hop 20 cm | 7\" HDMI; man resistive re |
| PSU | Ngoai vo | LRS-35-12 **~99×82×30** | Mean Well **LRS-35-12** / RSP nho | Adapter no-name; DIN DDR qua to |

### Goi y layout gon (khong doi chuc nang)

1. **U4/U9**: da doi **2×4ch** — do footprint that module Shopee truoc fab.
2. **U2/U8**: giu MP1584 22×17; dat sat J1 / J16.
3. **U5–U7**: 3 module ~25×20 xep doc, heatsink thap.
4. **Bom + AOD4184**: treo off-board / vach vo (khong an dien tich PCB).
5. Carrier target thuc te: **~120×100 … 140×120 mm** neu gom opto 4ch×2 (sau khi layout lai).

### Chat luong vs “nho nhat”

- Nho hon MP1584 ma van >1A tin cay → kho (module re de chay). Can hon: Recom/Murata ~0.5–1A **chi** neu tach TFT sang rail rieng.
- Khong cat DRV8871 / TMC / DevKitC de “sieu nho” — day la diem do ben.

## Tai tao

```
python gen_power_carrier.py
```

Do that truoc fab: ESP32-S3 DevKitC, DRV8871, MP1584 x2, AOD4184, opto 4ch, TFT pinout.
"""
    out = ROOT / "README.md"
    out.write_text(text, encoding="utf-8")
    return out



def write_project() -> Path:
    pro = {
        "meta": {"filename": "esp32_baseboard.kicad_pro", "version": 3},
        "sheets": [["esp32_baseboard.kicad_sch", "Root"]],
        "text_variables": {},
        "net_settings": {
            "classes": [
                {
                    "name": "Default",
                    "clearance": 0.2,
                    "track_width": 0.25,
                    "via_diameter": 0.6,
                    "via_drill": 0.3,
                    "wire_width": 6,
                    "bus_width": 12,
                    "diff_pair_gap": 0.25,
                    "diff_pair_via_gap": 0.25,
                    "diff_pair_width": 0.2,
                    "line_style": 0,
                    "microvia_diameter": 0.3,
                    "microvia_drill": 0.1,
                    "pcb_color": "rgba(0, 0, 0, 0.000)",
                    "schematic_color": "rgba(0, 0, 0, 0.000)",
                },
                {
                    "name": "Power",
                    "clearance": 0.25,
                    "track_width": 1.0,
                    "via_diameter": 0.8,
                    "via_drill": 0.4,
                    "wire_width": 6,
                    "bus_width": 12,
                    "diff_pair_gap": 0.25,
                    "diff_pair_via_gap": 0.25,
                    "diff_pair_width": 0.2,
                    "line_style": 0,
                    "microvia_diameter": 0.3,
                    "microvia_drill": 0.1,
                    "pcb_color": "rgba(0, 0, 0, 0.000)",
                    "schematic_color": "rgba(0, 0, 0, 0.000)",
                },
            ],
            "meta": {"version": 3},
        },
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "boards": [],
        "cvpcb": {"equivalence_files": []},
        "erc": {"erc_exclusions": [], "meta": {"version": 0}, "rule_severities": {}},
        "schematic": {
            "annotate_start_num": 0,
            "drawing": {},
            "legacy_lib_dir": "",
            "legacy_lib_list": [],
            "meta": {"version": 1},
            "page_layout_descr_file": "",
            "plot_directory": "",
            "spice_external_command": 'spice "%I"',
            "text_variables": {},
        },
        "pcbnew": {
            "last_paths": {
                "gencad": "",
                "idf": "",
                "netlist": "",
                "plot": "",
                "pos_files": "",
                "specctra_dsn": "",
                "step": "",
                "svg": "",
                "vrml": "",
            },
            "page_layout_descr_file": "",
        },
    }
    out = ROOT / "esp32_baseboard.kicad_pro"
    out.write_text(json.dumps(pro, indent=2) + "\n", encoding="utf-8")
    return out


def main() -> None:
    PRETTY.mkdir(parents=True, exist_ok=True)
    fps = [
        write_esp32_footprint(),
        write_mini560_footprint(),
        write_screw_terminal_footprint(),
        write_ptc_fuse_footprint(),
        write_tvs_do41_footprint(),
        write_tmc2209_footprint(),
        write_pc817_4ch_footprint(),
        write_l298n_footprint(),
        write_pin_header_footprint(4, "PinHeader_1x04_Motor", [p[1] for p in MOTOR_HEADER]),
        write_pin_header_footprint(TFT_PINS, TFT_FP, [p[1] for p in TFT_HEADER]),
        write_pin_header_footprint(3, "PinHeader_1x03_Buzzer", [p[1] for p in BUZZER_HEADER]),
        write_pin_header_footprint(4, "PinHeader_1x04_MOSFET", [p[1] for p in MOSFET_HEADER]),
        write_pin_header_footprint(10, "PinHeader_1x10_OptoField", [p[1] for p in OPTO_FIELD_HEADER]),
        write_pin_header_footprint(2, "PinHeader_1x02_MotorDC", ["M+", "M-"]),
        write_pin_header_footprint(2, "PinHeader_1x02_LimitSW", ["+12V", "SW"]),
        write_pin_header_footprint(4, "PinHeader_1x04_BUP30S", ["+12V", "GND", "OUT", "CTRL"]),
        write_r_axial_4k7_bup(),
        *write_star_power_passives(),
    ]
    sym = write_symbol_lib()
    write_lib_tables()
    sch = write_schematic_v2()
    pcb = write_pcb()
    pro = write_project()
    readme = write_readme()
    print("Wrote:")
    for p in [*fps, sym, sch, pcb, pro, readme]:
        print(" ", p)


if __name__ == "__main__":
    main()
