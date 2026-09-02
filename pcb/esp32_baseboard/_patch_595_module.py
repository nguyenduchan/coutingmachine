#!/usr/bin/env python3
"""Patch gen_power_carrier.py: replace DIP U10/U11 with Shopee 74HC595-24IO module east of ESP32."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
P = ROOT / "gen_power_carrier.py"
text = P.read_text(encoding="utf-8")

text = text.replace(
    "ULN via 2x 74HC595 DIP.",
    "ULN via Shopee 74HC595-24IO module (3x595) east of ESP32.",
)

text = text.replace(
    '        38: "QH_U10",\n        39: "SR_Q0",',
    '        39: "SR_Q0",',
)

text = text.replace(
    'parts.append(text("BOTTOM: U10/U11 74HC595 DIP + U5-U7 ULN | TOP: J5-J7 28BYJ", 20.32, 185.0, 1.27))\n'
    '    parts.append(text("SER/SRCLK/RCLK/OE=IO10-13; buy DIP IC not LED-bar module; R4 OE PU", 20.32, 190.5, 1.0))\n'
    '    parts.append(text("U10 Q0-3->U5; Q4-7->U6; U11 Q0-3->U7; COM=+12V", 20.32, 195.58, 1.0))',
    'parts.append(text("U10=74HC595-24IO module (Shopee) RIGHT of ESP32; U5-U7 ULN; J5-J7 BYJ", 20.32, 185.0, 1.27))\n'
    '    parts.append(text("CTRL LDEN/GND/VCC/LDSI/LDSTR/LDSCK = OE/GND/3V3/SER/RCLK/SRCLK; R4 LDEN PU", 20.32, 190.5, 1.0))\n'
    '    parts.append(text("1_Q0-3->U5; 1_Q4-7->U6; 2_Q0-3->U7; shift 3 bytes; COM=+12V", 20.32, 195.58, 1.0))',
)

old_start = "    # South: SHIFT (2x 74HC595 DIP) then AXIS1→3 (ULN COM = +12V)"
old_end = '    gr_text("R4 OE_595 pull-up 10k", r4x - 6, r4y + 4.5, "Cmts.User", 0.6)\n'
si = text.find(old_start)
ei = text.find(old_end)
if si < 0 or ei < 0 or ei <= si:
    raise SystemExit(f"SHIFT block markers not found {si=} {ei=}")
ei = ei + len(old_end)

new_block = r'''    # South: AXIS1→3 (ULN). SHIFT module U10 = 74HC595-24IO east of ESP32.
    _dip_y = max(mcu_wy1 + MODULE_MCU_CLEAR + 14.0, oy + 132.0)
    if _dip_y + 12.0 > iy1:
        _dip_y = iy1 - 12.0
    # Reclaim former DIP zone — pack AXIS toward POWER
    u5x, u5y = ox + 88.0, _dip_y
    u6x, u6y = ox + 123.0, _dip_y
    u7x, u7y = ox + 158.0, _dip_y

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
    MOD_CTRL_TO_Q = 17.0
    u10_ctrl_x = mcu_wx1 + MODULE_MCU_CLEAR + 3.0
    u10_q_x = u10_ctrl_x + MOD_CTRL_TO_Q
    u10_y0 = mcu_wy0 + 12.0
    if u10_y0 + 23 * PITCH + 2.0 > _dip_y - 10.0:
        u10_y0 = max(mcu_wy0 + 8.0, _dip_y - 10.0 - 23 * PITCH)
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

    r4x, r4y = u10_ctrl_x - 8.0, u10_y0 + 1.5 * PITCH
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
'''

text = text[:si] + new_block + text[ei:]

text = text.replace(
    '("C21", "CP_Radial_D6_100u_25V", "100u/25V", (u10x + u11x) / 2.0 + 4.0, _dip_y - 14.0, "ULN"),',
    '("C21", "CP_Radial_D6_100u_25V", "100u/25V", u5x - 14.0, _dip_y - 2.0, "ULN"),',
)

old_shift = """    c21x, c21y = (u10x + u11x) / 2.0 + 4.0, _dip_y - 14.0
    shift_boxes = [
        _dip16_aabb(u10x, u10y, dip_rot),
        _dip16_aabb(u11x, u11y, dip_rot),
        _axial_aabb(r4x, r4y, half=3.8, hy=1.8),
        _radial_aabb(c21x, c21y, 3.55, 1.25),
    ]"""
new_shift = """    c21x, c21y = u5x - 14.0, _dip_y - 2.0
    shift_boxes = [
        _hdr_aabb(u10_ctrl_x, u10_y0, 6),
        _hdr_aabb(u10_q_x, u10_y0, 24),
        _axial_aabb(r4x, r4y, half=3.8, hy=1.8),
        (mod_x0, mod_y0, mod_x1, mod_y1),
    ]"""
if old_shift not in text:
    raise SystemExit("shift_boxes block not found")
text = text.replace(old_shift, new_shift)

text = text.replace(
    'cluster_outline("5: SHIFT  U10/U11 595 DIP + R4 + C21", *_union_aabb(shift_boxes, pad=0.2), face="F", pad=0)',
    'cluster_outline("5: SHIFT  U10 595-24IO + J24/J25 + R4", *_union_aabb(shift_boxes, pad=0.2), face="F", pad=0)',
)

text = text.replace(
    "# ESP32-S3 Baseboard — BOM (ULN2003 + 74HC595 DIP)",
    "# ESP32-S3 Baseboard — BOM (ULN2003 + 74HC595-24IO module)",
)
text = text.replace(
    "| U10/U11 | **74HC595 DIP-16** | Shift → ULN (12 pha). **IC DIP**, không LED-thanh |\n"
    "| R4 | 10k axial | `/OE` pull-up → +3V3 |",
    "| **U10** | **74HC595-24IO module** (3×595) | [Shopee](https://shopee.vn/-C%C3%B3-s%E1%BA%B5n-M%E1%BA%A1ch-m%E1%BB%9F-r%E1%BB%99ng-I-O-24-ch%C3%A2n-74HC595-thegioimodule-i.951399259.42633627766) — **bên phải ESP32** |\n"
    "| J24 / J25 | Header cái 1×6 + 1×24 | CTRL + Q (cắm module) |\n"
    "| R4 | 10k axial | LDEN/`OE` pull-up → +3V3 |",
)

needle = '        write_pin_header_footprint(5, BYJ_FP, [p[1] for p in BYJ_HEADER]),'
insert = (
    '        write_pin_header_footprint(5, BYJ_FP, [p[1] for p in BYJ_HEADER]),\n'
    '        write_pin_header_footprint(6, "PinHeader_1x06_595CTRL",\n'
    '                                  ["LDEN", "GND", "VCC", "LDSI", "LDSTR", "LDSCK"]),\n'
    '        write_pin_header_footprint(24, "PinHeader_1x24_595Q",\n'
    '                                  [f"{i//8+1}_Q{i%8}" for i in range(24)]),'
)
if needle not in text:
    raise SystemExit("BYJ write_pin_header not found")
if "PinHeader_1x06_595CTRL" not in text.split("write_pin_header_footprint(6")[0][-80:]:
    # only insert once
    if 'PinHeader_1x06_595CTRL"' not in text[text.find("def main"):] if "def main" in text else True:
        pass
if text.count("PinHeader_1x06_595CTRL") == 0 or "write_pin_header_footprint(6, \"PinHeader_1x06_595CTRL\"" not in text:
    text = text.replace(needle, insert, 1)

P.write_text(text, encoding="utf-8")
print("WROTE", P)
print("OK _emit_dip16", "def _emit_dip16" in text)
print("_hdr_1xn defs", text.count("def _hdr_1xn"))
