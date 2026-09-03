#!/usr/bin/env python3
"""Apply JST-XH field I/O + split J31A/J31B into gen_power_carrier + related files.

Run once from pcb/esp32_baseboard. Idempotent markers: XH_FIELD_IO_V1
"""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parent
P = ROOT / "gen_power_carrier.py"
text = P.read_text(encoding="utf-8")
if "XH_FIELD_IO_V1" in text:
    print("already patched gen_power_carrier")
else:
    # Mark + replace endstop / J31 constants block
    old = '''# J31 = 1×11 @2.54 + shroud/key silk — use KF2510 keyed housing
XH_PITCH = 2.5  # JST-XH
POWER_PROT_FP = "JST_XH_04_Socket"
POWER_PROT_PINS = 4
POWER_PROT_HEADER = [("1", "RAW"), ("2", "GND"), ("3", "+12V"), ("4", "GND")]
POWER_PROT_SYM = "Conn_JST_XH_04"
OPTO4_FP = "PinHeader_1x11_Opto4"
OPTO4_PINS = 11
OPTO4_HEADER = [
    ("1", "IN1"), ("2", "IN2"), ("3", "IN3"), ("4", "IN4"),
    ("5", "SNS"), ("6", "GND"),
    ("7", "OUT1"), ("8", "OUT2"), ("9", "OUT3"), ("10", "OUT4"),
    ("11", "3V3"),
]
OPTO4_SYM = "Conn_1x11_Opto4"'''
    new = '''# XH_FIELD_IO_V1 — all field I/O + M1/M2 on JST-XH keyed (pitch 2.5)
XH_PITCH = 2.5  # JST-XH
POWER_PROT_FP = "JST_XH_04_Socket"
POWER_PROT_PINS = 4
POWER_PROT_HEADER = [("1", "RAW"), ("2", "GND"), ("3", "+12V"), ("4", "GND")]
POWER_PROT_SYM = "Conn_JST_XH_04"
# M2 split: cannot reverse; different counts from J30
OPTO_IN_FP = "JST_XH_06_Socket"
OPTO_IN_PINS = 6
OPTO_IN_HEADER = [
    ("1", "IN1"), ("2", "IN2"), ("3", "IN3"), ("4", "IN4"),
    ("5", "SNS"), ("6", "GND"),
]
OPTO_OUT_FP = "JST_XH_05_Socket"
OPTO_OUT_PINS = 5
OPTO_OUT_HEADER = [
    ("1", "OUT1"), ("2", "OUT2"), ("3", "OUT3"), ("4", "OUT4"), ("5", "3V3"),
]
# Legacy names for any leftover references
OPTO4_FP = OPTO_IN_FP
OPTO4_PINS = OPTO_IN_PINS
OPTO4_HEADER = OPTO_IN_HEADER
OPTO4_SYM = "Conn_JST_XH_06"
HOME_FP = "JST_XH_02_Socket"
HOME_PINS = 2
HOME_HEADER = [("1", "SIG"), ("2", "SNS")]  # dry NC → opto
BUP_FP = "JST_XH_04_Socket"
BUP_HEADER = [("1", "+12V"), ("2", "GND"), ("3", "OUT"), ("4", "CTRL")]
BZ_FP = "JST_XH_03_Socket"
BZ_HEADER = [("1", "VCC5"), ("2", "GND"), ("3", "SIG")]
BLW_FP = "JST_XH_04_Socket"
BLW_HEADER = [("1", "PWM"), ("2", "GND"), ("3", "+12V"), ("4", "FAN-")]
ENC_XH_FP = "JST_XH_04_Socket"
ENC_XH_HEADER = [("1", "GND"), ("2", "3V3"), ("3", "ENC_A"), ("4", "ENC_B")]'''
    if old not in text:
        raise SystemExit("constants block not found")
    text = text.replace(old, new)

    old_es = '''ENDSTOP_FP = "PinHeader_1x04_Endstop"
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
)'''
    new_es = '''ENDSTOP_FP = HOME_FP
ENDSTOP_SYM = "Conn_JST_XH_02"
ENDSTOP_HEADER = HOME_HEADER
ENDSTOP_SHOPEE = (
    "Limit switch dry NC + JST-XH 2P (SIG/SNS) — no CNC 4-pin module required"
)'''
    if old_es not in text:
        raise SystemExit("endstop block not found")
    text = text.replace(old_es, new_es)

    # Generalize write_jst_xh_04_socket into write_jst_xh_socket(n,...)
    # Keep write_jst_xh_04_socket as wrapper; add generic after it.
    marker = "def write_jst_xh_04_socket() -> Path:"
    if "def write_jst_xh_socket(" not in text:
        insert = '''
def write_jst_xh_socket(n_pins: int, fp_name: str, pin_names: list[str], title: str) -> Path:
    """JST-XH nP female — polarized shroud, pitch 2.5 mm."""
    pitch = XH_PITCH
    span = (n_pins - 1) * pitch
    lines: list[str] = []
    a = lines.append
    a(f'(footprint "{fp_name}"')
    a("\\t(version 20260206)")
    a('\\t(generator "gen_power_carrier.py")')
    a('\\t(layer "F.Cu")')
    a(f'\\t(descr "JST-XH {n_pins}P female keyed — {title}")')
    a('\\t(tags "JST XH keyed polarized anti-reverse")')
    a('\\t(property "Reference" "J**"')
    a(f"\\t\\t(at 0 {{-2.8}} 0)")
    a('\\t\\t(layer "F.SilkS")')
    a("\\t\\t(effects (font (size 1 1) (thickness 0.15)))")
    a("\\t)")
    a(f'\\t(property "Value" "{fp_name}"')
    a(f"\\t\\t(at 0 {{span + 2.8}} 0)")
    a('\\t\\t(layer "F.Fab")')
    a("\\t\\t(effects (font (size 0.8 0.8) (thickness 0.12)))")
    a("\\t)")
    a("\\t(attr through_hole)")
    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
        a("\\t(fp_rect")
        a(f"\\t\\t(start -3.2 {{-2.0}})")
        a(f"\\t\\t(end 3.2 {{span + 2.0}})")
        a(f"\\t\\t(stroke (width {{w}}) (type solid))")
        a("\\t\\t(fill none)")
        a(f'\\t\\t(layer "{{layer}}")')
        a("\\t)")
    a("\\t(fp_line")
    a("\\t\\t(start -3.2 -0.6)")
    a("\\t\\t(end -4.2 0)")
    a("\\t\\t(stroke (width 0.15) (type solid))")
    a('\\t\\t(layer "F.SilkS")')
    a("\\t)")
    a("\\t(fp_line")
    a("\\t\\t(start -4.2 0)")
    a("\\t\\t(end -3.2 0.6)")
    a("\\t\\t(stroke (width 0.15) (type solid))")
    a('\\t\\t(layer "F.SilkS")')
    a("\\t)")
    a('\\t(fp_text user "KEY"')
    a("\\t\\t(at -5.2 0 0)")
    a('\\t\\t(layer "F.SilkS")')
    a('\\t\\t(effects (font (size 0.7 0.7) (thickness 0.1)))')
    a("\\t)")
    for i, name in enumerate(pin_names):
        y = i * pitch
        a(f'\\t(fp_text user "{{name}}"')
        a(f"\\t\\t(at 4.2 {{y}} 0)")
        a('\\t\\t(layer "F.SilkS")')
        a('\\t\\t(effects (font (size 0.65 0.65) (thickness 0.1)) (justify left))')
        a("\\t)")
        shape = "rect" if i == 0 else "circle"
        a(f'\\t(pad "{{i + 1}}" thru_hole {{shape}}')
        a(f"\\t\\t(at 0 {{y}})")
        a("\\t\\t(size 1.6 1.6)")
        a("\\t\\t(drill 0.9)")
        a('\\t\\t(layers "*.Cu" "*.Mask")')
        a("\\t)")
    a(")")
    out = PRETTY / f"{{fp_name}}.kicad_mod"
    out.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
    return out


def write_jst_xh_04_socket() -> Path:
'''
        # Fix escaping - write properly without double escapes mess
        pass  # will write file differently

    P.write_text(text, encoding="utf-8")
    print("partial constants OK", P)
