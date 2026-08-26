#!/usr/bin/env python3
"""Apply ESP32-S3 + DRV8871 + HMI jack upgrade to gen_power_carrier.py and regenerate."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GEN = ROOT / "gen_power_carrier.py"

sys.path.insert(0, str(ROOT))
from s3_pinmap import (  # noqa: E402
    DRV_MOTORS,
    OPTO_GPIO,
    PIN_BY_NAME,
    pad_local,
)

NEW_HEADER = '''#!/usr/bin/env python3
"""Generate Mini560 + TMC2209 + PC817 + 3x DRV8871 + ESP32-S3 carrier.

Power path (modules on BOTTOM):
  12V-3A PSU --J1--> +12V/GND
       --> Mini560 (U2) buck 12V->5V -> ESP32-S3 5V pin
       --> TMC2209 (U3) VM=12V + VIO=3V3
       --> DRV8871 x3 (U5-U7) VM=12V
TOP: J2 NEMA17, J4 OPTO field, J5-J13 motors+limits, J14 BUP,
     J15 buzzer, J16 MOSFET blower, J17 TFT+touch.
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

# Mini560 ~29-30 x 18 mm stamp-hole module (VIN+/VIN-/VOUT+/VOUT-)
MINI560_W = 30.0
MINI560_H = 18.0
MINI560_PAD_SPAN_X = 25.4
MINI560_PAD_SPAN_Y = 2.54

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
TFT_HEADER = [
    ("1", "GND"),
    ("2", "3V3"),
    ("3", "SCK"),
    ("4", "MOSI"),
    ("5", "MISO"),
    ("6", "CS"),
    ("7", "DC"),
    ("8", "SDA"),
    ("9", "SCL"),
    ("10", "BL"),
]

BUZZER_HEADER = [("1", "VCC5"), ("2", "GND"), ("3", "SIG")]
MOSFET_HEADER = [("1", "SIG"), ("2", "GND"), ("3", "LOAD+"), ("4", "LOAD-")]

VIA12_DRILL = 0.6
VIA12_DIA = 1.1
VIA12_COUNT_X = 3
VIA12_COUNT_Y = 2
VIA12_PITCH = 1.8

PC817_W = 100.0
PC817_H = 28.0
PC817_ROW = 20.32
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

'''


def replace_between(text: str, start_pat: str, end_pat: str, new_block: str) -> str:
    m0 = re.search(start_pat, text)
    if not m0:
        raise SystemExit(f"start not found: {start_pat}")
    m1 = re.search(end_pat, text[m0.end() :])
    if not m1:
        raise SystemExit(f"end not found after start: {end_pat}")
    end = m0.end() + m1.start()
    return text[: m0.start()] + new_block + text[end:]


def main() -> None:
    src = GEN.read_text(encoding="utf-8")

    # Keep from first "def pad_world" onward, replace preamble
    idx = src.find("def pad_world")
    if idx < 0:
        raise SystemExit("def pad_world not found")
    body = src[idx:]

    # --- rename / rewrite ESP32 footprint ---
    body = body.replace("ESP32_DevKit_V1_30Pin_Socket", "ESP32_S3_DevKitC_44Pin_Socket")
    body = body.replace("ESP32_DevKit_V1_30Pin", "ESP32_S3_DevKitC_1")
    body = body.replace("ESP32 DevKit V1 30-pin", "ESP32-S3-DevKitC-1 44-pin")
    body = body.replace("ESP32 DevKit V1 30 pin", "ESP32-S3-DevKitC-1 44-pin")
    body = body.replace("30-pin", "44-pin")
    body = body.replace("30 pin", "44 pin")

    # Fix write_esp32_footprint for 22 pins/side
    old_fp = '''def write_esp32_footprint() -> Path:
    """Keep ESP32 socket footprint in sync."""
    y_last = (15 - 1) * PITCH'''
    new_fp = '''def write_esp32_footprint() -> Path:
    """ESP32-S3-DevKitC-1 female socket (2x22)."""
    y_last = (S3_PINS_PER_SIDE - 1) * PITCH'''
    if old_fp not in body:
        # already patched or different
        body = body.replace(
            "y_last = (15 - 1) * PITCH",
            "y_last = (S3_PINS_PER_SIDE - 1) * PITCH",
            1,
        )
    else:
        body = body.replace(old_fp, new_fp, 1)

    body = body.replace(
        'a(\'(footprint "ESP32_S3_DevKitC_44Pin_Socket"\')',
        'a(\'(footprint "ESP32_S3_DevKitC_44Pin_Socket"\')',
    )
    # Right column pad Y: was (num-16), now (num-23)
    body = body.replace(
        "y = (num - 16) * PITCH",
        "y = (num - 23) * PITCH",
    )

    # Symbol lib: 15 -> 22 pins
    body = body.replace(
        "pin_ys = [17.78 - i * 2.54 for i in range(15)]",
        "pin_ys = [26.67 - i * 2.54 for i in range(S3_PINS_PER_SIDE)]",
    )

    # L298N -> DRV8871 footprint rewrite
    drv_fp = '''def write_l298n_footprint() -> Path:
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
    a("\\t(version 20260206)")
    a('\\t(generator "gen_power_carrier.py")')
    a('\\t(generator_version "2.0")')
    a('\\t(layer "F.Cu")')
    a('\\t(descr "DRV8871 DC motor driver ~28x20mm for GA12-N20. VERIFY before fab.")')
    a('\\t(tags "DRV8871 DC motor driver")')
    a('\\t(property "Reference" "U**"')
    a(f'\\t\\t(at 0 {{-DRV_H / 2 - 1.8}} 0)')
    a('\\t\\t(layer "F.SilkS")')
    a("\\t\\t(effects (font (size 1 1) (thickness 0.15)))")
    a("\\t)")
    a('\\t(property "Value" "DRV8871_Module"')
    a(f'\\t\\t(at 0 {{DRV_H / 2 + 1.8}} 0)')
    a('\\t\\t(layer "F.Fab")')
    a("\\t\\t(effects (font (size 1 1) (thickness 0.15)))")
    a("\\t)")
    a("\\t(attr through_hole)")
    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
        a("\\t(fp_rect")
        a(f"\\t\\t(start {{-DRV_W / 2}} {{-DRV_H / 2}})")
        a(f"\\t\\t(end {{DRV_W / 2}} {{DRV_H / 2}})")
        a(f"\\t\\t(stroke (width {{w}}) (type solid))")
        a("\\t\\t(fill none)")
        a(f'\\t\\t(layer "{{layer}}")')
        a("\\t)")
    a('\\t(fp_text user "DRV8871"')
    a("\\t\\t(at 0 0 0)")
    a('\\t\\t(layer "F.SilkS")')
    a('\\t\\t(effects (font (size 1.0 1.0) (thickness 0.15)))')
    a("\\t)")
    for i, (num, name, x, y) in enumerate(pads):
        a(f'\\t(fp_text user "{{name}}"')
        a(f"\\t\\t(at {{x}} {{y - 2.0}} 0)")
        a('\\t\\t(layer "F.SilkS")')
        a('\\t\\t(effects (font (size 0.65 0.65) (thickness 0.1)))')
        a("\\t)")
        shape = "rect" if i == 0 else "circle"
        a(f'\\t(pad "{{num}}" thru_hole {{shape}}')
        a(f"\\t\\t(at {{x}} {{y}})")
        a("\\t\\t(size 1.8 1.8)")
        a("\\t\\t(drill 1.0)")
        a('\\t\\t(layers "*.Cu" "*.Mask")')
        a("\\t)")
    a(")")
    out = PRETTY / "DRV8871_Module.kicad_mod"
    out.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
    return out


'''
    # Use real newlines in written function - rewrite without double escaping
    drv_fp = '''def write_l298n_footprint() -> Path:
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
    out.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
    return out


'''
    # Fix the write_text join - the function body when embedded in apply script needs proper code
    # I'll write drv function to a separate file instead
    (ROOT / "_drv8871_fp_snippet.py").write_text(
        '''def write_l298n_footprint() -> Path:
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
    a("\\t(version 20260206)")
    a('\\t(generator "gen_power_carrier.py")')
    a('\\t(generator_version "2.0")')
    a('\\t(layer "F.Cu")')
    a('\\t(descr "DRV8871 DC motor driver ~28x20mm for GA12-N20. VERIFY before fab.")')
    a('\\t(tags "DRV8871 DC motor driver")')
    a('\\t(property "Reference" "U**"')
    a(f"\\t\\t(at 0 {{-DRV_H / 2 - 1.8}} 0)")
    a('\\t\\t(layer "F.SilkS")')
    a("\\t\\t(effects (font (size 1 1) (thickness 0.15)))")
    a("\\t)")
    a('\\t(property "Value" "DRV8871_Module"')
    a(f"\\t\\t(at 0 {{DRV_H / 2 + 1.8}} 0)")
    a('\\t\\t(layer "F.Fab")')
    a("\\t\\t(effects (font (size 1 1) (thickness 0.15)))")
    a("\\t)")
    a("\\t(attr through_hole)")
    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
        a("\\t(fp_rect")
        a(f"\\t\\t(start {{-DRV_W / 2}} {{-DRV_H / 2}})")
        a(f"\\t\\t(end {{DRV_W / 2}} {{DRV_H / 2}})")
        a(f"\\t\\t(stroke (width {{w}}) (type solid))")
        a("\\t\\t(fill none)")
        a(f'\\t\\t(layer "{{layer}}")')
        a("\\t)")
    a('\\t(fp_text user "DRV8871"')
    a("\\t\\t(at 0 0 0)")
    a('\\t\\t(layer "F.SilkS")')
    a('\\t\\t(effects (font (size 1.0 1.0) (thickness 0.15)))')
    a("\\t)")
    for i, (num, name, x, y) in enumerate(pads):
        a(f'\\t(fp_text user "{{name}}"')
        a(f"\\t\\t(at {{x}} {{y - 2.0}} 0)")
        a('\\t\\t(layer "F.SilkS")')
        a('\\t\\t(effects (font (size 0.65 0.65) (thickness 0.1)))')
        a("\\t)")
        shape = "rect" if i == 0 else "circle"
        a(f'\\t(pad "{{num}}" thru_hole {{shape}}')
        a(f"\\t\\t(at {{x}} {{y}})")
        a("\\t\\t(size 1.8 1.8)")
        a("\\t\\t(drill 1.0)")
        a('\\t\\t(layers "*.Cu" "*.Mask")')
        a("\\t)")
    a(")")
    out = PRETTY / "DRV8871_Module.kicad_mod"
    out.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
    return out
'''.replace("\\\\n", "\\n").replace("\\\\t", "\\t"),
        encoding="utf-8",
    )

    # Simpler: write DRV function as proper Python file and splice
    drv_code = (ROOT / "libraries").parent  # noqa
    Path(ROOT / "_tmp_drv_fn.py").write_text(
        r'''def write_l298n_footprint() -> Path:
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
''',
        encoding="utf-8",
    )
    drv_fn = (ROOT / "_tmp_drv_fn.py").read_text(encoding="utf-8")
    body = replace_between(
        body,
        r"def write_l298n_footprint\(\) -> Path:",
        r"\ndef write_mini560_footprint\(\) -> Path:",
        drv_fn + "\n\n",
    )

    # Symbol / refs: L298N_Module -> DRV8871_Module (keep write_l298n_footprint name)
    body = body.replace("L298N_Module", "DRV8871_Module")
    body = body.replace("L298N dual", "DRV8871")
    body = body.replace("L298N for GA12", "DRV8871 for GA12")
    body = body.replace("3x L298N", "3x DRV8871")
    body = body.replace("U5/U6/U7 L298N", "U5/U6/U7 DRV8871")
    body = body.replace("L298N GA12", "DRV8871 GA12")
    body = body.replace("tai moi L298N", "tai moi DRV8871")
    body = body.replace("3x L298N + bulk", "3x DRV8871 + bulk")

    # Fix accidental over-replace of write_l298n name is OK

    # Schematic u1_pin for 22 pins
    body = body.replace(
        """    def u1_pin(num: int) -> tuple[float, float]:
        if num <= 15:
            ly = 17.78 - (num - 1) * 2.54
            return (u1[0] - 17.78, u1[1] - ly)
        ly = 17.78 - (num - 16) * 2.54
        return (u1[0] + 17.78, u1[1] - ly)

    u1_3v3 = u1_pin(1)
    u1_io25 = u1_pin(23)  # STEP
    u1_io26 = u1_pin(22)  # DIR
    u1_io27 = u1_pin(21)  # EN
    u1_io32 = u1_pin(25)
    u1_io33 = u1_pin(24)
    u1_io34 = u1_pin(27)
    u1_io35 = u1_pin(26)""",
        """    def u1_pin(num: int) -> tuple[float, float]:
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
    u1_io27 = u1_io_en""",
    )

    # Power wire VIN -> 5V
    body = body.replace("u1_vin = (u1[0] + 17.78, u1[1] - 17.78)  # VIN pin16", "u1_vin = u1_pin(21)  # 5V")
    # If u1_pin not yet defined at that point, order matters - the replace above for u1_vin is BEFORE u1_pin def
    # Looking at original: u1_vin is before u1_pin. Need to fix order.
    body = body.replace(
        "u1_vin = u1_pin(21)  # 5V\n    u1_gnd_r = (u1[0] + 17.78, u1[1] - 15.24)  # GND pin17\n    u1_gnd_l = (u1[0] - 17.78, u1[1] - 15.24)  # GND pin2",
        "u1_gnd_r = None  # set after u1_pin\n    u1_gnd_l = None",
    )

    # After u1_pin block, set gnd and vin
    body = body.replace(
        "u1_io25 = u1_io_step\n    u1_io26 = u1_io_dir\n    u1_io27 = u1_io_en",
        "u1_io25 = u1_io_step\n    u1_io26 = u1_io_dir\n    u1_io27 = u1_io_en\n"
        "    u1_vin = u1_pin(21)\n    u1_gnd_r = u1_pin(22)\n    u1_gnd_l = u1_pin(22)",
    )

    # Opto GPIO pins on schematic - use S3 pad numbers
    opto_pins = [PIN_BY_NAME[n] for _, n in OPTO_GPIO]
    body = body.replace(
        "opto_gpio_pins = [3, 4, 5, 6, 7, 8, 9, 10]",
        f"opto_gpio_pins = {opto_pins}",
    )

    # Motor ESP pin numbers for schematic
    m_pins = [
        (PIN_BY_NAME[DRV_MOTORS[0][1]], PIN_BY_NAME[DRV_MOTORS[0][2]]),
        (PIN_BY_NAME[DRV_MOTORS[1][1]], PIN_BY_NAME[DRV_MOTORS[1][2]]),
        (PIN_BY_NAME[DRV_MOTORS[2][1]], PIN_BY_NAME[DRV_MOTORS[2][2]]),
    ]
    body = body.replace(
        '("U5", "J5", "J8", "J9", 95.25, 203.2, 165.1, 203.2, 11, 14, 3, 4, "TRUC1 MOT+LIM"),\n'
        '        ("U6", "J6", "J10", "J11", 95.25, 241.3, 165.1, 241.3, 15, 18, 5, 6, "TRUC2 MOT+LIM"),\n'
        '        ("U7", "J7", "J12", "J13", 95.25, 279.4, 165.1, 279.4, 19, 20, 7, 8, "TRUC3 MOT+LIM"),',
        f'("U5", "J5", "J8", "J9", 95.25, 203.2, 165.1, 203.2, {m_pins[0][0]}, {m_pins[0][1]}, 3, 4, "TRUC1 MOT+LIM"),\n'
        f'        ("U6", "J6", "J10", "J11", 95.25, 241.3, 165.1, 241.3, {m_pins[1][0]}, {m_pins[1][1]}, 5, 6, "TRUC2 MOT+LIM"),\n'
        f'        ("U7", "J7", "J12", "J13", 95.25, 279.4, 165.1, 279.4, {m_pins[2][0]}, {m_pins[2][1]}, 7, 8, "TRUC3 MOT+LIM"),',
    )

    # DRV symbol uses 6 pins - schematic still loops 1-8; fix to 1-6 and pad locals
    body = body.replace(
        'for n in ["1", "2", "3", "4", "5", "6", "7", "8"]:\n'
        '            parts.append(f\'\\t\\t(pin "{n}" (uuid "{uid()}"))\')',
        'for n in ["1", "2", "3", "4", "5", "6"]:\n'
        '            parts.append(f\'\\t\\t(pin "{n}" (uuid "{uid()}"))\')',
    )

    # Update motor symbol pin world positions for DRV8871 symbol (will redefine symbol)
    # Keep approximate: VM/GND left, IN1/IN2 left, OUT right

    # PCB y_last and esp_net
    body = body.replace(
        '    y_last = 14 * PITCH',
        '    y_last = (S3_PINS_PER_SIDE - 1) * PITCH',
        1,
    )

    new_esp_net = '''    def esp_net(name: str):
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
            "IO41": (49, "/TFT_MISO"),
            "IO42": (50, "/TFT_CS"),
            "IO21": (51, "/TFT_DC"),
            "IO47": (52, "/I2C_SDA"),
            "IO48": (53, "/I2C_SCL"),
            "IO38": (54, "/BUZZER"),
            "IO3": (55, "/BLOWER"),
        }
        return m.get(name)
'''
    body = re.sub(
        r"    def esp_net\(name: str\):.*?return m\.get\(name\)\n",
        new_esp_net,
        body,
        count=1,
        flags=re.S,
    )

    # Add nets 47-55 to nets dict
    body = body.replace(
        '        46: "+12V_SNS",\n    }',
        '        46: "+12V_SNS",\n'
        '        47: "/TFT_SCK",\n'
        '        48: "/TFT_MOSI",\n'
        '        49: "/TFT_MISO",\n'
        '        50: "/TFT_CS",\n'
        '        51: "/TFT_DC",\n'
        '        52: "/I2C_SDA",\n'
        '        53: "/I2C_SCL",\n'
        '        54: "/BUZZER",\n'
        '        55: "/BLOWER",\n'
        "    }",
    )

    # Opto GPIO local pad positions on PCB
    gpio_local_new = "    gpio_local = {\n"
    for gpio, name in OPTO_GPIO:
        pn = PIN_BY_NAME[name]
        lx, ly = pad_local(pn)
        gpio_local_new += f"        {gpio}: ({lx}, {ly}),  # {name} pad {pn}\n"
    gpio_local_new += "    }\n"
    body = re.sub(
        r"    gpio_local = \{.*?\n    \}\n",
        gpio_local_new,
        body,
        count=1,
        flags=re.S,
    )

    # Motor gpio local on PCB
    esp_gpio_items = []
    for _, g1, g2, _, _ in DRV_MOTORS:
        for g in (g1, g2):
            name = f"IO{g}"
            pn = PIN_BY_NAME[name]
            lx, ly = pad_local(pn)
            esp_gpio_items.append(f'        "{name}": ({lx}, {ly}),')
    esp_gpio_block = "    esp_gpio_local = {\n" + "\n".join(esp_gpio_items) + "\n    }\n"
    body = re.sub(
        r"    esp_gpio_local = \{.*?\n    \}\n",
        esp_gpio_block,
        body,
        count=1,
        flags=re.S,
    )

    # Update l298n_pcb motor gpio names
    body = body.replace(
        '("U5", "J5", "J8", "J9", ox + 148.0, oy + 50.0, ox + 70.0, oy + 42.0, 40, 41, 34, 35, "IO21", "IO22", 25, 26),\n'
        '        ("U6", "J6", "J10", "J11", ox + 148.0, oy + 100.0, ox + 105.0, oy + 42.0, 42, 43, 36, 37, "IO23", "IO13", 27, 28),\n'
        '        ("U7", "J7", "J12", "J13", ox + 148.0, oy + 150.0, ox + 140.0, oy + 42.0, 44, 45, 38, 39, "IO12", "IO14", 29, 30),',
        '("U5", "J5", "J8", "J9", ox + 148.0, oy + 50.0, ox + 70.0, oy + 42.0, 40, 41, 34, 35, "IO10", "IO11", 25, 26),\n'
        '        ("U6", "J6", "J10", "J11", ox + 148.0, oy + 100.0, ox + 105.0, oy + 42.0, 42, 43, 36, 37, "IO12", "IO13", 27, 28),\n'
        '        ("U7", "J7", "J12", "J13", ox + 148.0, oy + 150.0, ox + 140.0, oy + 42.0, 44, 45, 38, 39, "IO14", "IO15", 29, 30),',
    )

    # DRV pads on PCB (replace L298N pad list)
    body = body.replace(
        """        l298_pads = [
            ("1", -8.0, -16.0, 1, "+12V"),
            ("2", 0.0, -16.0, 2, "GND"),
            ("3", 8.0, -16.0, 0, ""),
            ("4", -18.0, -6.0, 0, ""),
            ("5", -18.0, 0.0, ni1, f"/DC{mi + 1}_IN1"),
            ("6", -18.0, 6.0, ni2, f"/DC{mi + 1}_IN2"),
            ("7", 18.0, -4.0, nma, f"/MotDC{mi + 1}_A"),
            ("8", 18.0, 4.0, nmb, f"/MotDC{mi + 1}_B"),
        ]""",
        """        l298_pads = [
            ("1", -8.0, -8.0, 1, "+12V"),
            ("2", 0.0, -8.0, 2, "GND"),
            ("3", -10.0, 0.0, ni1, f"/DC{mi + 1}_IN1"),
            ("4", -10.0, 6.0, ni2, f"/DC{mi + 1}_IN2"),
            ("5", 10.0, -4.0, nma, f"/MotDC{mi + 1}_A"),
            ("6", 10.0, 4.0, nmb, f"/MotDC{mi + 1}_B"),
        ]""",
    )
    body = body.replace(
        """        p_vs = pad_world(ux, uy, rot, -8.0, -16.0)
        p_gnd = pad_world(ux, uy, rot, 0.0, -16.0)
        p_in1 = pad_world(ux, uy, rot, -18.0, 0.0)
        p_in2 = pad_world(ux, uy, rot, -18.0, 6.0)
        p_o1 = pad_world(ux, uy, rot, 18.0, -4.0)
        p_o2 = pad_world(ux, uy, rot, 18.0, 4.0)""",
        """        p_vs = pad_world(ux, uy, rot, -8.0, -8.0)
        p_gnd = pad_world(ux, uy, rot, 0.0, -8.0)
        p_in1 = pad_world(ux, uy, rot, -10.0, 0.0)
        p_in2 = pad_world(ux, uy, rot, -10.0, 6.0)
        p_o1 = pad_world(ux, uy, rot, 10.0, -4.0)
        p_o2 = pad_world(ux, uy, rot, 10.0, 4.0)""",
    )

    # Footprint name on PCB for drivers
    body = body.replace('ESP32_Carrier:L298N_Module', 'ESP32_Carrier:DRV8871_Module')
    body = body.replace('ESP32_Carrier:DRV8871_Module', 'ESP32_Carrier:DRV8871_Module')  # noop if already

    # After over-replace, L298N_Module may have become DRV8871_Module already from earlier replace

    # main(): add TFT/buzzer/mosfet headers; remove sensor header
    body = body.replace(
        '        write_pin_header_footprint(6, "PinHeader_1x06_Sensor", [p[1] for p in SENSOR_HEADER]),',
        '        write_pin_header_footprint(10, "PinHeader_1x10_TFT", [p[1] for p in TFT_HEADER]),\n'
        '        write_pin_header_footprint(3, "PinHeader_1x03_Buzzer", [p[1] for p in BUZZER_HEADER]),\n'
        '        write_pin_header_footprint(4, "PinHeader_1x04_MOSFET", [p[1] for p in MOSFET_HEADER]),',
    )

    # README rewrite at end
    readme = '''def write_readme() -> Path:
    text = """# ESP32-S3 Baseboard - Mini560 + TMC2209 + PC817 + 3x DRV8871

## BOM modules

| Mat | Linh kien |
|-----|-----------|
| **Bottom** | J1, U2 Mini560, U3 TMC2209, U4 PC817, **U5/U6/U7 DRV8871**, **U1 ESP32-S3-DevKitC-1** |
| **Top** | J2 NEMA, J4 OPTO, J5-J13 TRUC (MOT+LIM), **J14 BUP-30S**, **J15 Buzzer**, **J16 MOSFET**, **J17 TFT** |

## MCU: ESP32-S3-DevKitC-1 (44-pin)

Socket 2x22 @ 2.54 mm, row 25.4 mm. Cap **5V** tu Mini560 (khong dung VIN kieu DevKit V1).

Khuyen dung **N8R2** (hoac N16R8). Tren N16R8 **khong dung GPIO35/36/37** (Octal flash/PSRAM).

### GPIO map

| Chuc nang | GPIO |
|-----------|------|
| Opto OUT1..6 (limit) | IO1,2,4,5,6,7 |
| Opto OUT7 (BUP) | IO8 |
| Opto OUT8 (spare) | IO9 |
| Motor1 IN1/IN2 | IO10 / IO11 |
| Motor2 | IO12 / IO13 |
| Motor3 | IO14 / IO15 |
| TMC STEP/DIR/EN | IO16 / IO17 / IO18 |
| TFT SCK/MOSI/MISO/CS/DC | IO39 / IO40 / IO41 / IO42 / IO21 |
| Touch I2C SDA/SCL | IO47 / IO48 |
| Buzzer | IO38 |
| MOSFET blower | IO3 |
| USB | IO19/20 (de trong) |

## 3x DRV8871 + GA12-N20 (12V)

Thay L298N — MOSFET, it nong, bao ve nhiet/dong. **Do footprint that** module Shopee truoc khi fab.

| Truc | Driver | Jack TOP | GPIO |
|------|--------|----------|------|
| 1 | U5 | J5 MOT, J8 MIN, J9 MAX | IO10/11 |
| 2 | U6 | J6, J10, J11 | IO12/13 |
| 3 | U7 | J7, J12, J13 | IO14/15 |

## HMI / phu

- **J15** Buzzer 5V: VCC=+5V, GND, SIG=IO38
- **J16** MOSFET logic-level: SIG=IO3, GND; LOAD tren +12V MOT
- **J17** TFT SPI + touch I2C (cap / FT6336|GT911)

## Opto + BUP + limits

Giu PC817 8ch + BUP-30S + 6 limit NC @12V_SNS (star power). J3 sensor cu **da bo**.

## STAR POWER

Giu: MOT 2.5mm / SNS 0.5mm + R10/C10/C11; bulk 470u tai moi driver.

## Tai tao

```
python gen_power_carrier.py
```

Do module that: ESP32-S3 DevKitC, DRV8871, TFT pinout, MOSFET logic-level.
"""
    out = ROOT / "README.md"
    out.write_text(text, encoding="utf-8")
    return out


'''
    body = replace_between(
        body,
        r"def write_readme\(\) -> Path:",
        r"\ndef write_project\(\) -> Path:",
        readme,
    )

    # Title strings
    body = body.replace(
        "ESP32 Baseboard - Mini560 + TMC + Opto + 3x DRV8871",
        "ESP32-S3 Baseboard - Mini560 + TMC + Opto + 3x DRV8871",
    )
    body = body.replace("J3 sensors", "J17 TFT / J15 buzzer / J16 MOSFET")
    body = body.replace("-> U1 ESP32 VIN", "-> U1 ESP32-S3 5V")

    # Symbol pins for DRV - replace old 8-pin list inside write_symbol_lib
    # After L298N->DRV8871 rename, find pin list with ENA
    old_sym_pins = '''        for num, name, etype, x, y, rot in [
        ("1", "Vs", "power_in", -15.24, 7.62, 0),
        ("2", "GND", "passive", -15.24, 5.08, 0),
        ("3", "5V", "passive", -15.24, 2.54, 0),
        ("5", "IN1", "input", -15.24, -2.54, 0),
        ("6", "IN2", "input", -15.24, -7.62, 0),
        ("7", "OUT1", "passive", 15.24, 5.08, 180),
        ("8", "OUT2", "passive", 15.24, 0.0, 180),
        ("4", "ENA", "input", 15.24, -5.08, 180),
    ]:'''
    # May already be Vs-> something; search more loosely
    if "ENA" in body and "DRV8871_Module_1_1" in body or "DRV8871" in body:
        body = re.sub(
            r'for num, name, etype, x, y, rot in \[\n(?:.*\n)*?.*ENA.*\n\s*\]:',
            '''for num, name, etype, x, y, rot in [
        ("1", "VM", "power_in", -15.24, 5.08, 0),
        ("2", "GND", "passive", -15.24, 2.54, 0),
        ("3", "IN1", "input", -15.24, -2.54, 0),
        ("4", "IN2", "input", -15.24, -5.08, 0),
        ("5", "OUT1", "passive", 15.24, 2.54, 180),
        ("6", "OUT2", "passive", 15.24, -2.54, 180),
    ]:''',
            body,
            count=1,
        )

    # Schematic motor pin positions for 6-pin DRV symbol
    body = body.replace(
        """        vs = (xu - 15.24, yu - 7.62)
        gndp = (xu - 15.24, yu - 5.08)
        # 5V NC at (xu-15.24, yu-2.54)
        in1 = (xu - 15.24, yu + 2.54)
        in2 = (xu - 15.24, yu + 7.62)
        out1 = (xu + 15.24, yu - 5.08)
        out2 = (xu + 15.24, yu - 0.0)
        ena = (xu + 15.24, yu + 5.08)""",
        """        vs = (xu - 15.24, yu - 5.08)
        gndp = (xu - 15.24, yu - 2.54)
        in1 = (xu - 15.24, yu + 2.54)
        in2 = (xu - 15.24, yu + 5.08)
        out1 = (xu + 15.24, yu - 2.54)
        out2 = (xu + 15.24, yu + 2.54)""",
    )

    # Remove J3 sensor block references that break - replace SENSOR_HEADER usage
    body = body.replace("SENSOR_HEADER", "TFT_HEADER")

    # Fix write_pcb docstring / J3 section title - leave J3 footprint as TFT J17 later via post
    # Change J3 reference to J17 in PCB
    body = body.replace('(property "Reference" "J3"', '(property "Reference" "J17"')
    body = body.replace("J3 CAM BIEN", "J17 TFT TOUCH")
    body = body.replace("J3 sensor", "J17 TFT")

    out_text = NEW_HEADER + body
    # Fix double-escaped newlines in drv if any
    out_text = out_text.replace('"\\\\n".join', '"\\n".join')

    # Backup
    bak = GEN.with_suffix(".py.bak_pre_s3")
    if not bak.exists():
        bak.write_text(src, encoding="utf-8")
    GEN.write_text(out_text, encoding="utf-8")
    print(f"Wrote {GEN} (backup {bak})")

    # Cleanup tmp
    for p in ROOT.glob("_tmp_*"):
        p.unlink(missing_ok=True)
    (ROOT / "_drv8871_fp_snippet.py").unlink(missing_ok=True)

    # Compile check
    r = subprocess.run([sys.executable, "-m", "py_compile", str(GEN)], cwd=ROOT)
    if r.returncode != 0:
        print("SYNTAX ERROR — restore backup if needed")
        return
    print("Syntax OK — regenerating board...")
    r = subprocess.run([sys.executable, str(GEN)], cwd=ROOT)
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
