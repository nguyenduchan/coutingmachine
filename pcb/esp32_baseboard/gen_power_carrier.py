#!/usr/bin/env python3
"""Generate MP1584EN + TMC2209 + PC817 DIP-4 + ULN2003 + ESP32-S3 carrier.

All parts on TOP (F.Cu); B.Cu is routing only.

Power path:
  12V-3A PSU --J1--> F1 PTC --> +12V (D1 TVS to GND)
       --> MP1584EN U2  -> +5V      -> ESP32-S3 / logic / TFT / buzzer
       --> +12V rail ----> AOD4184 (J16) -> 370 air pump 12V (3s / 5min)
       --> TMC2209 (U3) VM=12V + VIO=3V3; NEMA17 on U3 Mot pins (no J2)
       --> ULN2003 x3 (U5-U7) COM=+12V, IN from GPIO direct -> J5-J7 28BYJ-48
Jacks: J5-J7 BYJ, J8/J10/J12 HOME endstop 1×04 (2 NC), J14 BUP, J15 buzzer, J16 AOD4184,
       J17+J23 TFT+touch, J18 EC11, J15 buzzer. ULN via Shopee 74HC595-24IO module (3x595) east of ESP32.
MCU: ESP32-S3-DevKitC-1 (44-pin, 2x22 @ 2.54, row 25.4). Prefer N16R8;
     do not use GPIO35-37 on octal flash boards.
"""

from __future__ import annotations

import json
import os
import re
import sys
import uuid
from pathlib import Path

from placement_floorplan import balanced_placement
from s3_pinmap import (
    BUZZER_GPIO,
    DRV_MOTORS,
    ENC_GPIO,
    LEFT_PINS,
    MOSFET_GPIO,
    OPTO_GPIO,
    PIN_BY_NAME,
    RIGHT_PINS,
    SHIFT_GPIO,
    TFT_GPIO,
    TMC_GPIO,
    pad_local,
)
from maze_router import (
    autoroute_pads,
    emit_service_buses,
    format_routes,
    inject_routes,
    parse_kept_vias,
    parse_hole_sites,
    parse_keepout_holes,
    parse_pads,
    repair_open_pcb,
    strip_routes,
)

ROOT = Path(__file__).resolve().parent
LIB = ROOT / "libraries"
PRETTY = LIB / "ESP32_Carrier.pretty"

# Final copper: 2-layer A* maze (same-layer bends OK). Manual track_* become no-ops.
# Keep the legacy hand-routing helpers disabled: their track()/via() calls are
# no-ops whenever this is True, and the copper comes from a router instead.
USE_MAZE_AUTOROUTE = True
# The in-house maze router is now the fallback: FreeRouting does the routing
# (see route_freerouting.py). PCB_SKIP_MAZE=1 emits placement + nets only and
# hands the board straight to FreeRouting -- seconds instead of ~25 minutes.
RUN_MAZE = os.environ.get("PCB_SKIP_MAZE", "") != "1"

PITCH = 2.54
ROW_SPACING = 25.4
PAD_SIZE = 1.7
PAD_DRILL = 1.0
S3_PINS_PER_SIDE = 22

# MP1584EN mini buck 22 x 17 mm — Shopee item 41383641614 (fixed 5V 3A).
# Pad layout measured from PlantCtrl MP1584_buck_module.kicad_mod (22x17 dual-THT
# per pin — same PCB as adjustable mini MP1584 sold on Shopee/Taobao).
MP1584_W = 22.1
MP1584_H = 17.0
MP1584_PAD_X = 9.271  # |x| column center from board origin
MP1584_PAD_Y_HI = 6.604  # outer hole of each +/− pair
MP1584_PAD_Y_LO = 4.064  # inner hole; HI−LO = 2.54 mm
MP1584_PAD_Y_MID = (MP1584_PAD_Y_HI + MP1584_PAD_Y_LO) / 2  # 5.334
MP1584_PAD_SPAN_X = MP1584_PAD_X * 2  # 18.542 IN ↔ OUT
MP1584_PAD_SPAN_Y = MP1584_PAD_Y_MID * 2  # 10.668 + ↔ −
MP1584_SHOPEE_URL = (
    "https://shopee.vn/MP1584EN-Mini-DC-Buck-41383641614"
)
# Dual THT per pin: 1=VIN+ 2=VIN- 3=VOUT- 4=VOUT+ (PlantCtrl pinout).
MP1584_PADS: list[tuple[str, str, float, float]] = [
    ("1", "VIN+", -MP1584_PAD_X, MP1584_PAD_Y_LO),
    ("1", "VIN+", -MP1584_PAD_X, MP1584_PAD_Y_HI),
    ("2", "VIN-", -MP1584_PAD_X, -MP1584_PAD_Y_LO),
    ("2", "VIN-", -MP1584_PAD_X, -MP1584_PAD_Y_HI),
    ("3", "VOUT-", MP1584_PAD_X, -MP1584_PAD_Y_LO),
    ("3", "VOUT-", MP1584_PAD_X, -MP1584_PAD_Y_HI),
    ("4", "VOUT+", MP1584_PAD_X, MP1584_PAD_Y_LO),
    ("4", "VOUT+", MP1584_PAD_X, MP1584_PAD_Y_HI),
]
# Aliases so older Mini560 layout math keeps working
MINI560_W = MP1584_W
MINI560_H = MP1584_H
MINI560_PAD_SPAN_X = MP1584_PAD_SPAN_X
MINI560_PAD_SPAN_Y = MP1584_PAD_SPAN_Y

TB_PITCH = 5.0
# Default footprint orientation. Per-part ROT_* overrides when rubber-band
# crossings would otherwise force crossed traces (silk labels follow that rot).
PART_ROT = 0
BOTTOM_ROT = PART_ROT  # legacy alias
# Uncross: TMC STEP/DIR/EN vs U1 IO16/17/18; ENC A/B; DIP↔BYJ phase order
ROT_TMC = 270
ROT_ENC = 180
ROT_DIP = 180
ROT_BYJ = 180

TMC_W = 20.4
TMC_H = 20.4
TMC_ROW = 15.24

MOTOR_HEADER = [
    ("1", "A2", 11),
    ("2", "A1", 12),
    ("3", "B1", 13),
    ("4", "B2", 14),
]

# J17 LCD 1×9 + J23 touch 1×5 — contiguous column, MSP3520 / lcdwiki order.
# Module silk (exact): VCC GND CS RESET DC SDI SCK LED SDO | T_CLK T_CS T_DIN T_DO T_IRQ
# Shared SPI: SCK↔T_CLK, MOSI↔T_DIN; LCD SDO (J17.9) NC — T_DO owns MISO.
# EC11 on J18: GPIO47=ENC_A, GPIO45=ENC_B (SW unused — Enter on TFT).
# Avoid IO38 — DevKitC-1 v1.1 onboard WS2812.
TFT_LCD_HEADER = [
    ("1", "VCC"),    # module pin 1
    ("2", "GND"),
    ("3", "CS"),
    ("4", "RESET"),
    ("5", "DC"),
    ("6", "SDI"),    # MOSI
    ("7", "SCK"),
    ("8", "LED"),
    ("9", "SDO"),    # MISO LCD — NC on PCB
]
TFT_TP_HEADER = [
    ("1", "T_CLK"),  # module pin 10
    ("2", "T_CS"),   # 11
    ("3", "T_DIN"),  # 12
    ("4", "T_DO"),   # 13
    ("5", "T_IRQ"),  # 14
]
# Legacy combined list (docs / 1×14 silk names)
TFT_HEADER = TFT_LCD_HEADER + [
    (str(10 + i), name) for i, (_, name) in enumerate(TFT_TP_HEADER)
]
TFT_LCD_PINS = len(TFT_LCD_HEADER)
TFT_TP_PINS = len(TFT_TP_HEADER)
TFT_PINS = TFT_LCD_PINS + TFT_TP_PINS
TFT_LCD_FP = "PinHeader_1x09_TFT_LCD"
TFT_TP_FP = "PinHeader_1x05_TFT_TP"
TFT_FP = TFT_LCD_FP  # primary / sch footprint alias
TFT_LCD_SYM = "Conn_1x09_TFT_LCD"
TFT_TP_SYM = "Conn_1x05_TFT_TP"
TFT_SYM = TFT_LCD_SYM

BUZZER_HEADER = [("1", "VCC5"), ("2", "GND"), ("3", "SIG")]
MOSFET_HEADER = [("1", "PWM"), ("2", "GND"), ("3", "+12V"), ("4", "FAN-")]
# KY-040 / EC11: GND, 3V3, CLK(A), DT(B) — SW not on header (Enter on screen)
ENC_HEADER = [("1", "GND"), ("2", "3V3"), ("3", "ENC_A"), ("4", "ENC_B")]
ENC_PINS = len(ENC_HEADER)
ENC_FP = "PinHeader_1x04_ENC"
ENC_SYM = "Conn_1x04_ENC"

VIA12_DRILL = 0.6
VIA12_DIA = 1.1

# Carrier; modules keep ≥ MODULE_EDGE_CLEAR from Edge.Cuts.
# Width grown for ≥8 mm Eco gaps + ≥10 mm MCU keepout (E11.3).
BOARD_W = 220.0
BOARD_H = 160.0
BOARD_W_EXTRA = BOARD_W - 185.0
MODULE_EDGE_CLEAR = 10.0  # min distance module courtyard → board edge
MODULE_MCU_CLEAR = 10.0  # min gap any non-MCU Eco ↔ MCU Eco
MODULE_CLUSTER_GAP = 8.0  # min gap between same-face Eco boxes (E11.2)
SILK_TEXT_MIN_MM = 0.8  # KiCad board-setup silk text minimum
MOUNT_INSET = 3.5  # M3 hole centers from Edge.Cuts (mounts may sit in margin)
MOUNT_DRILL = 3.2
MOUNT_PAD = 6.5  # silk / keepout diameter
VIA12_COUNT_X = 3
VIA12_COUNT_Y = 2
VIA12_PITCH = 1.8

# Discrete PC817 DIP-4 ×4 (replaces 2× module 4CH). Pinout: 1=A 2=K 3=E 4=C.
DIP4_ROW = 7.62
DIP4_PAD = 1.6
DIP4_DRILL = 0.9
DIP4_BODY_L = 5.2
DIP4_BODY_W = 6.5
OPTO_CH = [
    # (uref, r_led, r_pu, in_id, in_net, out_id, out_net, anode_id, anode_net, tag)
    # Just enough: HOME×3 + BUP (field IN5–8 removed with 74HC595 GPIO reclaim).
    ("U41", "R41", "R45", 25, "/OPTO_IN1", 16, "/OPTO_OUT1", 80, "/OPTO_A1", "HOME1"),
    ("U42", "R42", "R46", 26, "/OPTO_IN2", 17, "/OPTO_OUT2", 81, "/OPTO_A2", "HOME2"),
    ("U43", "R43", "R47", 27, "/OPTO_IN3", 18, "/OPTO_OUT3", 82, "/OPTO_A3", "HOME3"),
    ("U44", "R44", "R48", 28, "/OPTO_IN4", 19, "/OPTO_OUT4", 83, "/OPTO_A4", "BUP"),
]
# Legacy names kept so old schematic helpers that still mention OPTO_FIELD_* compile.
OPTO_FIELD_HEADER = [
    ("1", "GND_I"),
    ("2", "VCC_I"),
    ("3", "IN1"),
    ("4", "IN2"),
    ("5", "IN3"),
    ("6", "IN4"),
]
OPTO_FIELD_PINS = len(OPTO_FIELD_HEADER)
OPTO_FIELD_FP = f"PinHeader_1x{OPTO_FIELD_PINS:02d}_OptoField"
OPTO_FIELD_SYM = f"Conn_1x{OPTO_FIELD_PINS:02d}_OptoField"

BYJ_HEADER = [("1", "A"), ("2", "B"), ("3", "C"), ("4", "D"), ("5", "+12V")]
BYJ_FP = "PinHeader_1x05_BYJ"
BYJ_SYM = "Conn_1x05_BYJ"

# CNC/3D endstop module 1×04 (Shopee). VCC+GND unused on carrier; SIG+SNS =
# dry NC → opto (+12V_SNS / OPTO_INx). Keep isolation via PC817.
ENDSTOP_FP = "PinHeader_1x04_Endstop"
ENDSTOP_SYM = "Conn_1x04_Endstop"
ENDSTOP_HEADER = [
    ("1", "VCC"),  # unused on PCB
    ("2", "GND"),  # unused
    ("3", "SIG"),  # → OPTO_INx
    ("4", "SNS"),  # → +12V_SNS
]
ENDSTOP_SHOPEE = (
    "https://shopee.vn/Module-c%C3%B4ng-t%E1%BA%AFc-h%C3%A0nh-tr%C3%ACnh-Endstop-CNC-Printer-3D"
    "-i.951399259.23532922598"
)

# DIP-16 (ULN2003AN / 74HC595)
DIP16_ROW = 7.62
# Square, like KiCad's own DIP footprints. The 2.2 mm tall pad bought nothing
# -- the annular ring is set by the 0.9 mm drill either way -- while the A7
# hole check models every pad as a circle of its largest dimension, so an
# oblong pad demanded 0.3 mm more room sideways than its copper actually
# occupies, and reported 55 phantom violations along the DIP rows.
DIP16_PAD_W, DIP16_PAD_H = 1.6, 1.6
# The DIP body (7.0 mm) is narrower than the 7.62 mm pad rows, so a silk
# outline drawn on the body ran straight through all 16 pads. Silk gets its
# own half-width, outside the pads; Fab and CrtYd keep the real body size.
DIP16_SILK_HX = DIP16_ROW / 2 + DIP16_PAD_W / 2 + 0.3
DIP16_DRILL = 0.9
DIP16_BODY_L = 19.5
DIP16_BODY_W = 7.0

# Legacy aliases (DRV_MOTORS emptied in s3_pinmap)
DRV_W = DIP16_BODY_L
DRV_H = DIP16_BODY_W
L298N_MOTORS = DRV_MOTORS
L298N_W = DRV_W
L298N_H = DRV_H

def pad_world(at_x: float, at_y: float, rot_deg: float, lx: float, ly: float) -> tuple[float, float]:
    """Footprint local pad -> board coordinates (KiCad rotation CCW)."""
    import math
    r = math.radians(rot_deg)
    c, s = math.cos(r), math.sin(r)
    return (at_x + lx * c + ly * s, at_y - lx * s + ly * c)


def local_rect_world_aabb(
    at_x: float, at_y: float, rot_deg: float,
    lx0: float, ly0: float, lx1: float, ly1: float,
) -> tuple[float, float, float, float]:
    """World AABB of a local-axis-aligned footprint rectangle after rotation."""
    corners = [(lx0, ly0), (lx1, ly0), (lx1, ly1), (lx0, ly1)]
    xs, ys = [], []
    for lx, ly in corners:
        wx, wy = pad_world(at_x, at_y, rot_deg, lx, ly)
        xs.append(wx)
        ys.append(wy)
    return min(xs), min(ys), max(xs), max(ys)


def write_mounting_hole_m3() -> Path:
    """Non-plated M3 hole for screwing carrier to enclosure wall."""
    lines: list[str] = []
    a = lines.append
    a('(footprint "MountingHole_M3"')
    a("\t(version 20260206)")
    a('\t(generator "gen_power_carrier.py")')
    a('\t(layer "F.Cu")')
    a('\t(descr "M3 NPTH mounting hole 3.2mm drill")')
    a('\t(tags "mounting hole M3")')
    a('\t(property "Reference" "H**"')
    a("\t\t(at 0 -4.5 0)")
    a('\t\t(layer "F.SilkS")')
    a("\t\t(effects (font (size 0.8 0.8) (thickness 0.1)))")
    a("\t)")
    a('\t(property "Value" "M3"')
    a("\t\t(at 0 4.5 0)")
    a('\t\t(layer "F.Fab")')
    a("\t\t(effects (font (size 0.8 0.8) (thickness 0.1)))")
    a("\t)")
    a("\t(attr through_hole exclude_from_pos_files exclude_from_bom)")
    a("\t(fp_circle")
    a("\t\t(center 0 0)")
    a(f"\t\t(end {MOUNT_PAD / 2} 0)")
    a("\t\t(stroke (width 0.12) (type solid))")
    a("\t\t(fill none)")
    a('\t\t(layer "F.SilkS")')
    a("\t)")
    a("\t(fp_circle")
    a("\t\t(center 0 0)")
    a(f"\t\t(end {MOUNT_PAD / 2 + 0.25} 0)")
    a("\t\t(stroke (width 0.05) (type solid))")
    a("\t\t(fill none)")
    a('\t\t(layer "F.CrtYd")')
    a("\t)")
    a('\t(pad "" np_thru_hole circle')
    a("\t\t(at 0 0)")
    a(f"\t\t(size {MOUNT_DRILL} {MOUNT_DRILL})")
    a(f"\t\t(drill {MOUNT_DRILL})")
    a('\t\t(layers "F&B.Cu" "*.Mask")')
    a("\t)")
    a(")")
    out = PRETTY / "MountingHole_M3.kicad_mod"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


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
        a('\t\t(effects (font (size 0.8 0.8) (thickness 0.1)) (justify right))')
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
        a('\t\t(effects (font (size 0.8 0.8) (thickness 0.1)) (justify left))')
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



def write_pc817_dip4_footprint() -> Path:
    """THT DIP-4 for discrete PC817 (1=A, 2=K, 3=E, 4=C)."""
    hx = DIP4_ROW / 2
    y0 = -0.5 * PITCH
    lines: list[str] = []
    a = lines.append
    a('(footprint "PC817_DIP4"')
    a("\t(version 20260206)")
    a('\t(generator "gen_power_carrier.py")')
    a('\t(generator_version "1.0")')
    a('\t(layer "F.Cu")')
    a('\t(descr "PC817 optocoupler DIP-4 THT — A/K/E/C")')
    a('\t(tags "PC817 optocoupler DIP-4")')
    a('\t(property "Reference" "U**"')
    a(f"\t\t(at 0 {-DIP4_BODY_L / 2 - 1.6} 0)")
    a('\t\t(layer "F.SilkS")')
    a("\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))")
    a("\t)")
    a('\t(property "Value" "PC817"')
    a(f"\t\t(at 0 {DIP4_BODY_L / 2 + 1.6} 0)")
    a('\t\t(layer "F.Fab")')
    a("\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))")
    a("\t)")
    a("\t(attr through_hole)")
    silk_hx = DIP4_ROW / 2 + DIP4_PAD / 2 + 0.3
    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
        a("\t(fp_rect")
        hxr = silk_hx if layer.endswith("SilkS") else DIP4_BODY_W / 2 + 0.2
        a(f"\t\t(start {-hxr} {-DIP4_BODY_L / 2 - 0.2})")
        a(f"\t\t(end {hxr} {DIP4_BODY_L / 2 + 0.2})")
        a(f"\t\t(stroke (width {w}) (type solid))")
        a("\t\t(fill none)")
        a(f'\t\t(layer "{layer}")')
        a("\t)")
    a("\t(fp_arc")
    a(f"\t\t(start {-DIP4_BODY_W / 2} {y0})")
    a(f"\t\t(mid 0 {y0 - 1.0})")
    a(f"\t\t(end {DIP4_BODY_W / 2} {y0})")
    a("\t\t(stroke (width 0.12) (type solid))")
    a('\t\t(layer "F.SilkS")')
    a("\t)")
    # pins 1(A),2(K) left; 4(C),3(E) right (DIP numbering)
    pads = [
        ("1", "A", -hx, y0, "rect"),
        ("2", "K", -hx, y0 + PITCH, "circle"),
        ("3", "E", hx, y0 + PITCH, "circle"),
        ("4", "C", hx, y0, "circle"),
    ]
    for num, name, x, y, shape in pads:
        a(f'\t(fp_text user "{name}"')
        j = "right" if x < 0 else "left"
        a(f"\t\t(at {x - 2.2 if x < 0 else x + 2.2} {y} 0)")
        a('\t\t(layer "F.SilkS")')
        a(f'\t\t(effects (font (size 0.7 0.7) (thickness 0.1)) (justify {j}))')
        a("\t)")
        a(f'\t(pad "{num}" thru_hole {shape}')
        a(f"\t\t(at {x} {y})")
        a(f"\t\t(size {DIP4_PAD} {DIP4_PAD})")
        a(f"\t\t(drill {DIP4_DRILL})")
        a('\t\t(layers "*.Cu" "*.Mask")')
        a("\t)")
    a(")")
    out = PRETTY / "PC817_DIP4.kicad_mod"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def write_pc817_4ch_footprint() -> Path:
    """Deprecated: module footprint removed — discrete DIP-4 only."""
    return write_pc817_dip4_footprint()


def write_pc817_8ch_footprint() -> Path:
    return write_pc817_dip4_footprint()


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
    a('\t\t(at 0 -2.6 0)')
    a('\t\t(layer "F.SilkS")')
    a("\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))")
    a("\t)")
    a('\t(property "Value" "4k7"')
    a('\t\t(at 0 2.6 0)')
    a('\t\t(layer "F.SilkS")')
    a("\t\t(effects (font (size 0.75 0.75) (thickness 0.1)))")
    a("\t)")
    a("\t(attr through_hole)")
    a('\t(fp_rect (start -3.2 -1.5) (end 3.2 1.5) '
      '(stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))')
    a('\t(fp_rect (start -3.4 -1.7) (end 3.4 1.7) '
      '(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))')
    a('\t(pad "1" thru_hole circle (at -3.75 0) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))')
    a('\t(pad "2" thru_hole circle (at 3.75 0) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))')
    a(")")
    out = PRETTY / "R_Axial_4k7_BUP.kicad_mod"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def write_star_power_passives() -> list:
    """Bulk 470u, SNS 47u, 100nF 0805, 10R 1206 — Ref+Value on silk + rect outline."""
    outs = []

    def _radial(name: str, d: float, pitch: float, descr: str, silk_val: str):
        r = d / 2
        # Rectangular silk outline around radial can (user request: đường bao chữ nhật)
        hx, hy = r + 0.4, r + 0.4
        lines = [
            f'(footprint "{name}"',
            "	(version 20260206)",
            '	(generator "gen_power_carrier.py")',
            '	(layer "F.Cu")',
            f'	(descr "{descr}")',
            f'	(property "Reference" "C**" (at 0 {-hy - 1.2} 0)',
            '		(layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))',
            f'	(property "Value" "{silk_val}" (at 0 {hy + 1.2} 0)',
            '		(layer "F.SilkS") (effects (font (size 0.75 0.75) (thickness 0.1))))',
            "	(attr through_hole)",
            f'	(fp_rect (start {-hx} {-hy}) (end {hx} {hy}) '
            f'(stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))',
            f'	(fp_circle (center 0 0) (end {r} 0) '
            f'(stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))',
            f'	(pad "1" thru_hole rect (at {-pitch / 2} 0) (size 1.8 1.8) (drill 0.9) (layers "*.Cu" "*.Mask"))',
            f'	(pad "2" thru_hole circle (at {pitch / 2} 0) (size 1.8 1.8) (drill 0.9) (layers "*.Cu" "*.Mask"))',
            ")",
        ]
        out = PRETTY / f"{name}.kicad_mod"
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return out

    outs.append(_radial("CP_Radial_D8_470u_25V", 8.0, 3.5, "470uF 25V bulk near TMC2209", "470u/25V"))
    outs.append(_radial("CP_Radial_D6_100u_25V", 6.3, 2.5, "100uF 25V shared ULN COM bulk", "100u/25V"))
    outs.append(_radial("CP_Radial_D6_47u_25V", 6.3, 2.5, "47uF 25V SNS rail", "47u/25V"))

    c0805 = (
        '(footprint "C_0805_100n"\n'
        "\t(version 20260206)\n"
        '\t(generator "gen_power_carrier.py")\n'
        '\t(layer "F.Cu")\n'
        '\t(descr "100nF 0805")\n'
        '\t(property "Reference" "C**" (at 0 -1.8 0) (layer "F.SilkS") '
        "(effects (font (size 0.8 0.8) (thickness 0.1))))\n"
        '\t(property "Value" "100n" (at 0 1.8 0) (layer "F.SilkS") '
        "(effects (font (size 0.7 0.7) (thickness 0.1))))\n"
        "\t(attr smd)\n"
        '\t(fp_rect (start -1.1 -0.7) (end 1.1 0.7) (stroke (width 0.12) (type solid)) '
        '(fill none) (layer "F.SilkS"))\n'
        '\t(fp_rect (start -1.3 -0.9) (end 1.3 0.9) (stroke (width 0.05) (type solid)) '
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
        '\t(property "Reference" "R**" (at 0 -1.9 0) (layer "F.SilkS") '
        "(effects (font (size 0.8 0.8) (thickness 0.1))))\n"
        '\t(property "Value" "10R" (at 0 1.9 0) (layer "F.SilkS") '
        "(effects (font (size 0.7 0.7) (thickness 0.1))))\n"
        "\t(attr smd)\n"
        '\t(fp_rect (start -1.7 -0.9) (end 1.7 0.9) (stroke (width 0.12) (type solid)) '
        '(fill none) (layer "F.SilkS"))\n'
        '\t(fp_rect (start -1.9 -1.1) (end 1.9 1.1) (stroke (width 0.05) (type solid)) '
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


def write_dip16_footprint(name: str, descr: str, silk_label: str) -> Path:
    """Standard DIP-16 THT: pitch 2.54, row 7.62, pad ~1.6x2.2, drill 0.9."""
    hx = DIP16_ROW / 2
    y0 = -3.5 * PITCH
    lines: list[str] = []
    a = lines.append
    a(f'(footprint "{name}"')
    a("\t(version 20260206)")
    a('\t(generator "gen_power_carrier.py")')
    a('\t(generator_version "3.0")')
    a('\t(layer "F.Cu")')
    a(f'\t(descr "{descr}")')
    a(f'\t(tags "{name} DIP-16")')
    a('\t(property "Reference" "U**"')
    a(f"\t\t(at 0 {-DIP16_BODY_L / 2 - 1.6} 0)")
    a('\t\t(layer "F.SilkS")')
    a("\t\t(effects (font (size 0.9 0.9) (thickness 0.12)))")
    a("\t)")
    a(f'\t(property "Value" "{name}"')
    a(f"\t\t(at 0 {DIP16_BODY_L / 2 + 1.6} 0)")
    a('\t\t(layer "F.Fab")')
    a("\t\t(effects (font (size 0.9 0.9) (thickness 0.12)))")
    a("\t)")
    a("\t(attr through_hole)")
    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
        a("\t(fp_rect")
        hxr = DIP16_SILK_HX if layer.endswith("SilkS") else DIP16_BODY_W / 2 + 0.3
        a(f"		(start {-hxr} {-DIP16_BODY_L / 2 - 0.3})")
        a(f"		(end {hxr} {DIP16_BODY_L / 2 + 0.3})")
        a(f"\t\t(stroke (width {w}) (type solid))")
        a("\t\t(fill none)")
        a(f'\t\t(layer "{layer}")')
        a("\t)")
    a("\t(fp_arc")
    a(f"\t\t(start {-DIP16_BODY_W / 2} {y0})")
    a(f"\t\t(mid 0 {y0 - 1.2})")
    a(f"\t\t(end {DIP16_BODY_W / 2} {y0})")
    a("\t\t(stroke (width 0.12) (type solid))")
    a('\t\t(layer "F.SilkS")')
    a("\t)")
    a(f'\t(fp_text user "{silk_label}"')
    a("\t\t(at 0 0 0)")
    a('\t\t(layer "F.SilkS")')
    a('\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))')
    a("\t)")
    for i in range(8):
        num = i + 1
        y = y0 + i * PITCH
        shape = "rect" if i == 0 else "oval"
        a(f'\t(pad "{num}" thru_hole {shape}')
        a(f"\t\t(at {-hx} {y})")
        a(f"\t\t(size {DIP16_PAD_W} {DIP16_PAD_H})")
        a(f"\t\t(drill {DIP16_DRILL})")
        a('\t\t(layers "*.Cu" "*.Mask")')
        a("\t)")
    for i in range(8):
        num = 16 - i
        y = y0 + i * PITCH
        a(f'\t(pad "{num}" thru_hole oval')
        a(f"\t\t(at {hx} {y})")
        a(f"\t\t(size {DIP16_PAD_W} {DIP16_PAD_H})")
        a(f"\t\t(drill {DIP16_DRILL})")
        a('\t\t(layers "*.Cu" "*.Mask")')
        a("\t)")
    a(")")
    out = PRETTY / f"{name}.kicad_mod"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def write_uln2003_footprint() -> Path:
    return write_dip16_footprint(
        "ULN2003AN",
        "ULN2003AN DIP-16 darlington array for 28BYJ-48 (COM=+12V)",
        "ULN2003",
    )


def write_74hc595_footprint() -> Path:
    return write_dip16_footprint(
        "74HC595",
        "74HC595 DIP-16 shift register (VCC=+3V3, /OE shared)",
        "74HC595",
    )


def write_l298n_footprint() -> Path:
    """Dead code: legacy DRV8871 — board uses ULN2003AN instead."""
    return write_uln2003_footprint()



def write_mini560_footprint() -> Path:
    """THT landing for MP1584EN 22x17 mm — Shopee 41383641614 fixed 5V."""
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
        '\t(descr "MP1584EN mini buck 22x17mm fixed 5V Shopee 41383641614. '
        '8x THT pad (dual hole/pin), span 18.54x10.67mm.")'
    )
    a('\t(tags "MP1584EN buck DC-DC 5V module carrier Shopee")')
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
    a('\t(property "Description" "MP1584EN 12V to 5V fixed Shopee 41383641614"')
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
    a(f"\t\t(at {-MP1584_PAD_X - 2.8} 0 0)")
    a('\t\t(layer "F.SilkS")')
    a('\t\t(effects (font (size 0.8 0.8) (thickness 0.1)) (justify right))')
    a("\t)")
    a('\t(fp_text user "OUT5V"')
    a(f"\t\t(at {MP1584_PAD_X + 2.8} 0 0)")
    a('\t\t(layer "F.SilkS")')
    a('\t\t(effects (font (size 0.8 0.8) (thickness 0.1)) (justify left))')
    a("\t)")
    a('\t(fp_text user "MP1584"')
    a("\t\t(at 0 0 0)")
    a('\t\t(layer "F.SilkS")')
    a('\t\t(effects (font (size 0.9 0.9) (thickness 0.12)))')
    a("\t)")

    for num, name, x, y in MP1584_PADS:
        shape = "rect" if num == "1" and y > 0 else "circle"
        a(f'\t(pad "{num}" thru_hole {shape}')
        a(f"\t\t(at {x} {y})")
        a("\t\t(size 1.8 1.8)")
        a("\t\t(drill 1.0)")
        a('\t\t(layers "*.Cu" "*.Mask")')
        a("\t\t(remove_unused_layers no)")
        a("\t)")
    for num, name, x, y in [
        ("1", "VIN+", -MP1584_PAD_X, MP1584_PAD_Y_MID),
        ("2", "VIN-", -MP1584_PAD_X, -MP1584_PAD_Y_MID),
        ("3", "VOUT-", MP1584_PAD_X, -MP1584_PAD_Y_MID),
        ("4", "VOUT+", MP1584_PAD_X, MP1584_PAD_Y_MID),
    ]:
        a(f'\t(fp_text user "{name}"')
        j = "right" if x < 0 else "left"
        a(f"\t\t(at {x - 2.5 if x < 0 else x + 2.5} {y} 0)")
        a('\t\t(layer "F.SilkS")')
        a(f'\t\t(effects (font (size 0.8 0.8) (thickness 0.1)) (justify {j}))')
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
    a("\t\t(at 0 -5.0 0)")
    a('\t\t(layer "F.SilkS")')
    a("\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a("\t)")
    a('\t(property "Value" "PTC_3A"')
    a("\t\t(at 0 5.0 0)")
    a('\t\t(layer "F.SilkS")')
    a("\t\t(effects (font (size 0.8 0.8) (thickness 0.1)))")
    a("\t)")
    a("\t(attr through_hole)")
    a('\t(fp_rect (start -4.2 -4.2) (end 4.2 4.2) '
      '(stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))')
    a('\t(fp_circle (center 0 0) (end 0 -3.5) '
      '(stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))')
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
    a("\t\t(at 0 -2.6 0)")
    a('\t\t(layer "F.SilkS")')
    a("\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a("\t)")
    a('\t(property "Value" "P6KE15A"')
    a("\t\t(at 0 2.6 0)")
    a('\t\t(layer "F.SilkS")')
    a("\t\t(effects (font (size 0.8 0.8) (thickness 0.1)))")
    a("\t)")
    a("\t(attr through_hole)")
    a('\t(fp_rect (start -3.2 -1.5) (end 3.2 1.5) '
      '(stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))')
    a('\t(fp_line (start 2.2 -1.2) (end 2.2 1.2) '
      '(stroke (width 0.12) (type solid)) (layer "F.SilkS"))')
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
        '"MP1584EN buck 12V→5V fixed Shopee 41383641614"'
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
        # MS1/MS2/PDN/PDN2/CLK exist on the module and on the footprint. They
        # are left unconnected here, but the symbol still has to declare them:
        # a pad with no matching pin is a schematic-parity error.
        ("2", "MS1", "input", -15.24, -10.16, 0),
        ("3", "MS2", "input", -15.24, -12.7, 0),
        ("4", "PDN", "input", -15.24, -15.24, 0),
        ("5", "PDN2", "input", -15.24, -17.78, 0),
        ("6", "CLK", "input", -15.24, -20.32, 0),
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




    # --- ULN2003AN DIP-16 ---
    a('\t(symbol "ULN2003AN"')
    a("\t\t(exclude_from_sim no)")
    a("\t\t(in_bom yes)")
    a("\t\t(on_board yes)")
    a("\t\t(in_pos_files yes)")
    a('\t\t(property "Reference" "U"')
    a("\t\t\t(at 0 12.7 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Value" "ULN2003AN"')
    a("\t\t\t(at 0 -12.7 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Footprint" "ESP32_Carrier:ULN2003AN"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Description" "ULN2003AN DIP-16 for 28BYJ-48; COM=+12V"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(symbol "ULN2003AN_0_1"')
    a("\t\t\t(rectangle")
    a("\t\t\t\t(start -10.16 10.16)")
    a("\t\t\t\t(end 10.16 -10.16)")
    a("\t\t\t\t(stroke (width 0.254) (type default))")
    a("\t\t\t\t(fill (type background))")
    a("\t\t\t)")
    a('\t\t\t(text "ULN2003"')
    a("\t\t\t\t(at 0 0 0)")
    a("\t\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t\t)")
    a("\t\t)")
    a('\t\t(symbol "ULN2003AN_1_1"')
    for num, name, etype, x, y, rot in [
        ("1", "IN1", "input", -15.24, 8.89, 0),
        ("2", "IN2", "input", -15.24, 6.35, 0),
        ("3", "IN3", "input", -15.24, 3.81, 0),
        ("4", "IN4", "input", -15.24, 1.27, 0),
        ("5", "IN5", "input", -15.24, -1.27, 0),
        ("6", "IN6", "input", -15.24, -3.81, 0),
        ("7", "IN7", "input", -15.24, -6.35, 0),
        ("8", "GND", "power_in", -15.24, -8.89, 0),
        ("9", "COM", "power_in", 15.24, -8.89, 180),
        ("10", "OUT7", "passive", 15.24, -6.35, 180),
        ("11", "OUT6", "passive", 15.24, -3.81, 180),
        ("12", "OUT5", "passive", 15.24, -1.27, 180),
        ("13", "OUT4", "passive", 15.24, 1.27, 180),
        ("14", "OUT3", "passive", 15.24, 3.81, 180),
        ("15", "OUT2", "passive", 15.24, 6.35, 180),
        ("16", "OUT1", "passive", 15.24, 8.89, 180),
    ]:
        a(f"\t\t\t(pin {etype} line")
        a(f"\t\t\t\t(at {x} {y} {rot})")
        a("\t\t\t\t(length 5.08)")
        a(f'\t\t\t\t(name "{name}" (effects (font (size 1.016 1.016))))')
        a(f'\t\t\t\t(number "{num}" (effects (font (size 1.016 1.016))))')
        a("\t\t\t)")
    a("\t\t)")
    a("\t)")

    # --- 74HC595 DIP-16 ---
    a('\t(symbol "74HC595"')
    a("\t\t(exclude_from_sim no)")
    a("\t\t(in_bom yes)")
    a("\t\t(on_board yes)")
    a("\t\t(in_pos_files yes)")
    a('\t\t(property "Reference" "U"')
    a("\t\t\t(at 0 12.7 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Value" "74HC595"')
    a("\t\t\t(at 0 -12.7 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Footprint" "ESP32_Carrier:74HC595"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Description" "74HC595 shift register VCC=3V3"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(symbol "74HC595_0_1"')
    a("\t\t\t(rectangle")
    a("\t\t\t\t(start -10.16 10.16)")
    a("\t\t\t\t(end 10.16 -10.16)")
    a("\t\t\t\t(stroke (width 0.254) (type default))")
    a("\t\t\t\t(fill (type background))")
    a("\t\t\t)")
    a('\t\t\t(text "74HC595"')
    a("\t\t\t\t(at 0 0 0)")
    a("\t\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t\t)")
    a("\t\t)")
    a('\t\t(symbol "74HC595_1_1"')
    for num, name, etype, x, y, rot in [
        ("1", "Q1", "output", -15.24, 8.89, 0),
        ("2", "Q2", "output", -15.24, 6.35, 0),
        ("3", "Q3", "output", -15.24, 3.81, 0),
        ("4", "Q4", "output", -15.24, 1.27, 0),
        ("5", "Q5", "output", -15.24, -1.27, 0),
        ("6", "Q6", "output", -15.24, -3.81, 0),
        ("7", "Q7", "output", -15.24, -6.35, 0),
        ("8", "GND", "power_in", -15.24, -8.89, 0),
        ("9", "QH", "output", 15.24, -8.89, 180),
        ("10", "SRCLR", "input", 15.24, -6.35, 180),
        ("11", "SRCLK", "input", 15.24, -3.81, 180),
        ("12", "RCLK", "input", 15.24, -1.27, 180),
        ("13", "OE", "input", 15.24, 1.27, 180),
        ("14", "SER", "input", 15.24, 3.81, 180),
        ("15", "Q0", "output", 15.24, 6.35, 180),
        ("16", "VCC", "power_in", 15.24, 8.89, 180),
    ]:
        a(f"\t\t\t(pin {etype} line")
        a(f"\t\t\t\t(at {x} {y} {rot})")
        a("\t\t\t\t(length 5.08)")
        a(f'\t\t\t\t(name "{name}" (effects (font (size 1.016 1.016))))')
        a(f'\t\t\t\t(number "{num}" (effects (font (size 1.016 1.016))))')
        a("\t\t\t)")
    a("\t\t)")
    a("\t)")

    a('\t(symbol "Conn_1x05_BYJ"')
    a("\t\t(exclude_from_sim no)")
    a("\t\t(in_bom yes)")
    a("\t\t(on_board yes)")
    a("\t\t(in_pos_files yes)")
    a('\t\t(property "Reference" "J"')
    a("\t\t\t(at 0 7.62 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Value" "Conn_1x05_BYJ"')
    a("\t\t\t(at 0 -7.62 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Footprint" "ESP32_Carrier:PinHeader_1x05_BYJ"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Description" "TOP: 28BYJ-48 JST-XH 5P A B C D +12V"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(symbol "Conn_1x05_BYJ_0_1"')
    a("\t\t\t(rectangle")
    a("\t\t\t\t(start -2.54 6.35)")
    a("\t\t\t\t(end 2.54 -6.35)")
    a("\t\t\t\t(stroke (width 0.254) (type default))")
    a("\t\t\t\t(fill (type background))")
    a("\t\t\t)")
    a('\t\t\t(text "BYJ"')
    a("\t\t\t\t(at 0 0 0)")
    a("\t\t\t\t(effects (font (size 1.016 1.016)))")
    a("\t\t\t)")
    a("\t\t)")
    a('\t\t(symbol "Conn_1x05_BYJ_1_1"')
    for num, name, y in [("1", "A", 5.08), ("2", "B", 2.54), ("3", "C", 0), ("4", "D", -2.54), ("5", "+12V", -5.08)]:
        a("\t\t\t(pin passive line")
        a(f"\t\t\t\t(at 0 {y} 90)")
        a("\t\t\t\t(length 2.54)")
        a(f'\t\t\t\t(name "{name}" (effects (font (size 1.016 1.016))))')
        a(f'\t\t\t\t(number "{num}" (effects (font (size 1.016 1.016))))')
        a("\t\t\t)")
    a("\t\t)")
    a("\t)")

    a('\t(symbol "Conn_1x04_Endstop"')
    a("\t\t(exclude_from_sim no)")
    a("\t\t(in_bom yes)")
    a("\t\t(on_board yes)")
    a("\t\t(in_pos_files yes)")
    a('\t\t(property "Reference" "J"')
    a("\t\t\t(at 0 7.62 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Value" "Conn_1x04_Endstop"')
    a("\t\t\t(at 0 -7.62 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a(f'\t\t(property "Footprint" "ESP32_Carrier:{ENDSTOP_FP}"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a(
        '\t\t(property "Description" '
        '"TOP: CNC endstop 1x04; VCC/GND NC; SIG+SNS dry NC to opto"'
    )
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(symbol "Conn_1x04_Endstop_0_1"')
    a("\t\t\t(rectangle")
    a("\t\t\t\t(start -2.54 5.08)")
    a("\t\t\t\t(end 2.54 -5.08)")
    a("\t\t\t\t(stroke (width 0.254) (type default))")
    a("\t\t\t\t(fill (type background))")
    a("\t\t\t)")
    a('\t\t\t(text "HOME"')
    a("\t\t\t\t(at 0 0 0)")
    a("\t\t\t\t(effects (font (size 1.016 1.016)))")
    a("\t\t\t)")
    a("\t\t)")
    a('\t\t(symbol "Conn_1x04_Endstop_1_1"')
    for num, name, y in [
        ("1", "VCC", 3.81),
        ("2", "GND", 1.27),
        ("3", "SIG", -1.27),
        ("4", "SNS", -3.81),
    ]:
        a("\t\t\t(pin passive line")
        a(f"\t\t\t\t(at 0 {y} 90)")
        a("\t\t\t\t(length 2.54)")
        a(f'\t\t\t\t(name "{name}" (effects (font (size 1.016 1.016))))')
        a(f'\t\t\t\t(number "{num}" (effects (font (size 1.016 1.016))))')
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
    a('\t\t(property "Description" "TOP: Autonics BUP-30S NPN 12V -> OPTO_IN4"')
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

    # --- PC817 DIP-4 (discrete) ---
    a('\t(symbol "PC817_DIP4"')
    a("\t\t(pin_names")
    a("\t\t\t(offset 1.016)")
    a("\t\t)")
    a("\t\t(exclude_from_sim no)")
    a("\t\t(in_bom yes)")
    a("\t\t(on_board yes)")
    a('\t\t(property "Reference" "U"')
    a("\t\t\t(at 0 5.08 0)")
    a('\t\t\t(effects (font (size 1.27 1.27)))')
    a("\t\t)")
    a('\t\t(property "Value" "PC817_DIP4"')
    a("\t\t\t(at 0 -5.08 0)")
    a('\t\t\t(effects (font (size 1.27 1.27)))')
    a("\t\t)")
    a('\t\t(property "Footprint" "ESP32_Carrier:PC817_DIP4"')
    a("\t\t\t(at 0 0 0)")
    a('\t\t\t(effects (font (size 1.27 1.27)) (hide yes))')
    a("\t\t)")
    a('\t\t(property "Datasheet" "~"')
    a("\t\t\t(at 0 0 0)")
    a('\t\t\t(effects (font (size 1.27 1.27)) (hide yes))')
    a("\t\t)")
    a('\t\t(property "Description" "PC817 optocoupler DIP-4 A/K/E/C"')
    a("\t\t\t(at 0 0 0)")
    a('\t\t\t(effects (font (size 1.27 1.27)) (hide yes))')
    a("\t\t)")
    a('\t\t(symbol "PC817_DIP4_0_1"')
    a("\t\t\t(rectangle")
    a("\t\t\t\t(start -5.08 3.81)")
    a("\t\t\t\t(end 5.08 -3.81)")
    a("\t\t\t\t(stroke (width 0.254) (type default))")
    a("\t\t\t\t(fill (type background))")
    a("\t\t\t)")
    a("\t\t)")
    a('\t\t(symbol "PC817_DIP4_1_1"')
    for num, name, x, y, etype in [
        ("1", "A", -7.62, 2.54, "passive"),
        ("2", "K", -7.62, -2.54, "passive"),
        ("3", "E", 7.62, -2.54, "passive"),
        ("4", "C", 7.62, 2.54, "passive"),
    ]:
        a(f'\t\t\t(pin {etype} line')
        a(f"\t\t\t\t(at {x} {y} {180 if x < 0 else 0})")
        a("\t\t\t\t(length 2.54)")
        a(f'\t\t\t\t(name "{name}" (effects (font (size 1.016 1.016))))')
        a(f'\t\t\t\t(number "{num}" (effects (font (size 1.016 1.016))))')
        a("\t\t\t)")
    a("\t\t)")
    a("\t)")

    # --- Top field header for opto IN (1x06 HOME+BUP) ---
    a(f'\t(symbol "{OPTO_FIELD_SYM}"')
    a("\t\t(exclude_from_sim no)")
    a("\t\t(in_bom yes)")
    a("\t\t(on_board yes)")
    a("\t\t(in_pos_files yes)")
    a('\t\t(property "Reference" "J"')
    a("\t\t\t(at 0 15.24 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a(f'\t\t(property "Value" "{OPTO_FIELD_SYM}"')
    a("\t\t\t(at 0 -15.24 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a(f'\t\t(property "Footprint" "ESP32_Carrier:{OPTO_FIELD_FP}"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Description" "TOP: opto field GND/VCC + IN1-4 (HOME+BUP)"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a(f'\t\t(symbol "{OPTO_FIELD_SYM}_0_1"')
    a("\t\t\t(rectangle")
    a("\t\t\t\t(start -2.54 7.62)")
    a("\t\t\t\t(end 2.54 -7.62)")
    a("\t\t\t\t(stroke (width 0.254) (type default))")
    a("\t\t\t\t(fill (type background))")
    a("\t\t\t)")
    a('\t\t\t(text "OPTO_IN"')
    a("\t\t\t\t(at 0 0 0)")
    a("\t\t\t\t(effects (font (size 1.016 1.016)))")
    a("\t\t\t)")
    a("\t\t)")
    a(f'\t\t(symbol "{OPTO_FIELD_SYM}_1_1"')
    for i, (num, name) in enumerate(OPTO_FIELD_HEADER):
        y = 6.35 - i * 2.54
        a("\t\t\t(pin passive line")
        a(f"\t\t\t\t(at 0 {y} 90)")
        a("\t\t\t\t(length 2.54)")
        a(f'\t\t\t\t(name "{name}" (effects (font (size 1.016 1.016))))')
        a(f'\t\t\t\t(number "{num}" (effects (font (size 1.016 1.016))))')
        a("\t\t\t)")
    a("\t\t)")
    a("\t)")

    # --- TFT: Conn_1x09 LCD + Conn_1x05 touch (MSP3520 order) ---
    def _emit_conn_header_sym(sym: str, fp: str, header: list, title: str, descr: str):
        n = len(header)
        a(f'\t(symbol "{sym}"')
        a("\t\t(exclude_from_sim no)")
        a("\t\t(in_bom yes)")
        a("\t\t(on_board yes)")
        a("\t\t(in_pos_files yes)")
        a('\t\t(property "Reference" "J"')
        a("\t\t\t(at 0 10.16 0)")
        a("\t\t\t(effects (font (size 1.27 1.27)))")
        a("\t\t)")
        a(f'\t\t(property "Value" "{sym}"')
        a("\t\t\t(at 0 -10.16 0)")
        a("\t\t\t(effects (font (size 1.27 1.27)))")
        a("\t\t)")
        a(f'\t\t(property "Footprint" "ESP32_Carrier:{fp}"')
        a("\t\t\t(at 0 0 0)")
        a("\t\t\t(hide yes)")
        a("\t\t\t(effects (font (size 1.27 1.27)))")
        a("\t\t)")
        a(f'\t\t(property "Description" "{descr}"')
        a("\t\t\t(at 0 0 0)")
        a("\t\t\t(hide yes)")
        a("\t\t\t(effects (font (size 1.27 1.27)))")
        a("\t\t)")
        half = (n - 1) * 1.27 + 1.27
        a(f'\t\t(symbol "{sym}_0_1"')
        a("\t\t\t(rectangle")
        a(f"\t\t\t\t(start -2.54 {half})")
        a(f"\t\t\t\t(end 2.54 {-half})")
        a("\t\t\t\t(stroke (width 0.254) (type default))")
        a("\t\t\t\t(fill (type background))")
        a("\t\t\t)")
        a(f'\t\t\t(text "{title}"')
        a("\t\t\t\t(at 0 0 0)")
        a("\t\t\t\t(effects (font (size 1.016 1.016)))")
        a("\t\t\t)")
        a("\t\t)")
        a(f'\t\t(symbol "{sym}_1_1"')
        for (num, name), y in zip(
            header,
            [(n - 1) * 1.27 - i * 2.54 for i in range(n)],
        ):
            a("\t\t\t(pin passive line")
            a(f"\t\t\t\t(at 0 {y} 90)")
            a("\t\t\t\t(length 2.54)")
            a(f'\t\t\t\t(name "{name}" (effects (font (size 1.27 1.27))))')
            a(f'\t\t\t\t(number "{num}" (effects (font (size 1.27 1.27))))')
            a("\t\t\t)")
        a("\t\t)")
        a("\t)")

    _emit_conn_header_sym(
        TFT_LCD_SYM, TFT_LCD_FP, TFT_LCD_HEADER, "TFT LCD",
        "MSP3520 pins1-9 LCD: VCC GND CS RESET DC SDI SCK LED SDO",
    )
    _emit_conn_header_sym(
        TFT_TP_SYM, TFT_TP_FP, TFT_TP_HEADER, "TFT TP",
        "MSP3520 pins10-14 touch: T_CLK T_CS T_DIN T_DO T_IRQ",
    )

    # --- J18 EC11 encoder ---
    a(f'\t(symbol "{ENC_SYM}"')
    a("\t\t(exclude_from_sim no)")
    a("\t\t(in_bom yes)")
    a("\t\t(on_board yes)")
    a("\t\t(in_pos_files yes)")
    a('\t\t(property "Reference" "J"')
    a("\t\t\t(at 0 7.62 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a(f'\t\t(property "Value" "{ENC_SYM}"')
    a("\t\t\t(at 0 -7.62 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a(f'\t\t(property "Footprint" "ESP32_Carrier:{ENC_FP}"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a(
        '\t\t(property "Description" '
        '"Wall-mount EC11/KY-040 jack: GND 3V3 ENC_A ENC_B (no SW)"'
    )
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    _eh = (ENC_PINS - 1) * 1.27 + 1.27
    a(f'\t\t(symbol "{ENC_SYM}_0_1"')
    a("\t\t\t(rectangle")
    a(f"\t\t\t\t(start -2.54 {_eh})")
    a(f"\t\t\t\t(end 2.54 {-_eh})")
    a("\t\t\t\t(stroke (width 0.254) (type default))")
    a("\t\t\t\t(fill (type background))")
    a("\t\t\t)")
    a('\t\t\t(text "ENC"')
    a("\t\t\t\t(at 0 0 0)")
    a("\t\t\t\t(effects (font (size 1.016 1.016)))")
    a("\t\t\t)")
    a("\t\t)")
    a(f'\t\t(symbol "{ENC_SYM}_1_1"')
    for (num, name), y in zip(
        ENC_HEADER,
        [(ENC_PINS - 1) * 1.27 - i * 2.54 for i in range(ENC_PINS)],
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
    j18_uuid = uid()
    j23_uuid = uid()

    emb = "\n".join(
        [
            _embed_from_lib("TerminalBlock_2P"),
            _embed_from_lib("MP1584_5V3A"),
            _embed_from_lib("ESP32_S3_DevKitC_1"),
            _embed_from_lib("Conn_1x04_Motor"),
            _embed_from_lib(TFT_LCD_SYM),
            _embed_from_lib(TFT_TP_SYM),
            _embed_from_lib(ENC_SYM),
            _embed_from_lib("TMC2209_StepStick"),
            _embed_from_lib("PC817_DIP4"),
            _embed_from_lib("74HC595"),
            _embed_from_lib("ULN2003AN"),
            _embed_from_lib(BYJ_SYM),
            _embed_from_lib(ENDSTOP_SYM),
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
    j18 = (265.0, 139.7)

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
        """Global label, not a local one.

        KiCad names a local label on the root sheet "/GND" while the PCB
        carries "GND" — that mismatch alone accounted for 32 of the
        net_conflict errors schematic parity reports. Global labels keep both
        sides on exactly the same net names.
        """
        # Match the PCB net table exactly: power rails are bare (GND, +12V),
        # every signal net carries a leading slash (/STEP). Parity compares the
        # strings, so "STEP" here and "/STEP" on the board is a conflict.
        if not name.startswith(("+", "/")) and name not in ("GND",):
            name = "/" + name
        return (
            f'\t(global_label "{name}"\n'
            "\t\t(shape input)\n"
            f"\t\t(at {x} {y} 0)\n"
            "\t\t(effects (font (size 1.27 1.27)) (justify left))\n"
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
        '\t\t(title "ESP32-S3 Baseboard - MP1584 + TMC + ULN2003 direct GPIO")',
        '\t\t(comment 1 "BOTTOM: J1 U2 U3 U5-7 U1 | TOP: J5-7 HOME TFT")',
        '\t\t(comment 2 "ULN COM=+12V; 595 OE R4; PC817 DIP-4 x4")',
        "\t)",
        "\t(lib_symbols",
        emb,
        "\t)",
        text("BOTTOM: J1 12V + MP1584EN + TMC2209 + ESP32", 20.32, 22.86, 1.27),
        text("TOP: J17+J23 TFT / J18 ENC / J15 buzzer / J16 MOSFET", 20.32, 120.65, 1.27),
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
        # J17 TFT LCD 1×9 + J23 touch 1×5 (MSP3520 contiguous column)
        f'\t(symbol (lib_id "ESP32_Carrier:{TFT_LCD_SYM}") (at {j3[0]} {j3[1]} 0) (unit 1)',
        f'\t\t(uuid "{j3_uuid}")',
        f'\t\t(property "Reference" "J17" (at {j3[0]} {j3[1] - 12.7} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)))",
        "\t\t)",
        f'\t\t(property "Value" "TFT_LCD_1x09" (at {j3[0]} {j3[1] + 15.24} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)))",
        "\t\t)",
        f'\t\t(property "Footprint" "ESP32_Carrier:{TFT_LCD_FP}" (at {j3[0]} {j3[1]} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\t\t)",
        f'\t\t(property "Datasheet" "~" (at {j3[0]} {j3[1]} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\t\t)",
        *[f'\t\t(pin "{n}" (uuid "{uid()}"))' for n in range(1, TFT_LCD_PINS + 1)],
        "\t\t(instances",
        f'\t\t\t(project "esp32_baseboard" (path "/{sch_uuid}" (reference "J17") (unit 1)))',
        "\t\t)",
        "\t)",
        f'\t(symbol (lib_id "ESP32_Carrier:{TFT_TP_SYM}") (at {j3[0] + 15.24} {j3[1]} 0) (unit 1)',
        f'\t\t(uuid "{j23_uuid}")',
        f'\t\t(property "Reference" "J23" (at {j3[0] + 15.24} {j3[1] - 10.16} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)))",
        "\t\t)",
        f'\t\t(property "Value" "TFT_TP_1x05" (at {j3[0] + 15.24} {j3[1] + 12.7} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)))",
        "\t\t)",
        f'\t\t(property "Footprint" "ESP32_Carrier:{TFT_TP_FP}" (at {j3[0] + 15.24} {j3[1]} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\t\t)",
        f'\t\t(property "Datasheet" "~" (at {j3[0] + 15.24} {j3[1]} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\t\t)",
        *[f'\t\t(pin "{n}" (uuid "{uid()}"))' for n in range(1, TFT_TP_PINS + 1)],
        "\t\t(instances",
        f'\t\t\t(project "esp32_baseboard" (path "/{sch_uuid}" (reference "J23") (unit 1)))',
        "\t\t)",
        "\t)",
        # J18 EC11 encoder (TOP)
        f'\t(symbol (lib_id "ESP32_Carrier:{ENC_SYM}") (at {j18[0]} {j18[1]} 0) (unit 1)',
        f'\t\t(uuid "{j18_uuid}")',
        f'\t\t(property "Reference" "J18" (at {j18[0]} {j18[1] - 10.16} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)))",
        "\t\t)",
        f'\t\t(property "Value" "EC11_ENC" (at {j18[0]} {j18[1] + 10.16} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)))",
        "\t\t)",
        f'\t\t(property "Footprint" "ESP32_Carrier:{ENC_FP}" (at {j18[0]} {j18[1]} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\t\t)",
        f'\t\t(property "Datasheet" "~" (at {j18[0]} {j18[1]} 0)',
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\t\t)",
        *[f'\t\t(pin "{n}" (uuid "{uid()}"))' for n in range(1, ENC_PINS + 1)],
        "\t\t(instances",
        f'\t\t\t(project "esp32_baseboard" (path "/{sch_uuid}" (reference "J18") (unit 1)))',
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

    # --- Discrete PC817 U41-U48 (schematic labels; PCB is source of truth) ---
    parts.append(text("U41-U44 PC817 DIP-4 + 2k2/10k (HOME×3+BUP)", 210.0, 55.88, 1.27))
    parts.append(text("IN: HOME×3 + BUP only (no field)", 210.0, 61.0, 1.0))
    for i, (uref, _rl, _rp, _iid, inet, _oid, onet, _aid, _anet, tag) in enumerate(OPTO_CH):
        col, row = i % 4, i // 4
        at = (240.0 + col * 25.4, 88.9 + row * 25.4)
        su = uid()
        parts += [
            f'\t(symbol (lib_id "ESP32_Carrier:PC817_DIP4") (at {at[0]} {at[1]} 0) (unit 1)',
            f'\t\t(uuid "{su}")',
            f'\t\t(property "Reference" "{uref}" (at {at[0]} {at[1] - 6.35} 0)',
            "\t\t\t(effects (font (size 1.27 1.27)))",
            "\t\t)",
            f'\t\t(property "Value" "PC817" (at {at[0]} {at[1] + 6.35} 0)',
            "\t\t\t(effects (font (size 1.27 1.27)))",
            "\t\t)",
            f'\t\t(property "Footprint" "ESP32_Carrier:PC817_DIP4" (at {at[0]} {at[1]} 0)',
            "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
            "\t\t)",
            f'\t\t(pin "1" (uuid "{uid()}"))',
            f'\t\t(pin "2" (uuid "{uid()}"))',
            f'\t\t(pin "3" (uuid "{uid()}"))',
            f'\t\t(pin "4" (uuid "{uid()}"))',
            "\t\t(instances",
            f'\t\t\t(project "esp32_baseboard" (path "/{sch_uuid}" (reference "{uref}") (unit 1)))',
            "\t\t)",
            "\t)",
        ]
        parts.append(label(inet.lstrip("/"), at[0] - 12.7, at[1] + 2.54))
        parts.append(label(onet.lstrip("/"), at[0] + 10.16, at[1] + 2.54))
        parts.append(text(tag, at[0] - 4, at[1] - 10.16, 1.0))

    # EC11: IO47=ENC_A, IO45=ENC_B (J18). SW unused.
    def j18_pin(n: int) -> tuple[float, float]:
        ly = (ENC_PINS - 1) * 1.27 - (n - 1) * 2.54
        return (j18[0], j18[1] - ly)

    parts.append(
        text(
            "J18 ENC: wall-mount EC11 → GND/3V3/A/B; CLK=IO38 DT=IO41; no SW",
            210.0, 48.0, 1.0,
        )
    )
    parts += wire_path(u1_pin(PIN_BY_NAME["IO38"]), (j18_pin(3)[0] - 8, u1_pin(PIN_BY_NAME["IO38"])[1]), j18_pin(3))
    parts.append(label("ENC_A", j18_pin(3)[0] - 6, j18_pin(3)[1]))
    parts += wire_path(u1_pin(PIN_BY_NAME["IO41"]), (j18_pin(4)[0] - 6, u1_pin(PIN_BY_NAME["IO41"])[1]), j18_pin(4))
    parts.append(label("ENC_B", j18_pin(4)[0] - 6, j18_pin(4)[1]))
    parts += wire_path(j18_pin(1), (j18_pin(1)[0] - 10, j18_pin(1)[1]), (j18_pin(1)[0] - 10, ygnd), (u1_gnd_l[0], ygnd))
    parts += wire_path(j18_pin(2), (j18_pin(2)[0] - 12, j18_pin(2)[1]), (j18_pin(2)[0] - 12, y3v3), (u1_3v3[0], y3v3))

    # --- ULN2003 + 74HC595 + 28BYJ (schematic net labels; PCB is source of truth) ---
    parts.append(text("U10=74HC595-24IO module (Shopee) RIGHT of ESP32; U5-U7 ULN; J5-J7 BYJ", 20.32, 185.0, 1.27))
    parts.append(text("CTRL LDEN/GND/VCC/LDSI/LDSTR/LDSCK = OE/GND/3V3/SER/RCLK/SRCLK; R4 LDEN PU", 20.32, 190.5, 1.0))
    parts.append(text("1_Q0-3->U5; 1_Q4-7->U6; 2_Q0-3->U7; shift 3 bytes; COM=+12V", 20.32, 195.58, 1.0))
    # HOME endstop jacks J8/J10/J12 — 1×04 (VCC/GND NC; SIG+SNS used)
    # Symbol pin y: 1=VCC +3.81, 2=GND +1.27, 3=SIG −1.27, 4=SNS −3.81
    # World pin = (at_x, at_y − pin_y) at 0° (same convention as other Conn_*).
    home_place = [
        ("J8", 165.1, 203.2, 1, "HOME1"),
        ("J10", 165.1, 228.6, 2, "HOME2"),
        ("J12", 165.1, 254.0, 3, "HOME3"),
    ]
    for jref_l, xjl, yj, ch, tag in home_place:
        ju = uid()
        psig = (xjl, yj - (-1.27))  # pin3 SIG
        psns = (xjl, yj - (-3.81))  # pin4 SNS
        parts += [
            f'\t(symbol (lib_id "ESP32_Carrier:{ENDSTOP_SYM}") (at {xjl} {yj} 0) (unit 1)',
            f'\t\t(uuid "{ju}")',
            f'\t\t(property "Reference" "{jref_l}" (at {xjl} {yj - 10.16} 0)',
            "\t\t\t(effects (font (size 1.27 1.27)))",
            "\t\t)",
            f'\t\t(property "Value" "END_{tag}" (at {xjl} {yj + 10.16} 0)',
            "\t\t\t(effects (font (size 1.27 1.27)))",
            "\t\t)",
            f'\t\t(property "Footprint" "ESP32_Carrier:{ENDSTOP_FP}" (at {xjl} {yj} 0)',
            "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
            "\t\t)",
            f'\t\t(pin "1" (uuid "{uid()}"))',
            f'\t\t(pin "2" (uuid "{uid()}"))',
            f'\t\t(pin "3" (uuid "{uid()}"))',
            f'\t\t(pin "4" (uuid "{uid()}"))',
            "\t\t(instances",
            f'\t\t\t(project "esp32_baseboard" (path "/{sch_uuid}" (reference "{jref_l}") (unit 1)))',
            "\t\t)",
            "\t)",
        ]
        # pin3 SIG → OPTO_INx; pin4 SNS → +12V_SNS (VCC/GND left NC on carrier)
        parts += wire_path(psig, (psig[0] + 5.08, psig[1]))
        parts.append(label(f"OPTO_IN{ch}", psig[0] + 5.08, psig[1]))
        parts += wire_path(psns, (psns[0], psns[1] - 2.54))
        parts.append(label("+12V_SNS", psns[0], psns[1] - 2.54))

    # --- Autonics BUP-30S (NPN) @12V -> OPTO_IN4 ---
    j14 = (95.25, 320.04)
    r1 = (120.65, 320.04)
    j14_uuid, r1_uuid = uid(), uid()
    parts.append(text("BUP-30S NPN -> OPTO_IN4 (was IN7)", 70.0, 304.8, 1.0))
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
    parts += wire_path(j14_12, (j14_12[0] - 5.08, j14_12[1]))
    parts.append(label("+12V_SNS", j14_12[0] - 5.08, j14_12[1]))
    parts += wire_path(j14_gnd, (j14_gnd[0] - 5.08, j14_gnd[1]))
    parts.append(label("GND", j14_gnd[0] - 5.08, j14_gnd[1]))
    parts += wire_path(j14_out, (j14_out[0] + 5.08, j14_out[1]))
    parts.append(label("OPTO_IN4", j14_out[0] + 5.08, j14_out[1]))
    parts += wire_path(r1_a, (r1_a[0], r1_a[1] - 2.54))
    parts.append(label("+12V_SNS", r1_a[0], r1_a[1] - 2.54))
    parts += wire_path(r1_b, (r1_b[0], r1_b[1] + 2.54))
    parts.append(label("OPTO_IN4", r1_b[0], r1_b[1] + 2.54))
    parts.append(f'\t(no_connect (at {j14_ctrl[0]} {j14_ctrl[1]}) (uuid "{uid()}"))')
    parts.append(text("CTRL: LightON->+12V / DarkON->GND", j14[0] - 5, j14[1] + 12.7, 1.0))

    # --- STAR POWER: RC filter +12V -> +12V_SNS ---
    parts.append(text("STAR: +12V_MOT (rong) / +12V_SNS qua R10=10R + C47u||100n", 20.32, 304.8, 1.0))
    # Net labels only: document filter (R10 C_SNS placed on PCB)
    parts.append(label("+12V", 38.1, 312.42))
    parts.append(label("+12V_SNS", 63.5, 312.42))
    parts.append(text("R10 10R + C10 47u + C11 100n (tren PCB)", 38.1, 317.5, 1.0))
    parts.append(text("Bulk C20 470u@TMC + C21 100u shared ULN COM (tren PCB)", 38.1, 322.58, 1.0))

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
        11: "/EN_TMC",
        12: "/MotA2",
        13: "/MotA1",
        14: "/MotB1",
        15: "/MotB2",
        16: "/OPTO_OUT1",
        17: "/OPTO_OUT2",
        18: "/OPTO_OUT3",
        19: "/OPTO_OUT4",
        25: "/OPTO_IN1",
        26: "/OPTO_IN2",
        27: "/OPTO_IN3",
        28: "/OPTO_IN4",  # BUP
        80: "/OPTO_A1",
        81: "/OPTO_A2",
        82: "/OPTO_A3",
        83: "/OPTO_A4",
        33: "/OPTO_GND_I",
        # 74HC595 control + Q outputs → ULN IN
        34: "SER",
        35: "SRCLK",
        36: "RCLK",
        37: "OE_595",
        39: "SR_Q0",
        40: "SR_Q1",
        41: "SR_Q2",
        42: "SR_Q3",
        43: "SR_Q4",
        44: "SR_Q5",
        45: "SR_Q6",
        63: "SR_Q7",
        64: "SR_Q8",
        65: "SR_Q9",
        66: "SR_Q10",
        67: "SR_Q11",
        # ULN OUT -> 28BYJ phases
        68: "BYJ1_A",
        69: "BYJ1_B",
        70: "BYJ1_C",
        71: "BYJ1_D",
        72: "BYJ2_A",
        73: "BYJ2_B",
        74: "BYJ2_C",
        75: "BYJ2_D",
        76: "BYJ3_A",
        77: "BYJ3_B",
        78: "BYJ3_C",
        79: "BYJ3_D",
        46: "+12V_SNS",
        47: "/TFT_SCK",
        48: "/TFT_MOSI",
        50: "/TFT_CS",
        51: "/TFT_DC",
        54: "/BUZZER",
        55: "/BLOWER",
        57: "+12V_RAW",
        52: "/TFT_MISO",
        53: "/T_CS",
        20: "/T_IRQ",
        58: "/TFT_RST",
        59: "/TFT_BL",
        60: "/ENC_B",
        61: "/BLW_RET",
        62: "/ENC_A",
    }

    def track(x1, y1, x2, y2, net, layer, w=0.25):
        if USE_MAZE_AUTOROUTE:
            return
        a("\t(segment")
        a(f"\t\t(start {x1} {y1})")
        a(f"\t\t(end {x2} {y2})")
        a(f"\t\t(width {w})")
        a(f'\t\t(layer "{layer}")')
        a(f"\t\t(net {net})")
        a(f'\t\t(uuid "{uid()}")')
        a("\t)")

    def via(x, y, net, drill=VIA12_DRILL, dia=VIA12_DIA):
        # No extra drill holes beyond component/header pins
        if USE_MAZE_AUTOROUTE:
            return
        a("\t(via")
        a(f"\t\t(at {x} {y})")
        a(f"\t\t(size {dia})")
        a(f"\t\t(drill {drill})")
        a('\t\t(layers "F.Cu" "B.Cu")')
        a(f"\t\t(net {net})")
        a(f'\t\t(uuid "{uid()}")')
        a("\t)")

    # Legacy helpers kept for call sites; with USE_MAZE_AUTOROUTE they no-op
    # (final copper comes from maze_router A* — same-layer bends allowed).
    def track_h(x1, x2, y, net, w=0.3):
        if abs(x1 - x2) < 1e-9:
            return
        track(x1, y, x2, y, net, "F.Cu", w)

    def track_v(x, y1, y2, net, w=0.3):
        if abs(y1 - y2) < 1e-9:
            return
        track(x, y1, x, y2, net, "B.Cu", w)

    def side_enter_pin(net, x_from, y_from, pin, w=0.3, side=-3.0, via_drill=0.4, via_dia=0.8):
        """PCB practice: approach beside header column, short H into target pad only.
        Never run B.Cu vertically on the pin column through neighbouring pins."""
        px, py = pin
        x_side = px + side
        if abs(x_from - x_side) > 1e-9:
            track_h(x_from, x_side, y_from, net, w)
            via(x_side, y_from, net, via_drill, via_dia)
        if abs(y_from - py) > 1e-9:
            track_v(x_side, y_from, py, net, w)
            via(x_side, py, net, via_drill, via_dia)
        track_h(x_side, px, py, net, w)

    def route_L(net, x1, y1, x2, y2, w=0.3, first="H", drill=0.4, dia=0.8):
        """L-bend: H on F.Cu, V on B.Cu, via at the corner (and no-op if axis-aligned)."""
        if abs(x1 - x2) < 1e-9 and abs(y1 - y2) < 1e-9:
            return
        if abs(y1 - y2) < 1e-9:
            track_h(x1, x2, y1, net, w)
            return
        if abs(x1 - x2) < 1e-9:
            track_v(x1, y1, y2, net, w)
            return
        if first == "H":
            track_h(x1, x2, y1, net, w)
            via(x2, y1, net, drill, dia)
            track_v(x2, y1, y2, net, w)
        else:
            track_v(x1, y1, y2, net, w)
            via(x1, y2, net, drill, dia)
            track_h(x1, x2, y2, net, w)

    # Long build notes go on Cmts.User, not the silkscreen: at 0.8 mm on a
    # 235x132 board they collide with the group boxes and the pads they sit
    # beside, and they are documentation rather than assembly markings.
    def gr_text(txt, x, y, layer, size=1.0, rot=0):
        # Descriptive text goes on the documentation layer, not the
        # silkscreen. Every part already prints its own reference and value
        # from its footprint; these extra notes only added 68 silk_overlap and
        # silk_over_copper warnings on a board this dense, and at 0.8 mm
        # crammed between the zone boxes they were not readable anyway.
        # Zone outlines (gr_box) stay on silk.
        if layer in ("F.SilkS", "B.SilkS"):
            layer = "Cmts.User"
        # Clamp to the fab's legibility floor: KiCad's board-setup silk minimum
        # is 0.8 mm, and anything under it is both a DRC warning and unreadable
        # on a real board. Back-layer text also has to be mirrored, or it reads
        # backwards once the board is flipped over.
        size = max(SILK_TEXT_MIN_MM, size)
        mirror = " " if layer.startswith("B.") else ""
        a(f'\t(gr_text "{txt}"')
        a(f"\t\t(at {x} {y} {rot})")
        a(f'\t\t(layer "{layer}")')
        a(
            f"\t\t(effects (font (size {size} {size}) "
            f"(thickness {max(0.15, size * 0.15)})){mirror})"
        )
        a(f'\t\t(uuid "{uid()}")')
        a("\t)")

    def gr_box(x0, y0, x1, y1, layer, w=0.12, color=None):
        # Zone outlines on F/B.SilkS remapped to Cmts — they are documentation.
        # Eco1/Eco2 keep the layer (cluster labels for the designer).
        if layer in ("F.SilkS", "B.SilkS"):
            layer = "Cmts.User"
        a("\t(gr_rect")
        a(f"\t\t(start {x0} {y0})")
        a(f"\t\t(end {x1} {y1})")
        if color is None:
            a(f"\t\t(stroke (width {w}) (type solid))")
        else:
            r, g, b, alpha = color
            a(
                f"\t\t(stroke (width {w}) (type solid) "
                f"(color {r} {g} {b} {alpha}))"
            )
        a("\t\t(fill none)")
        a(f'\t\t(layer "{layer}")')
        a(f'\t\t(uuid "{uid()}")')
        a("\t)")

    # Cluster outline colors (RGBA 0–255): TOP cyan / BOTTOM orange — easy to tell faces apart
    CLUSTER_COLOR_TOP = (0, 200, 255, 255)      # Eco1.User — mặt trên
    CLUSTER_COLOR_BOT = (255, 140, 0, 255)       # Eco2.User — mặt dưới
    cluster_boxes: list[tuple] = []  # (face, label, x0, y0, x1, y1) for E11.9

    def cluster_outline(label: str, x0: float, y0: float, x1: float, y1: float, face="F", pad=1.5):
        """Labeled AABB around a same-function module cluster (Eco1 front / Eco2 back)."""
        if x0 > x1:
            x0, x1 = x1, x0
        if y0 > y1:
            y0, y1 = y1, y0
        x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
        layer = "Eco1.User" if face == "F" else "Eco2.User"
        color = CLUSTER_COLOR_TOP if face == "F" else CLUSTER_COLOR_BOT
        gr_box(x0, y0, x1, y1, layer, w=0.35, color=color)
        lx = x0 + 1.2
        ly = y0 + 2.4
        size = max(SILK_TEXT_MIN_MM, 1.0)
        mirror = " " if face == "B" else ""
        # KiCad 10 PCB: font has no (color …) — only size/thickness/bold/italic
        a(f'\t(gr_text "{label}"')
        a(f"\t\t(at {lx} {ly} 0)")
        a(f'\t\t(layer "{layer}")')
        a(
            f"\t\t(effects (font (size {size} {size}) "
            f"(thickness {max(0.15, size * 0.15)})){mirror})"
        )
        a(f'\t\t(uuid "{uid()}")')
        a("\t)")
        # Record for same-face non-overlap check (E11.9)
        cluster_boxes.append((face, label, x0, y0, x1, y1))

    def fp_silk_rect(x0, y0, x1, y1, layer="F.SilkS", w=0.12):
        """Rectangular body outline on silk for discrete passives."""
        a("\t\t(fp_rect")
        a(f"\t\t\t(start {x0} {y0})")
        a(f"\t\t\t(end {x1} {y1})")
        a(f"\t\t\t(stroke (width {w}) (type solid))")
        a("\t\t\t(fill none)")
        a(f'\t\t\t(layer "{layer}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")

    def fp_silk_text(txt: str, lx: float, ly: float, ang: float = 0, size: float = 0.7):
        """Local-coord silk label — rotates with the footprint (anti-misplug)."""
        size = max(0.6, size)
        a(f'\t\t(fp_text user "{txt}"')
        a(f"\t\t\t(at {lx} {ly} {ang})")
        a('\t\t\t(layer "F.SilkS")')
        a(
            f"\t\t\t(effects (font (size {size} {size}) "
            f"(thickness {max(0.1, size * 0.15)})))"
        )
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")

    def fp_pin1_notch(body_w: float, pin1_y: float, depth: float = 1.1):
        """DIP pin-1 silk notch (arc on pin-1 end) — follows footprint rot."""
        a("\t\t(fp_arc")
        a(f"\t\t\t(start {-body_w / 2} {pin1_y})")
        a(f"\t\t\t(mid 0 {pin1_y - depth})")
        a(f"\t\t\t(end {body_w / 2} {pin1_y})")
        a('\t\t\t(stroke (width 0.12) (type solid))')
        a('\t\t\t(layer "F.SilkS")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")

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
    # Via size is set for the cheapest, highest-yield JLCPCB run rather than for
    # density: 0.3 mm hole / 0.6 mm pad is their *minimum* for a 2-layer board,
    # and sitting on a minimum leaves no margin for drill wander. 0.4 mm is a
    # standard drill and 0.8 mm keeps a 0.2 mm annular ring all round, both well
    # inside the free tier. The board has room to spare, so there is nothing to
    # gain from the smaller hole.
    a("\t\t(via_dia 0.8)")
    a("\t\t(via_drill 0.4)")
    a("\t)")
    # Two things matter here. Net names on the board are bare (write_pcb
    # strips the leading slash), so the old "/MotA1" spellings matched
    # nothing and the four NEMA17 phase nets fell back to Default 0.25 mm
    # -- 0.88 A on 1 oz copper for a winding the TMC2209 drives at ~1 A.
    # And 1.00 mm = 2.39 A (IPC-2221, 1 oz, 10 C rise) for the +12V trunk,
    # which carries the NEMA17 (~1 A), 3x 28BYJ-48 (~0.22 A), the pump and
    # the 5 V buck: about 2.2 A peak, more than 0.70 mm (1.85 A) covers.
    a('\t(net_class "Power" "12V/5V/GND/motor"')
    a("\t\t(clearance 0.25)")
    a("\t\t(trace_width 1.00)")
    a("\t\t(via_dia 1.1)")
    a("\t\t(via_drill 0.6)")
    a('\t\t(add_net "+12V")')
    a('\t\t(add_net "+12V_RAW")')
    a('\t\t(add_net "+12V_SNS")')
    a('\t\t(add_net "+5V")')
    a('\t\t(add_net "GND")')
    a('\t\t(add_net "+3V3")')
    a('\t\t(add_net "MotA2")')
    a('\t\t(add_net "MotA1")')
    a('\t\t(add_net "MotB1")')
    a('\t\t(add_net "MotB2")')
    for _bn in (
        "BYJ1_A", "BYJ1_B", "BYJ1_C", "BYJ1_D",
        "BYJ2_A", "BYJ2_B", "BYJ2_C", "BYJ2_D",
        "BYJ3_A", "BYJ3_B", "BYJ3_C", "BYJ3_D",
    ):
        a(f'\t\t(add_net "{_bn}")')
    a("\t)")

    ox, oy = 35.0, 30.0
    bw, bh = BOARD_W, BOARD_H
    extra_w = BOARD_W_EXTRA

    def sx(local_x: float) -> float:
        """Shift placements on the right half when board width grows."""
        return local_x + extra_w if local_x >= 125.0 else local_x
    # Band TOP: between HMI headers (~oy+10…33) and Mot/LIM row (oy+42).
    # Keep max lane ≤ oy+40 so F.H clears Mot pads (center 72, edge ~71.15).
    Y_CH0 = oy + 34.0
    Y_CH_PITCH = 0.45  # i=0..13 → 34.0…39.85

    def y_channel(i: int) -> float:
        return Y_CH0 + i * Y_CH_PITCH

    # Band MID: below Mot/LIM pins (~oy+42…45), above DRV H channels (~oy+58).
    Y_MID0 = oy + 48.0
    Y_MID_PITCH = 0.7

    def y_mid_ch(i: int) -> float:
        return Y_MID0 + i * Y_MID_PITCH
    a("\t(gr_rect")
    a(f"\t\t(start {ox} {oy})")
    a(f"\t\t(end {ox + bw} {oy + bh})")
    a("\t\t(stroke (width 0.1) (type default))")
    a("\t\t(fill none)")
    a('\t\t(layer "Edge.Cuts")')
    a(f'\t\t(uuid "{uid()}")')
    a("\t)")

    # --- 4× M3 mounting holes (corners) — screw to enclosure wall ---
    mount_xy = [
        (ox + MOUNT_INSET, oy + MOUNT_INSET, "H1"),
        (ox + bw - MOUNT_INSET, oy + MOUNT_INSET, "H2"),
        (ox + MOUNT_INSET, oy + bh - MOUNT_INSET, "H3"),
        (ox + bw - MOUNT_INSET, oy + bh - MOUNT_INSET, "H4"),
    ]
    for hx, hy, href in mount_xy:
        a('\t(footprint "ESP32_Carrier:MountingHole_M3"')
        a('\t\t(layer "F.Cu")')
        a(f'\t\t(uuid "{uid()}")')
        a(f"\t\t(at {hx} {hy})")
        a(f'\t\t(property "Reference" "{href}"')
        a("\t\t\t(at 0 0 0)")
        a('\t\t\t(layer "F.SilkS")')
        a('\t\t\t(hide yes)')
        a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.1)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a('\t\t(property "Value" "M3"')
        a("\t\t\t(at 0 0 0)")
        a('\t\t\t(layer "F.Fab")')
        a('\t\t\t(hide yes)')
        a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.1)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        # board_only: a mounting hole has no schematic symbol, so without this
        # schematic parity reports each one as an extra footprint.
        a("\t\t(attr through_hole board_only exclude_from_pos_files exclude_from_bom)")
        a('\t\t(fp_circle')
        a("\t\t\t(center 0 0)")
        a(f"\t\t\t(end {MOUNT_PAD / 2} 0)")
        a("\t\t\t(stroke (width 0.12) (type solid))")
        a("\t\t\t(fill none)")
        a('\t\t\t(layer "F.SilkS")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a('\t\t(fp_circle')
        a("\t\t\t(center 0 0)")
        a(f"\t\t\t(end {MOUNT_PAD / 2 + 0.25} 0)")
        a("\t\t\t(stroke (width 0.05) (type solid))")
        a("\t\t\t(fill none)")
        a('\t\t\t(layer "F.CrtYd")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a('\t\t(pad "" np_thru_hole circle')
        a("\t\t\t(at 0 0)")
        a(f"\t\t\t(size {MOUNT_DRILL} {MOUNT_DRILL})")
        a(f"\t\t\t(drill {MOUNT_DRILL})")
        a('\t\t\t(layers "F&B.Cu" "*.Mask")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a("\t)")
    gr_text("M3x4 corner mount", ox + bw / 2 - 12, oy + 2.2, "Cmts.User", 0.8)
    gr_text("All parts TOP (F.Cu); B.Cu = routing only. Eco1 cluster = cyan", ox + 8, oy + 2.2, "Cmts.User", 0.7)

    rot = PART_ROT  # default; see ROT_TMC / ROT_ENC / ROT_DIP / ROT_BYJ
    tmc_rot = ROT_TMC
    enc_rot = ROT_ENC
    dip_rot = ROT_DIP
    byj_rot = ROT_BYJ

    # --- Placement: force-directed + SA floorplan (placement_floorplan.py) ---
    # Traditional: spring-electrical layout, anneal for COM/quadrant balance,
    # then even pack within POWER / AXIS / HMI / OPTO / SHIFT.
    ix0, iy0 = ox + MODULE_EDGE_CLEAR, oy + MODULE_EDGE_CLEAR
    ix1, iy1 = ox + bw - MODULE_EDGE_CLEAR, oy + bh - MODULE_EDGE_CLEAR
    _u1_lx0, _u1_ly0 = -1.8, -8.0
    _u1_lx1, _u1_ly1 = ROW_SPACING + 1.8, y_last + 3.0
    FP = balanced_placement(
        ox, oy, bw, bh,
        edge_clear=MODULE_EDGE_CLEAR,
        cluster_gap=MODULE_CLUSTER_GAP + 1.5,  # margin vs actual Eco inflation
        mcu_clear=MODULE_MCU_CLEAR,
        seed=42,
    )
    print(f"Floorplan cost={FP['cost']:.0f}")
    mcu_wx0, mcu_wy0 = FP["mcu_wx0"], FP["mcu_wy0"]
    fx = mcu_wx0 - _u1_lx0
    fy = mcu_wy0 - _u1_ly0
    mcu_wx1 = mcu_wx0 + (_u1_lx1 - _u1_lx0)
    mcu_wy1 = mcu_wy0 + (_u1_ly1 - _u1_ly0)
    jx, jy = FP["jx"], FP["jy"]
    f1x, f1y = FP["f1x"], FP["f1y"]
    d1x, d1y = FP["d1x"], FP["d1y"]
    mx, my = FP["mx"], FP["my"]
    tx, ty = FP["tx"], FP["ty"]
    j3x, j3y = FP["j3x"], FP["j3y"]
    j18x, j18y = FP["j18x"], FP["j18y"]
    j15x, j15y = FP["j15x"], FP["j15y"]
    j16x, j16y = FP["j16x"], FP["j16y"]
    j14x, j14y = FP["j14x"], FP["j14y"]
    opto_origin = FP["opto_origin"]

    # Skip old J1 placement header — continue with J1 at jx,jy below
    # (coordinates already set; original jx,jy assignment removed from following block)

    # J1 screw terminal — pad axis || nearest Edge (left = vertical → rot 90°).
    # Footprint pads on local X; @90° pads along world Y; wire-entry silk faces west.
    j1_rot = 90
    # --- J1 ---
    # PLACEHOLDER_J1_START
    a('\t(footprint "ESP32_Carrier:TerminalBlock_2P_5.0mm"')
    a('\t\t(layer "F.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {jx} {jy} {j1_rot})")
    a('\t\t(property "Reference" "J1"')
    a(f"			(at -6.8 0 {j1_rot})")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "Screw_12V_IN"')
    a(f"			(at 6.8 0 {j1_rot})")
    a('\t\t\t(layer "F.Fab")')
    a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")
    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
        a("\t\t(fp_rect")
        a("			(start -5.1 -4)")
        a("			(end 5.1 4)")
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
    # f1x,f1y set in placement map
    a('\t(footprint "ESP32_Carrier:Fuse_PTC_Radial_5.1mm"')
    a('\t\t(layer "F.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {f1x} {f1y} {rot})")
    a('\t\t(property "Reference" "F1"')
    a(f"\t\t\t(at 0 -5.2 {rot})")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.9 0.9) (thickness 0.12)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "PTC_3A_30V"')
    a(f"\t\t\t(at 0 5.2 {rot})")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.1)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")
    fp_silk_rect(-4.2, -4.2, 4.2, 4.2, "F.SilkS")
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
    # d1 at placement map
    a('\t(footprint "ESP32_Carrier:Diode_TVS_DO41"')
    a('\t\t(layer "F.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {d1x} {d1y} {rot})")
    a('\t\t(property "Reference" "D1"')
    a(f"\t\t\t(at 0 -3.2 {rot})")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.9 0.9) (thickness 0.12)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "P6KE15A"')
    a(f"\t\t\t(at 0 3.2 {rot})")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.1)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")
    fp_silk_rect(-3.2, -1.5, 3.2, 1.5, "F.SilkS")
    # cathode band mark + K label (pad2 / +X) — follows PART_ROT
    a("\t\t(fp_line")
    a("\t\t\t(start 2.2 -1.2)")
    a("\t\t\t(end 2.2 1.2)")
    a('\t\t\t(stroke (width 0.12) (type solid))')
    a('\t\t\t(layer "F.SilkS")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    fp_silk_text("K", 3.75, -2.2, rot, 0.7)
    fp_silk_text("A", -3.75, -2.2, rot, 0.7)
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
    gr_text("F1 PTC + D1 TVS", ox + 20, oy + 73.5, "F.SilkS", 0.7)

    # --- U2 MP1584EN BOTTOM ---
    # --- U2 MP1584EN BOTTOM (logic +5V) — mx,my from placement map ---
    a('\t(footprint "ESP32_Carrier:MP1584_5V3A"')
    a('\t\t(layer "F.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {mx} {my} {rot})")
    a('\t\t(property "Reference" "U2"')
    # Inside the body: below it, U2's designator landed on U4's silk outline.
    a(f'\t\t\t(at 0 {-MINI560_H / 2 + 3.0} {rot})')
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "MP1584_5V3A"')
    a(f'\t\t\t(at 0 {MINI560_H / 2 + 1.8} {rot})')
    a('\t\t\t(layer "F.Fab")')
    a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")
    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
        a("\t\t(fp_rect")
        a(f"\t\t\t(start {-MINI560_W / 2} {-MINI560_H / 2})")
        a(f"\t\t\t(end {MINI560_W / 2} {MINI560_H / 2})")
        a(f"\t\t\t(stroke (width {w}) (type solid))")
        a("\t\t\t(fill none)")
        a(f'\t\t\t(layer "{layer}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
    for num, name, x, y, net_i, net_n in [
        ("1", "VIN+", -MP1584_PAD_X, MP1584_PAD_Y_LO, 1, "+12V"),
        ("1", "VIN+", -MP1584_PAD_X, MP1584_PAD_Y_HI, 1, "+12V"),
        ("2", "VIN-", -MP1584_PAD_X, -MP1584_PAD_Y_LO, 2, "GND"),
        ("2", "VIN-", -MP1584_PAD_X, -MP1584_PAD_Y_HI, 2, "GND"),
        ("3", "VOUT-", MP1584_PAD_X, -MP1584_PAD_Y_LO, 2, "GND"),
        ("3", "VOUT-", MP1584_PAD_X, -MP1584_PAD_Y_HI, 2, "GND"),
        ("4", "VOUT+", MP1584_PAD_X, MP1584_PAD_Y_LO, 3, "+5V"),
        ("4", "VOUT+", MP1584_PAD_X, MP1584_PAD_Y_HI, 3, "+5V"),
    ]:
        shape = "rect" if num == "1" and y > 0 else "circle"
        a(f'\t\t(pad "{num}" thru_hole {shape}')
        a(f"\t\t\t(at {x} {y})")
        a("\t\t\t(size 2.0 2.0)")
        a("\t\t\t(drill 1.0)")
        a('\t\t\t(layers "*.Cu" "*.Mask")')
        a(f'\t\t\t(net {net_i} "{net_n}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
    a("\t)")

    # --- U3 TMC2209 (tx,ty; ROT_TMC uncrosses STEP/DIR/EN) ---
    t_hx = TMC_ROW / 2
    t_y0 = -3.5 * PITCH
    a('\t(footprint "ESP32_Carrier:TMC2209_StepStick"')
    a('\t\t(layer "F.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {tx} {ty} {tmc_rot})")
    a('\t\t(property "Reference" "U3"')
    a(f'\t\t\t(at 0 {-TMC_H / 2 - 1.8} {tmc_rot})')
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "TMC2209"')
    a(f'\t\t\t(at 0 {TMC_H / 2 + 1.8} {tmc_rot})')
    a('\t\t\t(layer "F.Fab")')
    a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")
    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
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

    # --- U1 ESP32 BOTTOM (fx,fy from placement map) ---

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
            "IO9": (54, "/BUZZER"),
            "IO10": (34, "SER"),
            "IO11": (35, "SRCLK"),
            "IO12": (36, "RCLK"),
            "IO13": (37, "OE_595"),
            "IO38": (62, "/ENC_A"),
            "IO41": (60, "/ENC_B"),
            "IO39": (47, "/TFT_SCK"),
            "IO40": (48, "/TFT_MOSI"),
            "IO47": (52, "/TFT_MISO"),
            "IO42": (50, "/TFT_CS"),
            "IO21": (51, "/TFT_DC"),
            "IO3": (55, "/BLOWER"),
            "IO46": (58, "/TFT_RST"),
            "IO45": (59, "/TFT_BL"),
            "IO48": (53, "/T_CS"),
            "IO6": (20, "/T_IRQ"),
            # IO7/8/14/15 spare
        }
        return m.get(name)

    a('\t(footprint "ESP32_Carrier:ESP32_S3_DevKitC_44Pin_Socket"')
    a('\t\t(layer "F.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {fx} {fy} {rot})")
    a('\t\t(property "Reference" "U1"')
    a(f"\t\t\t(at 12.7 -10.5 {rot})")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "ESP32_S3_DevKitC_1"')
    a(f"\t\t\t(at 12.7 {y_last + 5.0} {rot})")
    a('\t\t\t(layer "F.Fab")')
    a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")
    x0, x1 = -1.8, ROW_SPACING + 1.8
    y0e, y1e = -8.0, y_last + 3.0
    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
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

    # J2 removed: NEMA17 wires to U3 Mot pins (A2/A1/B1/B2) on TMC2209 stepstick.

    # --- J17 TFT LCD 1×9 + J23 touch 1×5 (same column, MSP3520 order) ---
    j23x, j23y = j3x, j3y + TFT_LCD_PINS * PITCH
    j17_nets = [
        (4, "+3V3"),
        (2, "GND"),
        (50, "/TFT_CS"),
        (58, "/TFT_RST"),
        (51, "/TFT_DC"),
        (48, "/TFT_MOSI"),
        (47, "/TFT_SCK"),
        (59, "/TFT_BL"),
        None,  # LCD SDO NC
    ]
    j23_nets = [
        (47, "/TFT_SCK"),   # T_CLK
        (53, "/T_CS"),
        (48, "/TFT_MOSI"),  # T_DIN
        (52, "/TFT_MISO"),  # T_DO
        (20, "/T_IRQ"),
    ]

    def _emit_tft_header(ref: str, fp: str, value: str, ox: float, oy: float,
                         header: list, nets: list, silk_tag: str,
                         cy_top: float = 1.8, cy_bot: float = 1.8):
        n = len(header)
        a(f'\t(footprint "ESP32_Carrier:{fp}"')
        a('\t\t(layer "F.Cu")')
        a(f'\t\t(uuid "{uid()}")')
        a(f"\t\t(at {ox} {oy})")
        a(f'\t\t(property "Reference" "{ref}"')
        a("\t\t\t(at 0 -3.8 0)")
        a('\t\t\t(layer "F.SilkS")')
        a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a(f'\t\t(property "Value" "{value}"')
        a(f"\t\t\t(at 0 {(n - 1) * PITCH + 3.8} 0)")
        a('\t\t\t(layer "F.Fab")')
        a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.1)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a("\t\t(attr through_hole)")
        span = (n - 1) * PITCH
        # Tight abutting courtyards so J17+J23 form one contiguous column
        for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
            a("\t\t(fp_rect")
            a(f"\t\t\t(start -1.8 {-cy_top})")
            a(f"\t\t\t(end 1.8 {span + cy_bot})")
            a(f"\t\t\t(stroke (width {w}) (type solid))")
            a("\t\t\t(fill none)")
            a(f'\t\t\t(layer "{layer}")')
            a(f'\t\t\t(uuid "{uid()}")')
            a("\t\t)")
        for i, label in enumerate([p[1] for p in header]):
            y = i * PITCH
            # Silk name = module pin name; local angle = PART_ROT (anti-misplug)
            a(f'\t\t(fp_text user "{label}"')
            a(f"\t\t\t(at 3.8 {y} {rot})")
            a('\t\t\t(layer "F.SilkS")')
            a("\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1)) (justify left))")
            a(f'\t\t\t(uuid "{uid()}")')
            a("\t\t)")
            if i == 0:
                a('\t\t(fp_text user "1"')
                a(f"\t\t\t(at -2.6 {y} {rot})")
                a('\t\t\t(layer "F.SilkS")')
                a("\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1)))")
                a(f'\t\t\t(uuid "{uid()}")')
                a("\t\t)")
            shape = "rect" if i == 0 else "circle"
            a(f'\t\t(pad "{i + 1}" thru_hole {shape}')
            a(f"\t\t\t(at 0 {y})")
            a("\t\t\t(size 1.7 1.7)")
            a("\t\t\t(drill 1.0)")
            a('\t\t\t(layers "*.Cu" "*.Mask")')
            if nets[i] is not None:
                ni, nn = nets[i]
                a(f'\t\t\t(net {ni} "{nn}")')
            a(f'\t\t\t(uuid "{uid()}")')
            a("\t\t)")
        a("\t)")
        gr_text(silk_tag, ox - 4.5, oy + (n - 1) * PITCH / 2, "F.SilkS", 0.55)

    # cy_bot/cy_top = 0.5 on abutting edge → 2.54−1.0 = 1.54 mm courtyard gap
    _emit_tft_header(
        "J17", TFT_LCD_FP, "TFT_LCD", j3x, j3y,
        TFT_LCD_HEADER, j17_nets, "LCD", cy_bot=0.5,
    )
    _emit_tft_header(
        "J23", TFT_TP_FP, "TFT_TP", j23x, j23y,
        TFT_TP_HEADER, j23_nets, "TP", cy_top=0.5,
    )

    # --- J18 EC11 encoder — ROT_ENC uncrosses ENC_A/B vs U1 ---
    a(f'\t(footprint "ESP32_Carrier:{ENC_FP}"')
    a('\t\t(layer "F.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {j18x} {j18y} {enc_rot})")
    a('\t\t(property "Reference" "J18"')
    a(f"\t\t\t(at 0 -2.4 {enc_rot})")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "EC11_ENC"')
    a(f"\t\t\t(at 0 {(ENC_PINS - 1) * PITCH + 3.8} {enc_rot})")
    a('\t\t\t(layer "F.Fab")')
    a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.1)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")
    span_e = (ENC_PINS - 1) * PITCH
    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
        a("\t\t(fp_rect")
        a("\t\t\t(start -1.8 -1.8)")
        a(f"\t\t\t(end 1.8 {span_e + 1.8})")
        a(f"\t\t\t(stroke (width {w}) (type solid))")
        a("\t\t\t(fill none)")
        a(f'\t\t\t(layer "{layer}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
    j18_nets = [
        (2, "GND", "GND"),
        (4, "+3V3", "3V3"),
        (62, "/ENC_A", "ENC_A"),
        (60, "/ENC_B", "ENC_B"),
    ]
    for i, (ni, nn, lab) in enumerate(j18_nets):
        y = i * PITCH
        a(f'\t\t(fp_text user "{lab}"')
        a(f"\t\t\t(at 3.8 {y} {enc_rot})")
        a('\t\t\t(layer "F.SilkS")')
        a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.1)) (justify left))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        if i == 0:
            a('\t\t(fp_text user "1"')
            a(f"\t\t\t(at -2.6 {y} {enc_rot})")
            a('\t\t\t(layer "F.SilkS")')
            a("\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1)))")
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
    gr_text("J18 ENC wall-mount EC11", j18x - 8, j18y - 5.5, "F.SilkS", 0.7)
    gr_text("GND 3V3 A=IO38 B=IO41", j18x - 6, j18y - 3.8, "F.SilkS", 0.55)

    # --- J15 Buzzer TOP ---
    # --- J15 Buzzer TOP — j15 from placement map ---
    a('\t(footprint "ESP32_Carrier:PinHeader_1x03_Buzzer"')
    a('\t\t(layer "F.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {j15x} {j15y})")
    a('\t\t(property "Reference" "J15"')
    a("\t\t\t(at 0 -2.4 0)")
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
        a('\t\t\t(layer "Cmts.User")')
        a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.1)) (justify left))")
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
    # --- J16 MOSFET / blower TOP — j16 from placement map ---
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
            (1, "+12V", "+12V"),
            (61, "/BLW_RET", "FAN-"),
        ]
    ):
        y = i * PITCH
        a(f'\t\t(fp_text user "{lab}"')
        a(f"\t\t\t(at 3.8 {y} 0)")
        a('\t\t\t(layer "Cmts.User")')
        a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.1)) (justify left))")
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
    gr_text("J16 AOD4184 +12V pump", j16x - 8, j16y - 5.5, "F.SilkS", 0.7)

    # Pad world coords (ESP32-S3 DevKitC)
    j1_raw = pad_world(jx, jy, j1_rot, -TB_PITCH / 2, 0)
    j1_12 = pad_world(f1x, f1y, rot, 2.55, 0)  # +12V after F1 PTC (alias for farm/star)
    j1_gnd = pad_world(jx, jy, j1_rot, TB_PITCH / 2, 0)
    f1_in = pad_world(f1x, f1y, rot, -2.55, 0)
    d1_gnd = pad_world(d1x, d1y, rot, -3.75, 0)
    d1_12v = pad_world(d1x, d1y, rot, 3.75, 0)
    u2_vinp = pad_world(mx, my, rot, -MP1584_PAD_X, MP1584_PAD_Y_MID)
    u2_ving = pad_world(mx, my, rot, -MP1584_PAD_X, -MP1584_PAD_Y_MID)
    u2_voutp = pad_world(mx, my, rot, MP1584_PAD_X, MP1584_PAD_Y_MID)
    u2_voutg = pad_world(mx, my, rot, MP1584_PAD_X, -MP1584_PAD_Y_MID)
    j16_pwm = (j16x, j16y)
    j16_gnd = (j16x, j16y + PITCH)
    j16_12v = (j16x, j16y + 2 * PITCH)

    # 5V = pad 21 left, GND = pad 22 left, 3V3 = pad 1 left
    u1_vin = pad_world(fx, fy, rot, *pad_local(21))
    u1_gnd_r = pad_world(fx, fy, rot, *pad_local(22))
    u1_gnd_l = pad_world(fx, fy, rot, *pad_local(23))
    u1_3v3 = pad_world(fx, fy, rot, *pad_local(1))
    u1_io25 = pad_world(fx, fy, rot, *pad_local(PIN_BY_NAME["IO16"]))
    u1_io26 = pad_world(fx, fy, rot, *pad_local(PIN_BY_NAME["IO17"]))
    u1_io27 = pad_world(fx, fy, rot, *pad_local(PIN_BY_NAME["IO18"]))

    # TMC pads world (ROT_TMC)
    t_en = pad_world(tx, ty, tmc_rot, -t_hx, t_y0 + 0 * PITCH)
    t_step = pad_world(tx, ty, tmc_rot, -t_hx, t_y0 + 6 * PITCH)
    t_dir = pad_world(tx, ty, tmc_rot, -t_hx, t_y0 + 7 * PITCH)
    t_vm = pad_world(tx, ty, tmc_rot, t_hx, t_y0 + 0 * PITCH)
    t_gnd = pad_world(tx, ty, tmc_rot, t_hx, t_y0 + 1 * PITCH)
    t_a2 = pad_world(tx, ty, tmc_rot, t_hx, t_y0 + 2 * PITCH)
    t_a1 = pad_world(tx, ty, tmc_rot, t_hx, t_y0 + 3 * PITCH)
    t_b1 = pad_world(tx, ty, tmc_rot, t_hx, t_y0 + 4 * PITCH)
    t_b2 = pad_world(tx, ty, tmc_rot, t_hx, t_y0 + 5 * PITCH)
    t_vio = pad_world(tx, ty, tmc_rot, t_hx, t_y0 + 6 * PITCH)
    t_gnd2 = pad_world(tx, ty, tmc_rot, t_hx, t_y0 + 7 * PITCH)

    # MotA/B stay on U3 only — NEMA17 plugs / solders to TMC Mot pins (no J2).
    j3_3v3 = (j3x, j3y)           # pin 1 VCC
    j3_gnd = (j3x, j3y + PITCH)   # pin 2 GND

    # === +12V 3A via farm: AFTER F1 PTC (not raw J1) ===
    # J1 RAW -> F1 -> +12V farm; D1 TVS on +12V
    # Keep RAW/12V/GND local around J1 — no long diagonals.
    # J1 RAW -> F1 on Y offset from +12V farm row (same nets, path only)
    y_raw = j1_raw[1] - 3.0
    track_h(j1_raw[0], f1_in[0], y_raw, 57, 1.5)
    via(f1_in[0], y_raw, 57, 0.45, 0.9)
    track_v(f1_in[0], y_raw, f1_in[1], 57, 1.5)
    track_v(j1_12[0], j1_12[1], d1_12v[1], 1, 1.0)
    via(j1_12[0], d1_12v[1], 1, 0.4, 0.8)
    track_h(j1_12[0], d1_12v[0], d1_12v[1], 1, 0.8)
    # GND to TVS on offset Y — same pad-row Y would short across +12V stub
    y_d1g = d1_gnd[1] + 2.0
    track_v(j1_gnd[0], j1_gnd[1], y_d1g, 2, 0.8)
    via(j1_gnd[0], y_d1g, 2, 0.4, 0.8)
    track_h(j1_gnd[0], d1_gnd[0], y_d1g, 2, 0.8)
    via(d1_gnd[0], y_d1g, 2, 0.4, 0.8)
    track_v(d1_gnd[0], y_d1g, d1_gnd[1], 2, 0.8)

    # Via farm immediately WEST of F1 (short stub — do not span TFT corridor)
    farm_cx = j1_12[0] - 4.0
    farm_cy = j1_12[1]
    gr_text("+12V VIA 3A", farm_cx - 4, farm_cy - 5, "F.SilkS", 0.7)
    gr_text("+12V VIA 3A", farm_cx - 4, farm_cy - 5, "Cmts.User", 0.8)
    for ix in range(VIA12_COUNT_X):
        for iy in range(VIA12_COUNT_Y):
            vx = farm_cx + (ix - 1) * VIA12_PITCH
            vy = farm_cy + (iy - 0.5) * VIA12_PITCH
            via(vx, vy, 1)
    pw = 1.5
    # +12V: V on B to y12, H on F along spine, V on B to loads (Manhattan)
    track_h(j1_12[0], farm_cx, j1_12[1], 1, pw)
    via(farm_cx, j1_12[1], 1)
    track_h(farm_cx - VIA12_PITCH, farm_cx + VIA12_PITCH, farm_cy, 1, pw)

    y12 = oy + 56.0
    x12_east_power = ox + 48.0
    track_v(farm_cx, farm_cy, y12, 1, pw)
    via(farm_cx, y12, 1)
    track_h(farm_cx, x12_east_power, y12, 1, pw)
    track_h(x12_east_power, u2_vinp[0], y12, 1, pw)
    via(u2_vinp[0], y12, 1)
    track_v(u2_vinp[0], y12, u2_vinp[1], 1, pw)
    track_h(x12_east_power, t_vm[0], y12, 1, pw)
    via(t_vm[0], y12, 1)
    track_v(t_vm[0], y12, t_vm[1], 1, pw)
    x12_drv = ox + bw - 5.0
    track_h(t_vm[0], x12_drv, y12, 1, pw)
    via(x12_drv, y12, 1)
    track_v(x12_drv, y12, oy + 110.0 - 8.0, 1, 2.0)

    y_sig_via = max(y12, farm_cy) + 3.0

    # GND: modules drop on SHORT local H then V — never long H at pad Y (collides signals)
    yg = oy + bh - 5.0
    xg_drv = ox + bw - 11.0
    xg_west = ox + 5.0
    track_v(j1_gnd[0], j1_gnd[1], yg, 2, pw)
    via(j1_gnd[0], yg, 2)
    track_h(j1_gnd[0], xg_drv, yg, 2, pw)
    via(xg_drv, yg, 2)
    track_v(xg_drv, yg, oy + 62.0, 2, 2.0)
    track_h(j1_gnd[0], xg_west, yg, 2, pw)
    via(xg_west, yg, 2)
    track_v(xg_west, yg, oy + 70.0, 2, 1.2)
    for i, (px, py) in enumerate((
        (u2_ving[0], u2_ving[1]),
        (u2_voutg[0], u2_voutg[1]),
        (t_gnd[0], t_gnd[1]),
        (t_gnd2[0], t_gnd2[1]),
        (u1_gnd_l[0], u1_gnd_l[1]),
        (u1_gnd_r[0], u1_gnd_r[1]),
    )):
        # Short jog off pad X, then V to spine (same net; unique X avoids foreign nets)
        xg = px - 4.0 if px > ox + 20 else px + 4.0
        track_h(px, xg, py, 2, 1.0)
        via(xg, py, 2)
        track_v(xg, py, yg, 2, 1.0)
        via(xg, yg, 2)
        track_h(xg, j1_gnd[0], yg, 2, 1.0)
    for i in range(4):
        vx = j1_gnd[0] - 5.0 - i * 1.8
        via(vx, j1_gnd[1], 2)
        track_h(j1_gnd[0], vx, j1_gnd[1], 2, 1.0)
        via(vx, j1_gnd[1], 2)
        track_v(vx, j1_gnd[1], yg, 2, 1.0)
        via(vx, yg, 2)
        track_h(vx, j1_gnd[0], yg, 2, 1.0)

    # +5V: west of opto trunks (ox+72..) and MCU
    y5 = y12 + 4.0
    x5 = ox + 58.0
    track_v(u2_voutp[0], u2_voutp[1], y5, 3, 1.0)
    via(u2_voutp[0], y5, 3)
    track_h(u2_voutp[0], x5, y5, 3, 1.0)
    via(x5, y5, 3)
    track_v(x5, y5, u1_vin[1], 3, 1.0)
    via(x5, u1_vin[1], 3, 0.4, 0.8)
    track_h(x5, u1_vin[0], u1_vin[1], 3, 1.0)

    # J16 blower +12V from main spine (370 pump 12V — single U2 buck for logic only)
    y_blw_ch = y_mid_ch(0)
    x12_blw = j16_12v[0] - 5.0
    track_h(u2_vinp[0], x12_blw, y12, 1, 1.0)
    via(x12_blw, y12, 1)
    track_v(x12_blw, y12, y_blw_ch, 1, 0.8)
    via(x12_blw, y_blw_ch, 1, 0.4, 0.8)
    side_enter_pin(1, x12_blw, y_blw_ch, j16_12v, w=0.8, side=-3.0)
    # GND off J16: leave on EAST of column (+12V uses west x12_blw / side=-3)
    y16g = y_mid_ch(1)
    x16g = j16_gnd[0] + 3.5
    track_h(j16_gnd[0], x16g, j16_gnd[1], 2, 0.8)
    via(x16g, j16_gnd[1], 2)
    track_v(x16g, j16_gnd[1], y16g, 2, 0.8)
    via(x16g, y16g, 2)
    track_h(x16g, j1_gnd[0], y16g, 2, 0.8)
    via(j1_gnd[0], y16g, 2)
    track_v(j1_gnd[0], y16g, yg, 2, 0.8)

    # +3V3 ESP32 -> TMC VIO (offset Y from pad row; unique X)
    x3 = u1_3v3[0] + 5.0
    y3 = u1_3v3[1] - 2.5
    track_v(u1_3v3[0], u1_3v3[1], y3, 4, 0.5)
    via(u1_3v3[0], y3, 4, 0.4, 0.8)
    track_h(u1_3v3[0], x3, y3, 4, 0.5)
    via(x3, y3, 4, 0.4, 0.8)
    track_v(x3, y3, t_vio[1], 4, 0.5)
    via(x3, t_vio[1], 4, 0.4, 0.8)
    track_h(x3, t_vio[0], t_vio[1], 4, 0.5)
    y3v_bus = oy + 6.0
    ygnd_bus = oy + 7.5

    # Mot nets: single-pad on U3 (field wire to stepstick Mot) — no board tracks.

    # TMC control: leave MCU column with H first (left GPIOs share X)
    def route_sig(net_i, src, dst, xlane, y_lane):
        track_h(src[0], xlane, src[1], net_i, 0.35)
        via(xlane, src[1], net_i, 0.4, 0.8)
        track_v(xlane, src[1], y_lane, net_i, 0.35)
        via(xlane, y_lane, net_i, 0.4, 0.8)
        track_h(xlane, dst[0] - 3.0, y_lane, net_i, 0.35)
        via(dst[0] - 3.0, y_lane, net_i, 0.4, 0.8)
        track_v(dst[0] - 3.0, y_lane, dst[1], net_i, 0.35)
        via(dst[0] - 3.0, dst[1], net_i, 0.4, 0.8)
        track_h(dst[0] - 3.0, dst[0], dst[1], net_i, 0.35)

    # Keep west of +12V TMC VM column (~t_vm X)
    route_sig(5, u1_io25, t_step, ox + 100.0, oy + 52.0)
    route_sig(6, u1_io26, t_dir, ox + 102.0, oy + 53.5)
    route_sig(11, u1_io27, t_en, ox + 104.0, oy + 55.0)

    def route_mcu_to_top(net_i, src, dst, xlane, w=0.3, y_off=0.0, side=-3.0, esc_i=0):
        """Route to TOP header without crossing pin fields.
        Escape → exclusive channel Y → H to approach column beside dst → side-enter.
        xlane kept for API compat; approach is always beside the target pin.
        """
        y_h = src[1] + y_off
        y_ch = y_channel(esc_i)
        x_appr = dst[0] + side
        if src[0] < fx:
            x_esc = ox + 95.0 + esc_i * 1.15
        else:
            x_esc = ox + sx(143.0) + esc_i * 1.15
        if abs(y_off) > 0.05:
            track_v(src[0], src[1], y_h, net_i, w)
            via(src[0], y_h, net_i, 0.4, 0.8)
            track_h(src[0], x_esc, y_h, net_i, w)
            via(x_esc, y_h, net_i, 0.4, 0.8)
            track_v(x_esc, y_h, y_ch, net_i, w)
        else:
            track_h(src[0], x_esc, src[1], net_i, w)
            via(x_esc, src[1], net_i, 0.4, 0.8)
            track_v(x_esc, src[1], y_ch, net_i, w)
        via(x_esc, y_ch, net_i, 0.4, 0.8)
        track_h(x_esc, x_appr, y_ch, net_i, w)
        via(x_appr, y_ch, net_i, 0.4, 0.8)
        side_enter_pin(net_i, x_appr, y_ch, dst, w=w, side=side)

    # MSP3520: CS=2 RST=3 DC=4 MOSI=5 SCK=6 LED=7; touch CS=10 DO=12 IRQ=13
    tft_sigs = [
        (50, "IO42", 2),
        (58, "IO46", 3),
        (51, "IO21", 4),
        (48, "IO40", 5),
        (47, "IO39", 6),
        (59, "IO45", 7),
        (53, "IO48", 10),
        (52, "IO47", 12),
        (20, "IO6", 13),
    ]
    for i, (ni, gname, pin_i) in enumerate(tft_sigs):
        src = pad_world(fx, fy, rot, *pad_local(PIN_BY_NAME[gname]))
        dst = (j3x, j3y + pin_i * PITCH)
        route_mcu_to_top(ni, src, dst, ox + sx(178.0) + i * 1.2, side=-3.0, esc_i=i)
    def _tft_bridge(net_i: int, ya: float, yb: float):
        x_b = j3x - 2.2
        track_h(j3x, x_b, ya, net_i, 0.25)
        track_v(x_b, ya, yb, net_i, 0.25)
        track_h(x_b, j3x, yb, net_i, 0.25)

    _tft_bridge(47, j3y + 6 * PITCH, j3y + 9 * PITCH)
    _tft_bridge(48, j3y + 5 * PITCH, j3y + 11 * PITCH)
    bz = pad_world(fx, fy, rot, *pad_local(PIN_BY_NAME["IO9"]))
    route_mcu_to_top(54, bz, (j15x, j15y + 2 * PITCH), ox + sx(178.0) + 8 * 1.2, side=-3.0, esc_i=8)
    bl = pad_world(fx, fy, rot, *pad_local(PIN_BY_NAME["IO3"]))
    route_mcu_to_top(55, bl, (j16x, j16y), ox + sx(178.0) + 9 * 1.2, side=-3.0, esc_i=9)
    for i, (ni, gname, pin_i) in enumerate([(62, "IO38", 2), (60, "IO41", 3)]):
        src = pad_world(fx, fy, rot, *pad_local(PIN_BY_NAME[gname]))
        dst = pad_world(j18x, j18y, enc_rot, 0, pin_i * PITCH)
        route_mcu_to_top(ni, src, dst, ox + sx(178.0) + (10 + i) * 1.2, side=-3.0, esc_i=10 + i)
    route_mcu_to_top(4, u1_3v3, j3_3v3, ox + sx(192.0), y_off=-2.0, side=-3.0, esc_i=12)
    route_mcu_to_top(2, u1_gnd_l, j3_gnd, ox + sx(193.5), y_off=2.0, side=-3.0, esc_i=13)
    route_mcu_to_top(2, u1_gnd_l, pad_world(j18x, j18y, enc_rot, 0, 0), ox + sx(193.5), y_off=2.0, side=-3.0, esc_i=13)
    route_mcu_to_top(4, u1_3v3, pad_world(j18x, j18y, enc_rot, 0, PITCH), ox + sx(192.0), y_off=-2.0, side=-3.0, esc_i=12)

    # ===== Discrete PC817 ×4 + 2k2 LED + 10k pull-up (BOTTOM) =====
    rot4 = PART_ROT
    hx4 = DIP4_ROW / 2
    y_a = -0.5 * PITCH
    y_k = y_a + PITCH

    def _emit_pc817_dip4(ref: str, ux: float, uy: float, anode_net, out_net):
        """1=A(anode_net) 2=K(GND) 3=E(GND) 4=C(out_net). Silk pin1 + A/K/C/E."""
        a('\t(footprint "ESP32_Carrier:PC817_DIP4"')
        a('\t\t(layer "F.Cu")')
        a(f'\t\t(uuid "{uid()}")')
        a(f"\t\t(at {ux} {uy} {rot4})")
        a(f'\t\t(property "Reference" "{ref}"')
        a(f"\t\t\t(at 0 {-DIP4_BODY_L / 2 - 1.4} {rot4})")
        a('\t\t\t(layer "F.SilkS")')
        a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a('\t\t(property "Value" "PC817"')
        a(f"\t\t\t(at 0 {DIP4_BODY_L / 2 + 1.4} {rot4})")
        a('\t\t\t(layer "F.Fab")')
        a("\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a("\t\t(attr through_hole)")
        silk_hx = DIP4_ROW / 2 + DIP4_PAD / 2 + 0.3
        for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
            a("\t\t(fp_rect")
            hxr = silk_hx if layer.endswith("SilkS") else DIP4_BODY_W / 2 + 0.2
            a(f"\t\t\t(start {-hxr} {-DIP4_BODY_L / 2 - 0.2})")
            a(f"\t\t\t(end {hxr} {DIP4_BODY_L / 2 + 0.2})")
            a(f"\t\t\t(stroke (width {w}) (type solid))")
            a("\t\t\t(fill none)")
            a(f'\t\t\t(layer "{layer}")')
            a(f'\t\t\t(uuid "{uid()}")')
            a("\t\t)")
        fp_pin1_notch(DIP4_BODY_W, y_a, 1.0)
        # Pin labels in local frame — rotate with part (anti-misplug)
        fp_silk_text("A", -hx4 - 1.8, y_a, rot4, 0.65)
        fp_silk_text("K", -hx4 - 1.8, y_k, rot4, 0.65)
        fp_silk_text("E", hx4 + 1.8, y_k, rot4, 0.65)
        fp_silk_text("C", hx4 + 1.8, y_a, rot4, 0.65)
        pad_defs = [
            ("1", -hx4, y_a, "rect", anode_net),
            ("2", -hx4, y_k, "circle", (2, "GND")),
            ("3", hx4, y_k, "circle", (2, "GND")),
            ("4", hx4, y_a, "circle", out_net),
        ]
        for num, px, py, shape, net in pad_defs:
            a(f'\t\t(pad "{num}" thru_hole {shape}')
            a(f"\t\t\t(at {px} {py})")
            a(f"\t\t\t(size {DIP4_PAD} {DIP4_PAD})")
            a(f"\t\t\t(drill {DIP4_DRILL})")
            a('\t\t\t(layers "*.Cu" "*.Mask")')
            a(f'\t\t\t(net {net[0]} "{net[1]}")')
            a(f'\t\t\t(uuid "{uid()}")')
            a("\t\t)")
        a("\t)")

    def _emit_opto_axial(ref: str, val: str, ax: float, ay: float, na, nb, note=""):
        a('\t(footprint "ESP32_Carrier:R_Axial_4k7_BUP"')
        a('\t\t(layer "F.Cu")')
        a(f'\t\t(uuid "{uid()}")')
        a(f"\t\t(at {ax} {ay} {rot})")
        a(f'\t\t(property "Reference" "{ref}"')
        a(f"\t\t\t(at 0 -2.6 {rot})")
        a('\t\t\t(layer "F.SilkS")')
        a("\t\t\t(effects (font (size 0.75 0.75) (thickness 0.1)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a(f'\t\t(property "Value" "{val}"')
        a(f"\t\t\t(at 0 2.6 {rot})")
        a('\t\t\t(layer "F.SilkS")')
        a("\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a("\t\t(attr through_hole)")
        fp_silk_rect(-3.2, -1.5, 3.2, 1.5, "F.SilkS")
        fp_silk_text("1", -3.75, -2.0, rot, 0.55)
        for pnum, (ni, nn), px in ((1, na, -3.75), (2, nb, 3.75)):
            a(f'\t\t(pad "{pnum}" thru_hole {"rect" if pnum == 1 else "circle"}')
            a(f"\t\t\t(at {px} 0)")
            a("\t\t\t(size 1.6 1.6)")
            a("\t\t\t(drill 0.8)")
            a('\t\t\t(layers "*.Cu" "*.Mask")')
            a(f'\t\t\t(net {ni} "{nn}")')
            a(f'\t\t\t(uuid "{uid()}")')
            a("\t\t)")
        a("\t)")
        if note:
            gr_text(note, ax - 6, ay + 4.2, "Cmts.User", 0.55)

    ox_o, oy_o = opto_origin
    opto_row_pitch = 26.0  # RPU row0 vs RLED row1 silk rects need ≥6 mm center gap
    opto_col_pitch = 11.5
    gr_text("OPTO PC817x8 + 2k2/10k", ox_o - 8, oy_o - 14, "F.SilkS", 0.7)
    for i, (uref, rled, rpu, iid, inet, oid, onet, aid, anet, tag) in enumerate(OPTO_CH):
        col, row = i % 4, i // 4
        ux = ox_o + col * opto_col_pitch
        uy = oy_o + row * opto_row_pitch
        _emit_pc817_dip4(uref, ux, uy, (aid, anet), (oid, onet))
        _emit_opto_axial(
            rled, "2k2", ux - 3.5, uy - 8.5,
            (iid, inet), (aid, anet), f"{rled} LED {tag}",
        )
        _emit_opto_axial(
            rpu, "10k", ux + 3.5, uy + 8.5,
            (4, "+3V3"), (oid, onet), f"{rpu} PU {tag}",
        )

    def _opto_in_pad_ch(ch_i: int):
        """World coords of LED resistor pad1 (OPTO_INx) for channel index."""
        col, row = ch_i % 4, ch_i // 4
        ux = ox_o + col * opto_col_pitch
        uy = oy_o + row * opto_row_pitch
        return pad_world(ux - 3.5, uy - 8.5, 0, -3.75, 0)

    # --- DIP-16: U5-U7 ULN; BYJ J5-J7; HOME endstop J8/J10/J12 ---
    dip_y0 = -3.5 * PITCH
    dip_hx = DIP16_ROW / 2

    def _emit_dip16(fp, ref, val, ux, uy, pad_nets: dict, drot=None):
        """pad_nets: pin_number -> (net_id, net_name) or None for NC."""
        if drot is None:
            drot = dip_rot
        a(f'\t(footprint "ESP32_Carrier:{fp}"')
        a('\t\t(layer "F.Cu")')
        a(f'\t\t(uuid "{uid()}")')
        a(f"\t\t(at {ux} {uy} {drot})")
        a(f'\t\t(property "Reference" "{ref}"')
        a(f"\t\t\t(at 0 {-DIP16_BODY_L / 2 - 1.5} {drot})")
        a('\t\t\t(layer "F.SilkS")')
        a("\t\t\t(effects (font (size 0.9 0.9) (thickness 0.12)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a(f'\t\t(property "Value" "{val}"')
        a(f"\t\t\t(at 0 {DIP16_BODY_L / 2 + 1.5} {drot})")
        a('\t\t\t(layer "F.Fab")')
        a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.1)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a("\t\t(attr through_hole)")
        for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
            a("\t\t(fp_rect")
            hxr = DIP16_SILK_HX if layer.endswith("SilkS") else DIP16_BODY_W / 2 + 0.3
            a(f"			(start {-hxr} {-DIP16_BODY_L / 2 - 0.3})")
            a(f"			(end {hxr} {DIP16_BODY_L / 2 + 0.3})")
            a(f"\t\t\t(stroke (width {w}) (type solid))")
            a("\t\t\t(fill none)")
            a(f'\t\t\t(layer "{layer}")')
            a(f'\t\t\t(uuid "{uid()}")')
            a("\t\t)")
        fp_pin1_notch(DIP16_BODY_W, dip_y0, 1.2)
        fp_silk_text("1", -dip_hx - 2.2, dip_y0, drot, 0.7)
        fp_silk_text(val[:7], 0, 0, drot, 0.75)
        for i in range(8):
            num = i + 1
            y = dip_y0 + i * PITCH
            shape = "rect" if i == 0 else "oval"
            a(f'\t\t(pad "{num}" thru_hole {shape}')
            a(f"\t\t\t(at {-dip_hx} {y})")
            a(f"\t\t\t(size {DIP16_PAD_W} {DIP16_PAD_H})")
            a(f"\t\t\t(drill {DIP16_DRILL})")
            a('\t\t\t(layers "*.Cu" "*.Mask")')
            if num in pad_nets and pad_nets[num]:
                ni, nn = pad_nets[num]
                a(f'\t\t\t(net {ni} "{nn}")')
            a(f'\t\t\t(uuid "{uid()}")')
            a("\t\t)")
        for i in range(8):
            num = 16 - i
            y = dip_y0 + i * PITCH
            a(f'\t\t(pad "{num}" thru_hole oval')
            a(f"\t\t\t(at {dip_hx} {y})")
            a(f"\t\t\t(size {DIP16_PAD_W} {DIP16_PAD_H})")
            a(f"\t\t\t(drill {DIP16_DRILL})")
            a('\t\t\t(layers "*.Cu" "*.Mask")')
            if num in pad_nets and pad_nets[num]:
                ni, nn = pad_nets[num]
                a(f'\t\t\t(net {ni} "{nn}")')
            a(f'\t\t\t(uuid "{uid()}")')
            a("\t\t)")
        a("\t)")

    # South: AXIS1→3 (ULN). SHIFT module U10 from floorplan (east of ESP32).
    _dip_y = FP["_dip_y"]
    u5x, u5y = FP["u5x"], FP["u5y"]
    u6x, u6y = FP["u6x"], FP["u6y"]
    u7x, u7y = FP["u7x"], FP["u7y"]

    def uln_nets(in_ids, byj_ids):
        d = {
            1: in_ids[0], 2: in_ids[1], 3: in_ids[2], 4: in_ids[3],
            5: None, 6: None, 7: None,
            8: (2, "GND"), 9: (1, "+12V"),
            10: None, 11: None, 12: None,
            13: byj_ids[3], 14: byj_ids[2], 15: byj_ids[1], 16: byj_ids[0],
        }
        return d

    _emit_dip16(
        "ULN2003AN", "U5", "ULN2003AN", u5x, u5y,
        uln_nets(
            [(39, "SR_Q0"), (40, "SR_Q1"), (41, "SR_Q2"), (42, "SR_Q3")],
            [(68, "BYJ1_A"), (69, "BYJ1_B"), (70, "BYJ1_C"), (71, "BYJ1_D")],
        ),
    )
    _emit_dip16(
        "ULN2003AN", "U6", "ULN2003AN", u6x, u6y,
        uln_nets(
            [(43, "SR_Q4"), (44, "SR_Q5"), (45, "SR_Q6"), (63, "SR_Q7")],
            [(72, "BYJ2_A"), (73, "BYJ2_B"), (74, "BYJ2_C"), (75, "BYJ2_D")],
        ),
    )
    _emit_dip16(
        "ULN2003AN", "U7", "ULN2003AN", u7x, u7y,
        uln_nets(
            [(64, "SR_Q8"), (65, "SR_Q9"), (66, "SR_Q10"), (67, "SR_Q11")],
            [(76, "BYJ3_A"), (77, "BYJ3_B"), (78, "BYJ3_C"), (79, "BYJ3_D")],
        ),
    )

    def _hdr_1xn(fp, ref, val, atx, aty, pads, hrot=0):
        n = len(pads)
        a(f'\t(footprint "ESP32_Carrier:{fp}"')
        a('\t\t(layer "F.Cu")')
        a(f'\t\t(uuid "{uid()}")')
        a(f"\t\t(at {atx} {aty} {hrot})")
        a(f'\t\t(property "Reference" "{ref}"')
        a(f"\t\t\t(at 0 -3.8 {hrot})")
        a('\t\t\t(layer "F.SilkS")')
        a("\t\t\t(effects (font (size 0.9 0.9) (thickness 0.12)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a(f'\t\t(property "Value" "{val}"')
        a(f"\t\t\t(at 0 {(n - 1) * PITCH + 3.8} {hrot})")
        a('\t\t\t(layer "F.Fab")')
        a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.1)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a("\t\t(attr through_hole)")
        for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
            a("\t\t(fp_rect")
            a("\t\t\t(start -1.8 -1.8)")
            a(f"\t\t\t(end 1.8 {(n - 1) * PITCH + 1.8})")
            a(f"\t\t\t(stroke (width {w}) (type solid))")
            a("\t\t\t(fill none)")
            a(f'\t\t\t(layer "{layer}")')
            a(f'\t\t\t(uuid "{uid()}")')
            a("\t\t)")
        for pi, (neti, netn, lab) in enumerate(pads):
            y = pi * PITCH
            a(f'\t\t(fp_text user "{lab}"')
            a(f"\t\t\t(at 3.2 {y} {hrot})")
            a('\t\t\t(layer "F.SilkS")')
            a("\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1)) (justify left))")
            a(f'\t\t\t(uuid "{uid()}")')
            a("\t\t)")
            if pi == 0:
                a('\t\t(fp_text user "1"')
                a(f"\t\t\t(at -2.6 {y} {hrot})")
                a('\t\t\t(layer "F.SilkS")')
                a("\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1)))")
                a(f'\t\t\t(uuid "{uid()}")')
                a("\t\t)")
            shape = "rect" if pi == 0 else "circle"
            a(f'\t\t(pad "{pi + 1}" thru_hole {shape}')
            a(f"\t\t\t(at 0 {y})")
            a("\t\t\t(size 1.7 1.7)")
            a("\t\t\t(drill 1.0)")
            a('\t\t\t(layers "*.Cu" "*.Mask")')
            if neti:
                a(f'\t\t\t(net {neti} "{netn}")')
            a(f'\t\t\t(uuid "{uid()}")')
            a("\t\t)")
        a("\t)")

    # --- U10 74HC595-24IO module socket (Thế Giới Module / Shopee) EAST of ESP32 ---
    # Long axis vertical; CTRL 1×6 west (near MCU); Q 1×24 east. Pitch 2.54.
    # Verify hole span vs physical module before fab (typ. ~66×20 mm).
    MOD_CTRL_TO_Q = FP["MOD_CTRL_TO_Q"]
    u10_ctrl_x = max(FP["u10_ctrl_x"], mcu_wx1 + MODULE_MCU_CLEAR + 3.0)
    u10_q_x = u10_ctrl_x + MOD_CTRL_TO_Q
    u10_y0 = FP["u10_y0"]
    if u10_q_x + 10.0 > ix1:
        u10_q_x = ix1 - 10.0
        u10_ctrl_x = u10_q_x - MOD_CTRL_TO_Q
    r4x = min(ix1 - 4.0, max(FP["r4x"], u10_q_x + 6.0))
    r4y = FP["r4y"]
    _hdr_1xn(
        "PinHeader_1x06_595CTRL", "J24", "595_CTRL",
        u10_ctrl_x, u10_y0,
        [
            (37, "OE_595", "LDEN"),
            (2, "GND", "GND"),
            (4, "+3V3", "VCC"),
            (34, "SER", "LDSI"),
            (36, "RCLK", "LDSTR"),
            (35, "SRCLK", "LDSCK"),
        ],
    )
    q_pads = []
    q_nets = [
        (39, "SR_Q0"), (40, "SR_Q1"), (41, "SR_Q2"), (42, "SR_Q3"),
        (43, "SR_Q4"), (44, "SR_Q5"), (45, "SR_Q6"), (63, "SR_Q7"),
        (64, "SR_Q8"), (65, "SR_Q9"), (66, "SR_Q10"), (67, "SR_Q11"),
    ]
    for i in range(24):
        chip, bit = i // 8 + 1, i % 8
        lab = f"{chip}_Q{bit}"
        if i < 12:
            ni, nn = q_nets[i]
            q_pads.append((ni, nn, lab))
        else:
            q_pads.append((None, "", lab))
    _hdr_1xn(
        "PinHeader_1x24_595Q", "J25", "595_Q",
        u10_q_x, u10_y0, q_pads,
    )
    mod_x0, mod_y0 = u10_ctrl_x - 2.5, u10_y0 - 2.5
    mod_x1, mod_y1 = u10_q_x + 2.5, u10_y0 + 23 * PITCH + 2.5
    gr_box(mod_x0, mod_y0, mod_x1, mod_y1, "F.SilkS")
    gr_text("U10 74HC595-24IO module", mod_x0, mod_y0 - 2.2, "F.SilkS", 0.75)
    gr_text("Shopee thegioimodule 3x595", mod_x0, mod_y1 + 1.8, "Cmts.User", 0.55)
    u10x, u10y = (u10_ctrl_x + u10_q_x) / 2.0, u10_y0 + 11 * PITCH
    u11x, u11y = u10_q_x, u10_y0

    byj_jacks = [
        ("J5", u5x - 11.0, _dip_y + 4.0, 68, "BYJ1"),
        ("J6", u6x - 11.0, _dip_y + 4.0, 72, "BYJ2"),
        ("J7", u7x - 11.0, _dip_y + 4.0, 76, "BYJ3"),
    ]
    for jref, jx_b, jy_b, n0, tag in byj_jacks:
        gr_text(f"{jref} 28BYJ {tag}", jx_b - 10, jy_b - 4.5, "F.SilkS", 0.65)
        _hdr_1xn(
            BYJ_FP, jref, "28BYJ48", jx_b, jy_b,
            [
                (n0, f"{tag}_A", "A"),
                (n0 + 1, f"{tag}_B", "B"),
                (n0 + 2, f"{tag}_C", "C"),
                (n0 + 3, f"{tag}_D", "D"),
                (1, "+12V", "+12V"),
            ],
            hrot=byj_rot,
        )

    LIMIT_Y = iy0 + 4.0
    home_jacks = [
        ("J8", u5x + 11.0, _dip_y, 25, "/OPTO_IN1", "HOME1"),
        ("J10", u6x + 11.0, _dip_y, 26, "/OPTO_IN2", "HOME2"),
        ("J12", u7x + 11.0, _dip_y, 27, "/OPTO_IN3", "HOME3"),
    ]
    home_limit_pos = []
    for jref, lx, ly, ni, nn, tag in home_jacks:
        home_limit_pos.append((lx, ly))
        gr_text(f"{jref} {tag}", lx - 2, ly + 12.0, "F.SilkS", 0.65)
        _hdr_1xn(
            ENDSTOP_FP, jref, f"END_{tag}", lx, ly,
            [
                (None, "", "VCC"),
                (None, "", "GND"),
                (ni, nn, "SIG"),
                (46, "+12V_SNS", "SNS"),
            ],
        )

    field_jacks = []

    r4x, r4y = FP["r4x"], FP["r4y"]
    a('\t(footprint "ESP32_Carrier:R_Axial_4k7_BUP"')
    a('\t\t(layer "F.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {r4x} {r4y})")
    a('\t\t(property "Reference" "R4"')
    a("\t\t\t(at 0 -2.8 0)")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "10k"')
    a("\t\t\t(at 0 2.6 0)")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.75 0.75) (thickness 0.1)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")
    fp_silk_rect(-3.2, -1.5, 3.2, 1.5, "F.SilkS")
    a('\t\t(pad "1" thru_hole rect')
    a("\t\t\t(at -3.75 0)")
    a("\t\t\t(size 1.6 1.6)")
    a("\t\t\t(drill 0.8)")
    a('\t\t\t(layers "*.Cu" "*.Mask")')
    a('\t\t\t(net 37 "OE_595")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(pad "2" thru_hole circle')
    a("\t\t\t(at 3.75 0)")
    a("\t\t\t(size 1.6 1.6)")
    a("\t\t\t(drill 0.8)")
    a('\t\t\t(layers "*.Cu" "*.Mask")')
    a('\t\t\t(net 4 "+3V3")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t)")
    gr_text("R4 LDEN/OE pull-up 10k", r4x - 6, r4y + 4.5, "Cmts.User", 0.6)


    # --- J14 BUP-30S + R1 4k7 pull-up (TOP) — j14 from placement map ---
    # R1 pulls OPTO_IN4 up to +12V_SNS; just south of J14, north of opto LED row
    r1x, r1y = j14x, j14y + 5.2 * PITCH
    gr_box(j14x - 6, j14y - 5, j14x + 6, r1y + 4, "F.SilkS")
    gr_text("J14 BUP-30S NPN", j14x - 3, j14y - 6.5, "F.SilkS", 0.85)
    gr_text("Brn +12 Blu GND Blk OUT Wht CTRL", j14x - 3, j14y + 3 * PITCH + 4.5, "F.SilkS", 0.65)
    gr_text("R1 4k7 pullup NPN", r1x - 5, r1y + 3.5, "F.SilkS", 0.7)
    bup_pads = [
        (1, "+12V", 46, "+12V_SNS"),
        (2, "GND", 2, "GND"),
        (3, "OUT", 28, "/OPTO_IN4"),
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
        a('\t\t\t(layer "Cmts.User")')
        a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.1)) (justify left))")
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
    # R1 between +12V_SNS and OPTO_IN4
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
    a("\t\t\t(at 0 2.6 0)")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.75 0.75) (thickness 0.1)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")
    fp_silk_rect(-3.2, -1.5, 3.2, 1.5, "F.SilkS")
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
    a('\t\t\t(net 28 "/OPTO_IN4")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t)")
    # --- Boot-state passives: R2 (TMC EN pull-up), R3 (BLOWER pull-down),
    # D2 (pump flyback). PCB-only, same as F1 / D1 / the star-power passives.
    def _axial2(fp, ref, val, ax, ay, na, nb, drill, psz, note=""):
        a(f'\t(footprint "ESP32_Carrier:{fp}"')
        a('\t\t(layer "F.Cu")')
        a(f'\t\t(uuid "{uid()}")')
        a(f"\t\t(at {ax} {ay} {rot})")
        a(f'\t\t(property "Reference" "{ref}"')
        a(f"\t\t\t(at 0 -2.6 {rot})")
        a('\t\t\t(layer "F.SilkS")')
        a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a(f'\t\t(property "Value" "{val}"')
        a(f"\t\t\t(at 0 2.6 {rot})")
        a('\t\t\t(layer "F.SilkS")')
        a("\t\t\t(effects (font (size 0.75 0.75) (thickness 0.1)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a("\t\t(attr through_hole)")
        fp_silk_rect(-3.2, -1.5, 3.2, 1.5, "F.SilkS")
        if "Diode" in fp:
            a("\t\t(fp_line")
            a("\t\t\t(start 2.2 -1.2)")
            a("\t\t\t(end 2.2 1.2)")
            a('\t\t\t(stroke (width 0.12) (type solid))')
            a('\t\t\t(layer "F.SilkS")')
            a(f'\t\t\t(uuid "{uid()}")')
            a("\t\t)")
            fp_silk_text("K", 3.75, -2.2, rot, 0.7)
            fp_silk_text("A", -3.75, -2.2, rot, 0.7)
        else:
            fp_silk_text("1", -3.75, -2.0, rot, 0.55)
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
            gr_text(note, ax - 7, ay + 4.6, "Cmts.User", 0.6)

    # TMC EN pull-up — south of U3 center (clear MCU Eco)
    _axial2("R_Axial_4k7_BUP", "R2", "10k", tx + 2.0, ty + 16.0,
            (11, "/EN_TMC"), (4, "+3V3"), 0.8, 1.6, "R2 EN_TMC pull-up 10k")
    # Blower PD / freewheel beside J16 (keep inside BLOWER Eco Y)
    _axial2("R_Axial_4k7_BUP", "R3", "10k", j16x - 8.0, j16y + 2.0,
            (55, "/BLOWER"), (2, "GND"), 0.8, 1.6, "R3 BLOWER pull-down 10k")
    _axial2("Diode_TVS_DO41", "D2", "1N5819", j16x + 8.0, j16y + 2.0,
            (1, "+12V"), (61, "/BLW_RET"), 0.9, 1.7, "D2 K(band)->+12V")

    # BUP GND + OUT → U44 (J14 now sits on field row above opto — short stub)
    p12 = (j14x, j14y)
    pg = (j14x, j14y + PITCH)
    po = (j14x, j14y + 2 * PITCH)
    _jg = pad_world(jx, jy, j1_rot, TB_PITCH / 2, 0)
    track_h(pg[0], pg[0] - 6, pg[1], 2, 0.5)
    via(pg[0] - 6, pg[1], 2, 0.4, 0.8)
    track_v(pg[0] - 6, pg[1], yg, 2, 0.5)
    via(pg[0] - 6, yg, 2)
    track_h(pg[0] - 6, _jg[0], yg, 2, 0.5)
    upt4 = _opto_in_pad_ch(3)  # U44 / R44 OPTO_IN4
    # Vertical drop from J14.OUT to LED pad under it
    x_drop = po[0]
    track_v(x_drop, po[1], upt4[1], 28, 0.35)
    via(x_drop, upt4[1], 28, 0.4, 0.8)
    track_h(x_drop, upt4[0], upt4[1], 28, 0.35)
    # R1 below J14: pad1 (+12V_SNS) ↔ pin1, pad2 (OPTO_IN4) ↔ pin3
    track_v(r1x - 3.75, r1y, p12[1], 46, 0.4)
    via(r1x - 3.75, p12[1], 46, 0.4, 0.8)
    track_h(r1x - 3.75, p12[0], p12[1], 46, 0.4)
    track_v(r1x + 3.75, r1y, po[1], 28, 0.4)
    via(r1x + 3.75, po[1], 28, 0.4, 0.8)
    track_h(r1x + 3.75, po[0], po[1], 28, 0.4)

    # ========== STAR POWER ISOLATION ==========
    # J1 = star hub. Branch MOT 2.5mm / Branch SNS 0.5mm + RC. GND star separately.
    W_MOT = 2.5
    W_SNS = 0.5
    gr_text("STAR +12V: MOT 2.5mm | SNS 0.5mm+RC", ox + 4, oy + 44, "Cmts.User", 0.8)
    gr_text("GND star gap chi gap tai J1-", ox + 4, oy + 46.5, "Cmts.User", 0.8)

    # --- RC filter east+south of J1 (F.Cu); clear of U2; J1 stays leftmost ---
    r10x, r10y = FP["r10x"], FP["r10y"]
    c10x, c10y = FP["c10x"], FP["c10y"]
    c11x, c11y = FP["c10x"] + 8.0, FP["c10y"]
    gr_box(r10x - 4, r10y - 4, c11x + 5, c10y + 5, "F.SilkS")
    gr_text("RC SNS FILTER", r10x - 3, r10y - 5, "F.SilkS", 0.75)
    a('\t(footprint "ESP32_Carrier:R_1206_10R"')
    a('\t\t(layer "F.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {r10x} {r10y})")
    a('\t\t(property "Reference" "R10"')
    a("\t\t\t(at 0 -2 0)")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.1)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "10R"')
    a("\t\t\t(at 0 1.9 0)")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr smd)")
    fp_silk_rect(-1.7, -0.9, 1.7, 0.9, "F.SilkS")
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
    a("\t\t\t(at 0 -4.6 0)")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.1)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "47u/25V"')
    a("\t\t\t(at 0 4.2 0)")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")
    fp_silk_rect(-3.55, -3.55, 3.55, 3.55, "F.SilkS")
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
    a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.1)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "100n"')
    a("\t\t\t(at 0 1.8 0)")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr smd)")
    fp_silk_rect(-1.1, -0.7, 1.1, 0.7, "F.SilkS")
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
    # Star spur: J1+ -> R10 (same nets); Manhattan — H on F, V on B
    track_h(j1_12[0], r10x - 1.4, j1_12[1], 1, W_SNS)
    via(r10x - 1.4, j1_12[1], 1, 0.4, 0.8)
    track_v(r10x - 1.4, j1_12[1], r10y, 1, W_SNS)
    sns_x = ox + bw - 28.0  # clear of BYJ jack column / power buses
    y_sns = yg - 3.0
    via(r10x + 1.4, r10y, 46, 0.4, 0.8)
    track_h(r10x + 1.4, sns_x, r10y, 46, W_SNS)
    track_h(c10x - 1.25, r10x + 1.4, c10y, 46, W_SNS)
    track_h(c11x - 0.95, r10x + 1.4, c11y, 46, W_SNS)
    track_v(r10x + 1.4, r10y, c10y, 46, W_SNS)
    via(sns_x, r10y, 46, 0.4, 0.8)
    track_v(sns_x, r10y, y_sns, 46, W_SNS)
    via(sns_x, y_sns, 46, 0.4, 0.8)
    track_h(sns_x, ox + 50.0, y_sns, 46, W_SNS)
    # SNS GND back to J1-
    j1_gnd = pad_world(jx, jy, j1_rot, TB_PITCH / 2, 0)
    track_v(c10x + 1.25, c10y, j1_gnd[1] + 6, 2, W_SNS)
    via(c10x + 1.25, j1_gnd[1] + 6, 2, 0.4, 0.8)
    track_h(c10x + 1.25, j1_gnd[0], j1_gnd[1] + 6, 2, W_SNS)
    via(j1_gnd[0], j1_gnd[1] + 6, 2, 0.4, 0.8)
    track_v(j1_gnd[0], j1_gnd[1] + 6, j1_gnd[1], 2, W_SNS)
    track_h(c11x + 0.95, c10x + 1.25, c11y, 2, W_SNS)

    for di, (px, py) in enumerate(home_limit_pos):
        # SNS pad = pin4 at local y=3*PITCH on 1×04 endstop
        pad_y = py + 3 * PITCH
        xs = px - 3.0 - di * 0.8
        via(xs, y_sns, 46, 0.4, 0.8)
        track_v(xs, y_sns, pad_y, 46, W_SNS)
        via(xs, pad_y, 46, 0.4, 0.8)
        track_h(xs, px, pad_y, 46, W_SNS)
    xs14 = j14x - 4.0
    via(xs14, y_sns, 46, 0.4, 0.8)
    track_v(xs14, y_sns, j14y, 46, W_SNS)
    via(xs14, j14y, 46, 0.4, 0.8)
    track_h(xs14, j14x, j14y, 46, W_SNS)

    # --- Bulk: C20 SE of TMC; C21 near AXIS1 ULN COM ---
    bulk_places = [
        ("C20", "CP_Radial_D8_470u_25V", "470u/25V", tx + 12.0, ty + 16.0, "TMC"),
        ("C21", "CP_Radial_D6_100u_25V", "100u/25V", FP["c21x"], FP["c21y"], "ULN"),
    ]
    for ref, fp, val, bx, by, tag in bulk_places:
        pitch_c = 3.5 if "470" in val else 2.5
        half = pitch_c / 2
        body = 4.4 if "470" in val else 3.55
        gr_text(f"{ref} {val} {tag}", bx - 4, by - body - 2.0, "Cmts.User", 0.6)
        a(f'\t(footprint "ESP32_Carrier:{fp}"')
        a('\t\t(layer "F.Cu")')
        a(f'\t\t(uuid "{uid()}")')
        a(f"\t\t(at {bx} {by} {rot})")
        a(f'\t\t(property "Reference" "{ref}"')
        a(f"\t\t\t(at 0 {-body - 1.2} {rot})")
        a('\t\t\t(layer "F.SilkS")')
        a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.1)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a(f'\t\t(property "Value" "{val}"')
        a(f"\t\t\t(at 0 {body + 1.2} {rot})")
        a('\t\t\t(layer "F.SilkS")')
        a("\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a("\t\t(attr through_hole)")
        fp_silk_rect(-body, -body, body, body, "F.SilkS")
        # Electrolytic: pad1 = + (rect); silk + follows PART_ROT
        fp_silk_text("+", -half, -body - 0.2, rot, 0.9)
        fp_silk_text("-", half, -body - 0.2, rot, 0.7)
        a('\t\t(pad "1" thru_hole rect')
        a(f"\t\t\t(at {-half} 0)")
        a("\t\t\t(size 1.8 1.8)")
        a("\t\t\t(drill 0.9)")
        a('\t\t\t(layers "*.Cu" "*.Mask")')
        a('\t\t\t(net 1 "+12V")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a('\t\t(pad "2" thru_hole circle')
        a(f"\t\t\t(at {half} 0)")
        a("\t\t\t(size 1.8 1.8)")
        a("\t\t\t(drill 0.9)")
        a('\t\t\t(layers "*.Cu" "*.Mask")')
        a('\t\t\t(net 2 "GND")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a("\t)")
        p12b = pad_world(bx, by, rot, -half, 0.0)
        pgdb = pad_world(bx, by, rot, half, 0.0)
        y12b = min(p12b[1], pgdb[1]) - 5.0
        ygdb = max(p12b[1], pgdb[1]) + 5.0
        track_h(p12b[0], x12_drv, y12b, 1, W_MOT)
        via(p12b[0], y12b, 1, 0.45, 0.9)
        track_v(p12b[0], y12b, p12b[1], 1, 1.0)
        track_h(pgdb[0], xg_drv, ygdb, 2, W_MOT)
        via(pgdb[0], ygdb, 2, 0.45, 0.9)
        track_v(pgdb[0], ygdb, pgdb[1], 2, 1.0)

    # ========== CLUSTER OUTLINES (all TOP / Eco1 cyan) ==========
    # Same-function modules share one labeled AABB. Boxes are the UNION of
    # member courtyards so no jack/module/discrete sits outside (E11.14).
    # Same-face boxes must not intersect (E11.9).
    def _union_aabb(boxes: list[tuple[float, float, float, float]], pad: float = 0.5):
        if not boxes:
            raise SystemExit("cluster has no member boxes")
        x0 = min(b[0] for b in boxes) - pad
        y0 = min(b[1] for b in boxes) - pad
        x1 = max(b[2] for b in boxes) + pad
        y1 = max(b[3] for b in boxes) + pad
        return x0, y0, x1, y1

    def _hdr_aabb(ax, ay, n_pins, hrot=0, cy=1.5):
        span = (n_pins - 1) * PITCH
        return local_rect_world_aabb(ax, ay, hrot, -cy, -cy, cy, span + cy)

    def _dip16_aabb(ax, ay, drot=0):
        hxr = DIP16_BODY_W / 2 + 0.2
        hl = DIP16_BODY_L / 2 + 0.15
        return local_rect_world_aabb(ax, ay, drot, -hxr, -hl, hxr, hl)

    def _axial_aabb(ax, ay, half=4.0, hy=2.2, r=0):
        # Match silk/pad envelope of R_Axial / diode (±3.75 pad + silk)
        return local_rect_world_aabb(ax, ay, r, -half, -hy, half, hy)

    def _radial_aabb(ax, ay, body, half_pitch, r=0):
        b = body + 0.6
        return local_rect_world_aabb(ax, ay, r, -b, -b, b, b)

    # --- member courtyards ---
    hmi_boxes = [
        _hdr_aabb(j3x, j3y, TFT_LCD_PINS),
        _hdr_aabb(j23x, j23y, TFT_TP_PINS),
        _hdr_aabb(j18x, j18y, ENC_PINS, enc_rot),
        _hdr_aabb(j15x, j15y, 3),
    ]
    bup_boxes = [
        _hdr_aabb(j14x, j14y, 4),
        _axial_aabb(r1x, r1y),
    ]

    blower_boxes = [
        _hdr_aabb(j16x, j16y, 4),
        _axial_aabb(j16x - 8.0, j16y + 2.0),
        _axial_aabb(j16x + 8.0, j16y + 2.0),
    ]
    c21x, c21y = FP["c21x"], FP["c21y"]
    shift_boxes = [
        _hdr_aabb(u10_ctrl_x, u10_y0, 6),
        _hdr_aabb(u10_q_x, u10_y0, 24),
        _axial_aabb(r4x, r4y, half=3.8, hy=1.8),
        (mod_x0, mod_y0, mod_x1, mod_y1),
    ]
    axis_defs = [
        (home_jacks[0], (u5x, u5y), byj_jacks[0], "A1: HOME1+U5+J5"),
        (home_jacks[1], (u6x, u6y), byj_jacks[1], "A2: HOME2+U6+J6"),
        (home_jacks[2], (u7x, u7y), byj_jacks[2], "A3: HOME3+U7+J7"),
    ]
    axis_box_lists = []
    for i, (hj, (ux, uy), bj, _lab) in enumerate(axis_defs):
        boxes = [
            _hdr_aabb(hj[1], hj[2], 4),
            _dip16_aabb(ux, uy, dip_rot),
            _hdr_aabb(bj[1], bj[2], 5, byj_rot),
        ]
        if i == 0:
            boxes.append(_radial_aabb(c21x, c21y, 3.55, 1.25))
        axis_box_lists.append(boxes)
    power_boxes = [
        local_rect_world_aabb(jx, jy, j1_rot, -5.5, -4.5, 5.5, 4.5),
        local_rect_world_aabb(f1x, f1y, rot, -5.0, -5.0, 5.0, 5.0),
        local_rect_world_aabb(d1x, d1y, rot, -4.0, -2.5, 4.0, 2.5),
        local_rect_world_aabb(
            mx, my, rot,
            -MP1584_W / 2 - 0.5, -MP1584_H / 2 - 0.5,
            MP1584_W / 2 + 0.5, MP1584_H / 2 + 0.5,
        ),
        local_rect_world_aabb(r10x, r10y, 0, -2.0, -1.2, 2.0, 1.2),
        local_rect_world_aabb(c10x, c10y, 0, -2.2, -2.2, 2.2, 2.2),
        local_rect_world_aabb(c11x, c11y, 0, -2.2, -2.2, 2.2, 2.2),
    ]
    mcu_boxes = [(fx + _u1_lx0, fy + _u1_ly0, fx + _u1_lx1, fy + _u1_ly1)]
    tmc_boxes = [
        local_rect_world_aabb(tx, ty, tmc_rot, -TMC_W / 2, -TMC_H / 2, TMC_W / 2, TMC_H / 2),
        _axial_aabb(tx + 2.0, ty + 16.0),
        _radial_aabb(tx + 12.0, ty + 16.0, 4.4, 1.75),
    ]
    opto_boxes = []
    for i, _ch in enumerate(OPTO_CH):
        col, row = i % 4, i // 4
        ux = opto_origin[0] + col * opto_col_pitch
        uy = opto_origin[1] + row * opto_row_pitch
        silk_hx = DIP4_BODY_W / 2 + 1.2
        opto_boxes.append(local_rect_world_aabb(
            ux, uy, rot4,
            -silk_hx, -DIP4_BODY_L / 2 - 0.5, silk_hx, DIP4_BODY_L / 2 + 0.5,
        ))
        opto_boxes.append(_axial_aabb(ux - 3.5, uy - 8.5))
        opto_boxes.append(_axial_aabb(ux + 3.5, uy + 8.5))

    # pad=0: member AABBs already include silk/crt margin
    cluster_outline("C: HMI  J17 LCD + J23 TP + J18 ENC + J15 BZ", *_union_aabb(hmi_boxes, pad=0.2), face="F", pad=0)
    cluster_outline("U: BUP-30S  J14 + R1 4k7", *_union_aabb(bup_boxes, pad=0.2), face="F", pad=0)
    cluster_outline("B: BLOWER  J16 AOD4184 + R3/D2", *_union_aabb(blower_boxes, pad=0.2), face="F", pad=0)
    cluster_outline("5: SHIFT  U10 595-24IO + J24/J25 + R4", *_union_aabb(shift_boxes, pad=0.2), face="F", pad=0)
    for boxes, (_hj, _u, _bj, lab) in zip(axis_box_lists, axis_defs):
        cluster_outline(lab, *_union_aabb(boxes, pad=0.2), face="F", pad=0)
    cluster_outline("1: POWER  J1+F1+D1+U2+RC", *_union_aabb(power_boxes, pad=0.2), face="F", pad=0)
    cluster_outline("2: MCU  U1 ESP32-S3 DevKitC", *_union_aabb(mcu_boxes, pad=0.2), face="F", pad=0)
    cluster_outline("3: TMC  U3 + Mot pins (NEMA17 on module)", *_union_aabb(tmc_boxes, pad=0.2), face="F", pad=0)
    cluster_outline("4: OPTO  U41-U44 PC817 + R2k2/10k", *_union_aabb(opto_boxes, pad=0.2), face="F", pad=0)

    # E11.9 — same-face cluster outlines must not cut each other
    # E11.2 — same-face Ecos keep ≥ MODULE_CLUSTER_GAP (AABB separation)
    for i, (fa, la, ax0, ay0, ax1, ay1) in enumerate(cluster_boxes):
        for fb, lb, bx0, by0, bx1, by1 in cluster_boxes[i + 1 :]:
            if fa != fb:
                continue
            ox_ = min(ax1, bx1) - max(ax0, bx0)
            oy_ = min(ay1, by1) - max(ay0, by0)
            if ox_ > 0 and oy_ > 0:
                raise SystemExit(
                    f"E11.9 cluster overlap [{fa}] {la!r} x {lb!r}: "
                    f"{ox_:.1f}x{oy_:.1f} mm — adjust placement"
                )
            # Separation: if boxes share a projected strip, measure gap on the other axis
            if ox_ > 0:
                gap = max(ay0, by0) - min(ay1, by1)
                if 0 < gap < MODULE_CLUSTER_GAP - 0.05:
                    raise SystemExit(
                        f"E11.2 cluster gap Y [{fa}] {la!r} x {lb!r}: "
                        f"{gap:.1f} mm < {MODULE_CLUSTER_GAP} mm"
                    )
            if oy_ > 0:
                gap = max(ax0, bx0) - min(ax1, bx1)
                if 0 < gap < MODULE_CLUSTER_GAP - 0.05:
                    raise SystemExit(
                        f"E11.2 cluster gap X [{fa}] {la!r} x {lb!r}: "
                        f"{gap:.1f} mm < {MODULE_CLUSTER_GAP} mm"
                    )

    # E11.12 — every non-MCU Eco ≥ MODULE_MCU_CLEAR from MCU Eco
    mcu_box = next((c for c in cluster_boxes if c[1].startswith("2: MCU")), None)
    if mcu_box is None:
        raise SystemExit("E11.12: MCU cluster missing")
    _, _, mx0, my0, mx1, my1 = mcu_box
    for face, label, ax0, ay0, ax1, ay1 in cluster_boxes:
        if label.startswith("2: MCU"):
            continue
        # Expand MCU by MODULE_MCU_CLEAR; other Eco must not intersect
        kx0, ky0 = mx0 - MODULE_MCU_CLEAR, my0 - MODULE_MCU_CLEAR
        kx1, ky1 = mx1 + MODULE_MCU_CLEAR, my1 + MODULE_MCU_CLEAR
        ox_ = min(ax1, kx1) - max(ax0, kx0)
        oy_ = min(ay1, ky1) - max(ay0, ky0)
        if ox_ > 0 and oy_ > 0:
            # Actual AABB gap to MCU (positive = separated)
            gx = max(ax0, mx0) - min(ax1, mx1)
            gy = max(ay0, my0) - min(ay1, my1)
            if gx < 0 and gy < 0:
                raise SystemExit(f"E11.12 {label!r} overlaps MCU Eco")
            # Chebyshev-style: min axis gap when separated on one axis
            if gx >= 0 and gy < 0:
                gap = gx
            elif gy >= 0 and gx < 0:
                gap = gy
            else:
                gap = min(gx, gy) if gx >= 0 and gy >= 0 else 0.0
            if gap < MODULE_MCU_CLEAR - 0.05:
                raise SystemExit(
                    f"E11.12 {label!r} too close to MCU: gap={gap:.1f} mm "
                    f"(need ≥{MODULE_MCU_CLEAR} mm)"
                )

    # E11.14 — every non-mount footprint courtyard must lie in some Eco1 cluster
    # (checked after write via _check_cluster_cover.py; members above define boxes).

    # E11.10 — module clusters ≥ MODULE_EDGE_CLEAR from Edge.Cuts
    for face, label, ax0, ay0, ax1, ay1 in cluster_boxes:
        if (
            ax0 < ox + MODULE_EDGE_CLEAR - 0.05
            or ay0 < oy + MODULE_EDGE_CLEAR - 0.05
            or ax1 > ox + bw - MODULE_EDGE_CLEAR + 0.05
            or ay1 > oy + bh - MODULE_EDGE_CLEAR + 0.05
        ):
            raise SystemExit(
                f"E11.10 cluster too close to edge [{face}] {label!r}: "
                f"box=({ax0:.1f},{ay0:.1f})-({ax1:.1f},{ay1:.1f}) "
                f"need ≥{MODULE_EDGE_CLEAR} mm inside "
                f"({ox + MODULE_EDGE_CLEAR:.0f},{oy + MODULE_EDGE_CLEAR:.0f})-"
                f"({ox + bw - MODULE_EDGE_CLEAR:.0f},{oy + bh - MODULE_EDGE_CLEAR:.0f})"
            )

    # MOT already fed via y12 spine + right buses — no extra mid-board crossbars.

    a(")")
    text = "\n".join(lines) + "\n"
    if RUN_MAZE:
        text = strip_routes(text)
        pads = parse_pads(text)
        kept = parse_kept_vias(text)
        keepouts = parse_keepout_holes(text)
        hole_sites = parse_hole_sites(text)
        print(
            f"Maze autoroute: {len(pads)} pads, {len(hole_sites)} drill sites, no extra vias, "
            f"grid board {bw:.0f}x{bh:.0f} mm @ origin ({ox},{oy})"
        )
        result = autoroute_pads(
            pads, ox, oy, bw, bh, kept, grid=0.55, hole_sites=hole_sites
        )
        print(
            f"Maze result: {len(result.segments)} segments, {len(result.vias)} vias, "
            f"{len(result.failed)} failed edges"
        )
        for net, name, axy, bxy in result.failed[:20]:
            print(f"  FAIL net {net} {name} {axy} -> {bxy}")
        text = inject_routes(text, format_routes(result, uid))
        print("Service buses (clearance-aware B.Cu lanes)…")
        text, bus = emit_service_buses(text, ox, oy, bw, bh, uid_fn=uid)
        print(f"  buses: +{len(bus.segments)} segments")
        print("Repair open copper islands (clearance-aware)…")
        for rnd in range(12):
            text, repair = repair_open_pcb(text, ox, oy, bw, bh, uid_fn=uid)
            print(
                f"  round {rnd + 1}: +{len(repair.segments)} segments, "
                f"{len(repair.failed)} failed"
            )
            if not repair.segments:
                break
        if not text.endswith("\n"):
            text += "\n"
    # Net names must not carry a leading slash. KiCad treats "/" as the
    # hierarchy separator, so a global label written "/STEP" comes back as the
    # net "{slash}STEP" — which never matches a pad called "/STEP", and every
    # signal net then shows up as a schematic-parity conflict. Bare names are
    # what a KiCad-native flow produces anyway.
    text = re.sub(r'\(net (\d+) "/', r'(net \1 "', text)
    text = re.sub(r'\(net "/', '(net "', text)
    out = ROOT / "esp32_baseboard.kicad_pcb"
    out.write_text(text, encoding="utf-8")
    return out


def write_readme() -> Path:
    text = """# ESP32-S3 Baseboard — BOM (ULN2003 + 74HC595-24IO module)

**Full module list:** see [`MODULES.md`](MODULES.md).

PSU **Mean Well 12V**. Limits = mechanical HOME only (J8/J10/J12). Board is jacks + drivers.

## On-board

| Ref | Part | Role |
|-----|------|------|
| J1 / F1 / D1 | Terminal + PTC + TVS | 12V in + protect |
| U1 | ESP32-S3-DevKitC-1 N16R8 | MCU |
| U2 | MP1584EN 5V | Logic buck (only) |
| U3 | TMC2209 | NEMA17 trên Mot (không J2) |
| U41–U44 | PC817 DIP-4 ×4 | HOME1-3 + BUP |
| R41–R44 | 2k2 axial | LED series (~5 mA @12V) |
| R45–R48 | 10k axial | Collector pull-up → +3V3 |
| **U10** | **74HC595-24IO module** (3×595) | [Shopee](https://shopee.vn/-C%C3%B3-s%E1%BA%B5n-M%E1%BA%A1ch-m%E1%BB%9F-r%E1%BB%99ng-I-O-24-ch%C3%A2n-74HC595-thegioimodule-i.951399259.42633627766) — **bên phải ESP32** |
| J24 / J25 | Header cái 1×6 + 1×24 | CTRL + Q (cắm module) |
| R4 | 10k axial | LDEN/`OE` pull-up → +3V3 |
| U5–U7 | **ULN2003AN** DIP-16 | 28BYJ; IN←SR_Q*; COM=+12V |
| R1 | 4k7 | BUP NPN pull-up → OPTO_IN4 |
| R2/R3 | 10k | EN_TMC PU / BLOWER PD |
| C20 | 470µ | Bulk @ TMC |
| C21 | 100µ | Shared ULN COM bulk |
| ~~J2~~ | — | **XOÁ** (Mot trên U3) |
| J5–J7 | **1×05** | 28BYJ-48 |
| J8/J10/J12 | 1×04 endstop | HOME NC @12V → opto |
| J14 | 1×04 | BUP-30S |
| J15–J18/J23 | — | Buzzer / TFT LCD+touch / EC11 |

**Deleted:** J2, J4/J9/J11/J13, J19–J22 field (optional later), U4/U9, DRV8871.

> All footprints on **TOP (F.Cu)**; B.Cu for routing only.

## GPIO

| Function | GPIO |
|----------|------|
| HOME OUT1-3 / BUP OUT4 | IO1,2,4,5 |
| SER / SRCLK / RCLK / OE_595 | IO10–13 |
| TMC STEP/DIR/EN | IO16–18 |
| TFT SPI + BL + touch | IO39/40/42/21/46/45 + MISO47 T_CS48 T_IRQ6 |
| ENC_A / ENC_B | IO38 / IO41 |
| Buzzer / blower | IO9 / IO3 |
| Spare | IO7,8,14,15 |

## Regenerate

```
$env:PCB_SKIP_MAZE=1; python gen_power_carrier.py
```

Board size target **220×160 mm**. Modules ≥10 mm from edge; ≥10 mm from MCU Eco; ≥8 mm between Ecos. Power netclass track **0.70 mm** (matches FreeRouting).
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
                {
                    "name": "Power",
                    "clearance": 0.25,
                    "track_width": 0.70,
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
        write_mounting_hole_m3(),
        write_esp32_footprint(),
        write_mini560_footprint(),
        write_screw_terminal_footprint(),
        write_ptc_fuse_footprint(),
        write_tvs_do41_footprint(),
        write_tmc2209_footprint(),
        write_pc817_dip4_footprint(),
        write_uln2003_footprint(),
        write_74hc595_footprint(),
        write_pin_header_footprint(4, "PinHeader_1x04_Motor", [p[1] for p in MOTOR_HEADER]),
        write_pin_header_footprint(TFT_LCD_PINS, TFT_LCD_FP, [p[1] for p in TFT_LCD_HEADER]),
        write_pin_header_footprint(TFT_TP_PINS, TFT_TP_FP, [p[1] for p in TFT_TP_HEADER]),
        write_pin_header_footprint(3, "PinHeader_1x03_Buzzer", [p[1] for p in BUZZER_HEADER]),
        write_pin_header_footprint(4, "PinHeader_1x04_MOSFET", [p[1] for p in MOSFET_HEADER]),
        write_pin_header_footprint(ENC_PINS, ENC_FP, [p[1] for p in ENC_HEADER]),
        write_pin_header_footprint(5, BYJ_FP, [p[1] for p in BYJ_HEADER]),
        write_pin_header_footprint(6, "PinHeader_1x06_595CTRL",
                                  ["LDEN", "GND", "VCC", "LDSI", "LDSTR", "LDSCK"]),
        write_pin_header_footprint(24, "PinHeader_1x24_595Q",
                                  [f"{i//8+1}_Q{i%8}" for i in range(24)]),
        write_pin_header_footprint(4, ENDSTOP_FP, [p[1] for p in ENDSTOP_HEADER]),
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
    # E11.14 — every non-mount part must sit in an Eco1 cluster
    import subprocess
    cov = subprocess.run(
        [sys.executable, str(ROOT / "_check_cluster_cover.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    print(cov.stdout, end="")
    if cov.returncode != 0:
        raise SystemExit("E11.14 FAIL — footprint pads outside Eco1 clusters")



if __name__ == "__main__":
    main()
