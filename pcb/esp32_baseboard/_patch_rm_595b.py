"""Remove 74HC595 / R4 / field / ENC from gen_power_carrier.py (pass 2)."""
from __future__ import annotations

import re
from pathlib import Path

p = Path(__file__).resolve().parent / "gen_power_carrier.py"
t = p.read_text(encoding="utf-8")

def must_sub(old: str, new: str, label: str) -> None:
    global t
    if old not in t:
        raise SystemExit(f"MISSING: {label}")
    t = t.replace(old, new, 1)
    print("OK", label)

# 1) placement coords
must_sub(
    """    # South: SHIFT east of POWER, then AXIS1→3 — below MCU keepout
    _dip_y = max(mcu_wy1 + MODULE_MCU_CLEAR + 14.0, oy + 132.0)
    if _dip_y + 12.0 > iy1:
        _dip_y = iy1 - 12.0
    u10x, u10y = ox + 78.0, _dip_y
    u11x, u11y = ox + 92.0, _dip_y
    u5x, u5y = ox + 122.0, _dip_y
    u6x, u6y = ox + 156.0, _dip_y
    u7x, u7y = ox + 190.0, _dip_y
""",
    """    # South: AXIS1→3 (HOME+ULN+BYJ) — no 74HC595
    _dip_y = max(mcu_wy1 + MODULE_MCU_CLEAR + 14.0, oy + 132.0)
    if _dip_y + 12.0 > iy1:
        _dip_y = iy1 - 12.0
    u5x, u5y = ox + 100.0, _dip_y
    u6x, u6y = ox + 140.0, _dip_y
    u7x, u7y = ox + 180.0, _dip_y
""",
    "dip placement",
)

# 2) DIP emit
must_sub(
    """    # 74HC595 pin map: Q0=15,Q1=1..Q7=7; QH'=9; /SRCLR=10; SRCLK=11; RCLK=12; /OE=13; SER=14; VCC=16; GND=8
    u10_nets = {
        15: (39, "SR_Q0"), 1: (40, "SR_Q1"), 2: (41, "SR_Q2"), 3: (42, "SR_Q3"),
        4: (43, "SR_Q4"), 5: (44, "SR_Q5"), 6: (45, "SR_Q6"), 7: (63, "SR_Q7"),
        8: (2, "GND"), 9: (38, "QH_U10"), 10: (4, "+3V3"), 11: (35, "SRCLK"),
        12: (36, "RCLK"), 13: (37, "OE_595"), 14: (34, "SER"), 16: (4, "+3V3"),
    }
    u11_nets = {
        15: (64, "SR_Q8"), 1: (65, "SR_Q9"), 2: (66, "SR_Q10"), 3: (67, "SR_Q11"),
        # Q4-Q7 unused on U11
        4: None, 5: None, 6: None, 7: None,
        8: (2, "GND"), 9: None, 10: (4, "+3V3"), 11: (35, "SRCLK"),
        12: (36, "RCLK"), 13: (37, "OE_595"), 14: (38, "QH_U10"), 16: (4, "+3V3"),
    }
    # ULN2003: IN1-4=1-4, GND=8, COM=9, OUT1-4=16,15,14,13; IN5-7/OUT5-7 NC
    def uln_nets(sr_ids, byj_ids):
        # sr_ids = 4 net tuples for IN1-4; byj_ids = 4 for OUT1-4
        d = {
            1: sr_ids[0], 2: sr_ids[1], 3: sr_ids[2], 4: sr_ids[3],
            5: None, 6: None, 7: None,
            8: (2, "GND"), 9: (1, "+12V"),
            10: None, 11: None, 12: None,
            13: byj_ids[3], 14: byj_ids[2], 15: byj_ids[1], 16: byj_ids[0],
        }
        return d

    _emit_dip16("74HC595", "U10", "74HC595", u10x, u10y, u10_nets)
    _emit_dip16("74HC595", "U11", "74HC595", u11x, u11y, u11_nets)
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
""",
    """    # ULN2003: IN1-4 from GPIO; GND=8; COM=9=+12V; OUT1-4 → BYJ
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
            [(34, "BYJ1_IN_A"), (35, "BYJ1_IN_B"), (36, "BYJ1_IN_C"), (37, "BYJ1_IN_D")],
            [(68, "BYJ1_A"), (69, "BYJ1_B"), (70, "BYJ1_C"), (71, "BYJ1_D")],
        ),
    )
    _emit_dip16(
        "ULN2003AN", "U6", "ULN2003AN", u6x, u6y,
        uln_nets(
            [(38, "BYJ2_IN_A"), (39, "BYJ2_IN_B"), (40, "BYJ2_IN_C"), (41, "BYJ2_IN_D")],
            [(72, "BYJ2_A"), (73, "BYJ2_B"), (74, "BYJ2_C"), (75, "BYJ2_D")],
        ),
    )
    _emit_dip16(
        "ULN2003AN", "U7", "ULN2003AN", u7x, u7y,
        uln_nets(
            [(42, "BYJ3_IN_A"), (43, "BYJ3_IN_B"), (44, "BYJ3_IN_C"), (45, "BYJ3_IN_D")],
            [(76, "BYJ3_A"), (77, "BYJ3_B"), (78, "BYJ3_C"), (79, "BYJ3_D")],
        ),
    )
""",
    "ULN emit",
)

# 3) HMI placement without J18
must_sub(
    """    j3x, j3y = ix1 - 23.0, iy0 + 6.0  # TFT LCD; 1×09 span ≤ usable
    j18x, j18y = max(mcu_wx1 + MODULE_MCU_CLEAR + 3.0, j3x - 14.0), iy0 + 10.0
    j15x, j15y = (j18x + j3x) / 2.0, iy0 + 6.0
""",
    """    j3x, j3y = ix1 - 23.0, iy0 + 6.0  # TFT LCD; 1×09 span ≤ usable
    j15x, j15y = j3x - 14.0, iy0 + 6.0  # buzzer west of TFT (no ENC)
""",
    "HMI placement",
)

# 4) touch pads NC (T_CS / T_DO / T_IRQ) — keep T_CLK/T_DIN share SPI
must_sub(
    """    j23_nets = [
        (47, "/TFT_SCK"),   # T_CLK
        (53, "/T_CS"),
        (48, "/TFT_MOSI"),  # T_DIN
        (52, "/TFT_MISO"),  # T_DO
        (20, "/T_IRQ"),
    ]
""",
    """    j23_nets = [
        (47, "/TFT_SCK"),   # T_CLK shares LCD SCK
        None,               # T_CS NC — GPIO reclaimed for BYJ
        (48, "/TFT_MOSI"),  # T_DIN shares LCD MOSI
        None,               # T_DO NC
        None,               # T_IRQ NC
    ]
""",
    "j23 nets",
)

# 5) Remove J18 footprint block
m18 = re.search(
    r"    # --- J18 EC11 encoder — ROT_ENC uncrosses ENC_A/B vs U1 ---\n"
    r".*?"
    r"    gr_text\(\"GND 3V3 A=IO38 B=IO41\".*?\n",
    t,
    re.S,
)
if not m18:
    raise SystemExit("MISSING: J18 footprint block")
t = t[: m18.start()] + "    # J18 ENC removed — GPIOs used for BYJ3\n" + t[m18.end() :]
print("OK J18 PCB remove")

# 6) tft_sigs + ENC routes
must_sub(
    """    # MSP3520 pad index (0-based): CS=2 RST=3 DC=4 MOSI=5 SCK=6 LED=7
    # MISO LCD=8 NC; T_CLK=9 shares SCK; T_CS=10; T_DIN=11 shares MOSI; T_DO=12; T_IRQ=13
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
""",
    """    # MSP3520 pad index (0-based): CS=2 RST=3 DC=4 MOSI=5 SCK=6 LED=7
    # Touch T_CS/T_DO/T_IRQ NC; T_CLK/T_DIN still share SPI via bridges below
    tft_sigs = [
        (50, "IO42", 2),
        (58, "IO46", 3),
        (51, "IO21", 4),
        (48, "IO40", 5),
        (47, "IO39", 6),
        (59, "IO45", 7),
    ]
""",
    "tft_sigs",
)

must_sub(
    """    for i, (ni, gname, pin_i) in enumerate([(62, "IO38", 2), (60, "IO41", 3)]):
        src = pad_world(fx, fy, rot, *pad_local(PIN_BY_NAME[gname]))
        dst = pad_world(j18x, j18y, enc_rot, 0, pin_i * PITCH)
        route_mcu_to_top(ni, src, dst, ox + sx(178.0) + (10 + i) * 1.2, side=-3.0, esc_i=10 + i)
    route_mcu_to_top(4, u1_3v3, j3_3v3, ox + sx(192.0), y_off=-2.0, side=-3.0, esc_i=12)
    route_mcu_to_top(2, u1_gnd_l, j3_gnd, ox + sx(193.5), y_off=2.0, side=-3.0, esc_i=13)
    route_mcu_to_top(2, u1_gnd_l, pad_world(j18x, j18y, enc_rot, 0, 0), ox + sx(193.5), y_off=2.0, side=-3.0, esc_i=13)
    route_mcu_to_top(4, u1_3v3, pad_world(j18x, j18y, enc_rot, 0, PITCH), ox + sx(192.0), y_off=-2.0, side=-3.0, esc_i=12)
""",
    """    route_mcu_to_top(4, u1_3v3, j3_3v3, ox + sx(192.0), y_off=-2.0, side=-3.0, esc_i=12)
    route_mcu_to_top(2, u1_gnd_l, j3_gnd, ox + sx(193.5), y_off=2.0, side=-3.0, esc_i=13)
""",
    "ENC routes remove",
)

# 7) field jacks + R4 emit
m_field = re.search(
    r"    field_jacks = \[.*?"
    r"    gr_text\(\"R4 OE_595 pull-up 10k\".*?\n",
    t,
    re.S,
)
if not m_field:
    raise SystemExit("MISSING: field+R4 block")
t = (
    t[: m_field.start()]
    + "    field_jacks = []  # ESTOP/HOPPER/DOOR/SPARE removed (GPIO → BYJ)\n"
    + "    # R4 OE_595 removed with 74HC595\n"
    + t[m_field.end() :]
)
print("OK field+R4 remove")

# 8) field SNS loop
must_sub(
    """    field_sns_xs = [j[1] for j in field_jacks]
    for di, (px, py) in enumerate(home_limit_pos):
""",
    """    for di, (px, py) in enumerate(home_limit_pos):
""",
    "field_sns header",
)
must_sub(
    """    for di, px in enumerate(field_sns_xs):
        jy_g = LIMIT_Y
        xs = px - 3.0 - (di + 3) * 0.8
        via(xs, y_sns, 46, 0.4, 0.8)
        track_v(xs, y_sns, jy_g, 46, W_SNS)
        via(xs, jy_g, 46, 0.4, 0.8)
        track_h(xs, px, jy_g, 46, W_SNS)
""",
    "",
    "field SNS loop",
)

# 9) C21 placement
must_sub(
    """    # --- Bulk: C20 SE of TMC; C21 with SHIFT (595 COM rail) ---
    bulk_places = [
        ("C20", "CP_Radial_D8_470u_25V", "470u/25V", tx + 12.0, ty + 16.0, "TMC"),
        ("C21", "CP_Radial_D6_100u_25V", "100u/25V", u10x - 12.0, _dip_y + 6.0, "ULN"),
    ]
""",
    """    # --- Bulk: C20 SE of TMC; C21 near AXIS1 ULN COM ---
    bulk_places = [
        ("C20", "CP_Radial_D8_470u_25V", "470u/25V", tx + 12.0, ty + 16.0, "TMC"),
        ("C21", "CP_Radial_D6_100u_25V", "100u/25V", u5x - 14.0, _dip_y + 6.0, "ULN"),
    ]
""",
    "C21 place",
)

# 10) clusters
must_sub(
    """    hmi_boxes = [
        _hdr_aabb(j3x, j3y, TFT_LCD_PINS),
        _hdr_aabb(j23x, j23y, TFT_TP_PINS),
        _hdr_aabb(j18x, j18y, ENC_PINS, enc_rot),
        _hdr_aabb(j15x, j15y, 3),
    ]
    field_boxes = [_hdr_aabb(j[1], LIMIT_Y, 2) for j in field_jacks]
""",
    """    hmi_boxes = [
        _hdr_aabb(j3x, j3y, TFT_LCD_PINS),
        _hdr_aabb(j23x, j23y, TFT_TP_PINS),
        _hdr_aabb(j15x, j15y, 3),
    ]
""",
    "hmi_boxes",
)

must_sub(
    """    c21x, c21y = u10x - 12.0, _dip_y + 6.0
    # SHIFT Eco: 74HC595 + OE pull-up + ULN COM bulk
    shift_boxes = [
        _dip16_aabb(u10x, u10y, dip_rot),
        _dip16_aabb(u11x, u11y, dip_rot),
        _axial_aabb(r4x, r4y, half=3.8, hy=1.8),
        _radial_aabb(c21x, c21y, 3.55, 1.25),
    ]
    # Three adjuster AXIS Ecos (order 1→2→3): endstop jack + ULN + BYJ
    axis_defs = [
        (home_jacks[0], (u5x, u5y), byj_jacks[0], "A1: HOME1+U5+J5"),
        (home_jacks[1], (u6x, u6y), byj_jacks[1], "A2: HOME2+U6+J6"),
        (home_jacks[2], (u7x, u7y), byj_jacks[2], "A3: HOME3+U7+J7"),
    ]
    axis_box_lists = []
    for hj, (ux, uy), bj, _lab in axis_defs:
        axis_box_lists.append([
            _hdr_aabb(hj[1], hj[2], 4),
            _dip16_aabb(ux, uy, dip_rot),
            _hdr_aabb(bj[1], bj[2], 5, byj_rot),
        ])
""",
    """    c21x, c21y = u5x - 14.0, _dip_y + 6.0
    # Three adjuster AXIS Ecos (order 1→2→3): endstop + ULN + BYJ (+ C21 on A1)
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
""",
    "axis clusters",
)

must_sub(
    """    cluster_outline("C: HMI  J17 LCD + J23 TP + J18 ENC + J15 BZ", *_union_aabb(hmi_boxes, pad=0.2), face="F", pad=0)
    cluster_outline("F: FIELD I/O  ESTOP/HOPPER/DOOR/SPARE", *_union_aabb(field_boxes, pad=0.2), face="F", pad=0)
    cluster_outline("U: BUP-30S  J14 + R1 4k7", *_union_aabb(bup_boxes, pad=0.2), face="F", pad=0)
    cluster_outline("B: BLOWER  J16 AOD4184 + R3/D2", *_union_aabb(blower_boxes, pad=0.2), face="F", pad=0)
    cluster_outline("5: SHIFT  U10/U11 595 + R4 + C21", *_union_aabb(shift_boxes, pad=0.2), face="F", pad=0)
""",
    """    cluster_outline("C: HMI  J17 LCD + J23 TP + J15 BZ", *_union_aabb(hmi_boxes, pad=0.2), face="F", pad=0)
    cluster_outline("U: BUP-30S  J14 + R1 4k7", *_union_aabb(bup_boxes, pad=0.2), face="F", pad=0)
    cluster_outline("B: BLOWER  J16 AOD4184 + R3/D2", *_union_aabb(blower_boxes, pad=0.2), face="F", pad=0)
""",
    "cluster outlines",
)

must_sub(
    '    cluster_outline("4: OPTO  U41-U48 PC817 + R2k2/10k", *_union_aabb(opto_boxes, pad=0.2), face="F", pad=0)\n',
    '    cluster_outline("4: OPTO  U41-U44 PC817 + R2k2/10k", *_union_aabb(opto_boxes, pad=0.2), face="F", pad=0)\n',
    "opto cluster label",
)

# 11) schematic embeds / titles / J18 symbol block (text-only + skip J18)
must_sub('            _embed_from_lib("74HC595"),\n', "", "embed 74HC595")
must_sub(
    '        \'\\t\\t(title "ESP32-S3 Baseboard - MP1584 + TMC + ULN2003 + 74HC595")\',\n'
    '        \'\\t\\t(comment 1 "BOTTOM: J1 U2 U3 U4 U5-7 U10/11 U1 | TOP: J2 J4 J5-7 HOME")\',\n',
    '        \'\\t\\t(title "ESP32-S3 Baseboard - MP1584 + TMC + ULN2003 direct GPIO")\',\n'
    '        \'\\t\\t(comment 1 "BOTTOM: J1 U2 U3 U5-7 U1 | TOP: J5-7 HOME TFT")\',\n',
    "sch title",
)
must_sub(
    '        text("TOP: J2 NEMA17 / J17+J23 TFT / J18 ENC / J15 buzzer / J16 MOSFET", 20.32, 120.65, 1.27),\n',
    '        text("TOP: J17+J23 TFT / J15 buzzer / J16 MOSFET (no ENC)", 20.32, 120.65, 1.27),\n',
    "sch top text",
)

# Remove J18 schematic instance
must_sub(
    """        # J18 EC11 encoder (TOP)
        f'\\t(symbol (lib_id "ESP32_Carrier:{ENC_SYM}") (at {j18[0]} {j18[1]} 0) (unit 1)',
        f'\\t\\t(uuid "{j18_uuid}")',
        f'\\t\\t(property "Reference" "J18" (at {j18[0]} {j18[1] - 10.16} 0)',
        "\\t\\t\\t(effects (font (size 1.27 1.27)))",
        "\\t\\t)",
        f'\\t\\t(property "Value" "EC11_ENC" (at {j18[0]} {j18[1] + 10.16} 0)',
        "\\t\\t\\t(effects (font (size 1.27 1.27)))",
        "\\t\\t)",
        f'\\t\\t(property "Footprint" "ESP32_Carrier:{ENC_FP}" (at {j18[0]} {j18[1]} 0)',
        "\\t\\t\\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\\t\\t)",
        f'\\t\\t(property "Datasheet" "~" (at {j18[0]} {j18[1]} 0)',
        "\\t\\t\\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\\t\\t)",
        *[f'\\t\\t(pin "{n}" (uuid "{uid()}"))' for n in range(1, ENC_PINS + 1)],
        "\\t\\t(instances",
        f'\\t\\t\\t(project "esp32_baseboard" (path "/{sch_uuid}" (reference "J18") (unit 1)))',
        "\\t\\t)",
        "\\t)",
""",
    "        # J18 ENC removed from schematic\n",
    "J18 sch remove",
)

# ENC wire labels in sch
m_encw = re.search(
    r"    # EC11: IO38=ENC_A, IO41=ENC_B \(J18\). SW unused\.\n.*?"
    r"    parts \+= wire_path\(j18_pin\(2\).*?\n",
    t,
    re.S,
)
if m_encw:
    t = t[: m_encw.start()] + "    # EC11 removed\n" + t[m_encw.end() :]
    print("OK ENC wires")
else:
    print("WARN ENC wires not found")

must_sub(
    """    parts.append(text("U41-U48 PC817 DIP-4 + 2k2/10k (8ch field)", 210.0, 55.88, 1.27))
""",
    """    parts.append(text("U41-U44 PC817 DIP-4 + 2k2/10k (HOME×3+BUP)", 210.0, 55.88, 1.27))
""",
    "opto sch text",
)

must_sub(
    """    parts.append(text("BOTTOM: U10/U11 74HC595 + U5-U7 ULN2003 | TOP: J5-J7 28BYJ", 20.32, 185.0, 1.27))
    parts.append(text("SER/SRCLK/RCLK/OE = IO10-13; /SRCLR=+3V3; R4 10k OE->+3V3", 20.32, 190.5, 1.0))
    parts.append(text("U10 Q0-3->U5; Q4-7->U6; U11 Q0-3->U7; COM(9)=+12V", 20.32, 195.58, 1.0))
""",
    """    parts.append(text("BOTTOM: U5-U7 ULN2003 GPIO direct | TOP: J5-J7 28BYJ", 20.32, 185.0, 1.27))
    parts.append(text("ULN IN = BYJ*_IN_* from IO (no 74HC595)", 20.32, 190.5, 1.0))
    parts.append(text("U5/U6/U7 COM(9)=+12V; phases → J5-J7", 20.32, 195.58, 1.0))
""",
    "ULN sch notes",
)

# README BOM inside generator
must_sub(
    "# ESP32-S3 Baseboard — BOM (ULN2003 + 74HC595)",
    "# ESP32-S3 Baseboard — BOM (ULN2003 direct GPIO)",
    "readme title",
)
must_sub(
    "| U10/U11 | **74HC595** DIP-16 | Shift chain (12 phases) |\n| R4 | 10k axial | `/OE` pull-up → +3V3 |\n",
    "",
    "readme 595 rows",
)
must_sub(
    "| SER / SRCLK / RCLK / OE_595 | IO10–13 |\n",
    "| BYJ1–3 ULN IN | IO10–13, IO7/8/14/15, IO38/41/6/48 |\n",
    "readme gpio row",
)
must_sub(
    "| U41–U48 | PC817 DIP-4 ×8 | HOME1-3 + BUP + ESTOP/HOPPER/DOOR/SPARE |\n",
    "| U41–U44 | PC817 DIP-4 ×4 | HOME1-3 + BUP |\n",
    "readme opto",
)
must_sub(
    "| J15–J18 | — | Buzzer / AOD4184 / **TFT 1×14** / ENC |\n",
    "| J15–J17/J23 | — | Buzzer / TFT LCD+TP / (no ENC) |\n",
    "readme jacks",
)

# main footprint write
must_sub("        write_74hc595_footprint(),\n", "", "main write 595")

# comments / docstring
must_sub(
    "       J17+J23 TFT, J18 EC11, J19-J22 field. (J2 removed — Mot on TMC module.)",
    "       J17+J23 TFT, J15 buzzer. (No 74HC595 / ENC / field jacks.)",
    "module docstring",
)
must_sub(
    "# EC11 on J18: GPIO38=ENC_A, GPIO41=ENC_B (SW unused — Enter on TFT).\n",
    "# ENC removed — IO38/41 used for BYJ3.\n",
    "ENC header comment",
)
must_sub(
    "    # S: SHIFT(595) + A1→A3 (HOME+ULN+BYJ)\n",
    "    # S: A1→A3 (HOME+ULN+BYJ)\n",
    "layout comment",
)
must_sub(
    "    # --- DIP-16: U10/U11 SHIFT + U5-U7 ULN; BYJ J5-J7; HOME endstop J8/J10/J12 ---\n",
    "    # --- DIP-16: U5-U7 ULN; BYJ J5-J7; HOME endstop J8/J10/J12 ---\n",
    "dip section comment",
)

# Move BUP west (field gone)
must_sub(
    "    # FIELD NW; BUP east of FIELD (gap)\n    j14x, j14y = ix0 + 42.0, iy0 + 4.0\n",
    "    # BUP NW (field jacks removed)\n    j14x, j14y = ix0 + 8.0, iy0 + 4.0\n",
    "j14 place",
)

p.write_text(t, encoding="utf-8")
print("WROTE", p)
# sanity
for bad in ("u10x", "u11x", "r4x", "j18x", '"OE_595"', "SR_Q0", "_emit_dip16(\"74HC595"):
    if bad in t and bad not in ("# R4 OE_595 removed with 74HC595",):
        # allow comments mentioning removed parts
        hits = [ln for ln in t.splitlines() if bad in ln and not ln.strip().startswith("#")]
        # filter symbol lib still defining 74HC595 is ok for now
        hits = [h for h in hits if "symbol \"74HC595" not in h and "write_74hc595" not in h and "74HC595 DIP" not in h]
        if hits and bad not in ("write_74hc595",):
            print("REMAIN", bad, "count", len(hits))
            for h in hits[:8]:
                print(" ", h[:120])
