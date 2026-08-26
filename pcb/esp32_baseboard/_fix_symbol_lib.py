#!/usr/bin/env python3
"""Restore write_symbol_lib from pre-S3 backup and apply S3/DRV8871 patches."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CUR = ROOT / "gen_power_carrier.py"
BAK = ROOT / "gen_power_carrier.py.bak_pre_s3"

NEW_DRV = r'''
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

'''


def main() -> None:
    cur = CUR.read_text(encoding="utf-8")
    bak = BAK.read_text(encoding="utf-8")
    m = re.search(
        r"\ndef write_symbol_lib\(\) -> Path:.*?\n(?=def write_lib_tables)",
        bak,
        re.S,
    )
    if not m:
        raise SystemExit("backup write_symbol_lib not found")
    sym = m.group(0)
    sym = sym.replace(
        "pin_ys = [17.78 - i * 2.54 for i in range(15)]",
        "pin_ys = [26.67 - i * 2.54 for i in range(S3_PINS_PER_SIDE)]",
    )
    sym = sym.replace("ESP32_DevKit_V1_30Pin_Socket", "ESP32_S3_DevKitC_44Pin_Socket")
    sym = sym.replace("ESP32_DevKit_V1_30Pin", "ESP32_S3_DevKitC_1")
    sym = sym.replace(
        "ESP32 DevKit V1 30-pin socket", "ESP32-S3-DevKitC-1 44-pin socket"
    )
    i0 = sym.find("    # --- L298N (channel A) ---")
    i1 = sym.find("    a('\\t(symbol \"Conn_1x02_MotorDC\"")
    if i0 < 0 or i1 < 0:
        raise SystemExit(f"L298N markers missing {i0} {i1}")
    sym = sym[:i0] + NEW_DRV + "\n" + sym[i1:]
    sym = sym.replace(
        "TOP: sensors (GND 3V3 IO32-35)",
        "LEGACY J3 unused; use J17 TFT header",
    )

    m2 = re.search(
        r"\ndef write_symbol_lib\(\) -> Path:.*?\n(?=def write_lib_tables)",
        cur,
        re.S,
    )
    if not m2:
        raise SystemExit("current write_symbol_lib not found")
    out = cur[: m2.start()] + "\n" + sym.lstrip("\n") + "\n" + cur[m2.end() :]
    CUR.write_text(out, encoding="utf-8")
    print("OK restored write_symbol_lib")


if __name__ == "__main__":
    main()
