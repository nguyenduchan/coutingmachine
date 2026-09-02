"""Restore 74HC595 chain for ULN2003 in gen_power_carrier.py."""
from __future__ import annotations

import re
from pathlib import Path

p = Path(__file__).resolve().parent / "gen_power_carrier.py"
t = p.read_text(encoding="utf-8")

def must(old: str, new: str, label: str) -> None:
    global t
    if old not in t:
        raise SystemExit(f"MISSING: {label}")
    t = t.replace(old, new, 1)
    print("OK", label)

must(
    """from s3_pinmap import (
    BUZZER_GPIO,
    DRV_MOTORS,
    ENC_GPIO,
    LEFT_PINS,
    MOSFET_GPIO,
    OPTO_GPIO,
    PIN_BY_NAME,
    RIGHT_PINS,
    BYJ_GPIO,
    TFT_GPIO,
    TMC_GPIO,
    pad_local,
)
""",
    """from s3_pinmap import (
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
""",
    "imports",
)

must(
    "       J17+J23 TFT, J18 EC11, J15 buzzer. (No 74HC595 / field jacks.)",
    "       J17+J23 TFT+touch, J18 EC11, J15 buzzer. ULN via 2x 74HC595 DIP.",
    "docstring",
)

must(
    """        # GPIO → ULN2003 IN (direct; was 74HC595 Q)
        34: "BYJ1_IN_A",
        35: "BYJ1_IN_B",
        36: "BYJ1_IN_C",
        37: "BYJ1_IN_D",
        38: "BYJ2_IN_A",
        39: "BYJ2_IN_B",
        40: "BYJ2_IN_C",
        41: "BYJ2_IN_D",
        42: "BYJ3_IN_A",
        43: "BYJ3_IN_B",
        44: "BYJ3_IN_C",
        45: "BYJ3_IN_D",
""",
    """        # 74HC595 control + Q outputs → ULN IN
        34: "SER",
        35: "SRCLK",
        36: "RCLK",
        37: "OE_595",
        38: "QH_U10",
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
""",
    "nets shift",
)

must(
    """        58: "/TFT_RST",
        60: "/ENC_B",
        61: "/BLW_RET",
        62: "/ENC_A",
    }
""",
    """        52: "/TFT_MISO",
        53: "/T_CS",
        20: "/T_IRQ",
        58: "/TFT_RST",
        59: "/TFT_BL",
        60: "/ENC_B",
        61: "/BLW_RET",
        62: "/ENC_A",
    }
""",
    "nets tft/enc",
)

must(
    """            "IO9": (54, "/BUZZER"),
            "IO10": (34, "BYJ1_IN_A"),
            "IO11": (35, "BYJ1_IN_B"),
            "IO12": (36, "BYJ1_IN_C"),
            "IO13": (37, "BYJ1_IN_D"),
            "IO7": (38, "BYJ2_IN_A"),
            "IO8": (39, "BYJ2_IN_B"),
            "IO14": (40, "BYJ2_IN_C"),
            "IO15": (41, "BYJ2_IN_D"),
            "IO38": (42, "BYJ3_IN_A"),
            "IO41": (43, "BYJ3_IN_B"),
            "IO6": (44, "BYJ3_IN_C"),
            "IO48": (45, "BYJ3_IN_D"),
            "IO39": (47, "/TFT_SCK"),
            "IO40": (48, "/TFT_MOSI"),
            "IO42": (50, "/TFT_CS"),
            "IO21": (51, "/TFT_DC"),
            "IO3": (55, "/BLOWER"),
            "IO46": (58, "/TFT_RST"),
            "IO47": (62, "/ENC_A"),
            "IO45": (60, "/ENC_B"),
            # TFT_BL hardwired +3V3 on J17.8
        }
""",
    """            "IO9": (54, "/BUZZER"),
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
""",
    "esp_net",
)

must(
    """    j17_nets = [
        (4, "+3V3"),
        (2, "GND"),
        (50, "/TFT_CS"),
        (58, "/TFT_RST"),
        (51, "/TFT_DC"),
        (48, "/TFT_MOSI"),
        (47, "/TFT_SCK"),
        (4, "+3V3"),  # LED/BL hardwired on (frees IO45 for ENC)
        None,  # LCD SDO NC
    ]
    j23_nets = [
        (47, "/TFT_SCK"),   # T_CLK shares LCD SCK
        None,               # T_CS NC — GPIO reclaimed for BYJ
        (48, "/TFT_MOSI"),  # T_DIN shares LCD MOSI
        None,               # T_DO NC
        None,               # T_IRQ NC
    ]
""",
    """    j17_nets = [
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
""",
    "j17/j23 nets",
)

must(
    '    gr_text("GND 3V3 A=IO47 B=IO45", j18x - 6, j18y - 3.8, "F.SilkS", 0.55)\n',
    '    gr_text("GND 3V3 A=IO38 B=IO41", j18x - 6, j18y - 3.8, "F.SilkS", 0.55)\n',
    "J18 silk",
)

must(
    """    # MSP3520 pad index (0-based): CS=2 RST=3 DC=4 MOSI=5 SCK=6 LED=7
    # Touch T_CS/T_DO/T_IRQ NC; T_CLK/T_DIN still share SPI via bridges below
    tft_sigs = [
        (50, "IO42", 2),
        (58, "IO46", 3),
        (51, "IO21", 4),
        (48, "IO40", 5),
        (47, "IO39", 6),
        # pin7 LED = +3V3 hardwired (no GPIO)
    ]
    # Trunks in east corridor; side-enter each jack pin
    for i, (ni, gname, pin_i) in enumerate(tft_sigs):
        src = pad_world(fx, fy, rot, *pad_local(PIN_BY_NAME[gname]))
        dst = (j3x, j3y + pin_i * PITCH)
        route_mcu_to_top(ni, src, dst, ox + sx(178.0) + i * 1.2, side=-3.0, esc_i=i)
    # Side-bridge shared SPI (avoid shorting through mid pads on the column)
    def _tft_bridge(net_i: int, ya: float, yb: float):
        x_b = j3x - 2.2
        track_h(j3x, x_b, ya, net_i, 0.25)
        track_v(x_b, ya, yb, net_i, 0.25)
        track_h(x_b, j3x, yb, net_i, 0.25)

    _tft_bridge(47, j3y + 6 * PITCH, j3y + 9 * PITCH)
    _tft_bridge(48, j3y + 5 * PITCH, j3y + 11 * PITCH)
    # LED pin → +3V3 (same net as J17.1)
    j3_led = (j3x, j3y + 7 * PITCH)
    route_mcu_to_top(4, u1_3v3, j3_led, ox + sx(191.0), y_off=-1.0, side=-3.0, esc_i=7)
    bz = pad_world(fx, fy, rot, *pad_local(PIN_BY_NAME["IO9"]))
    route_mcu_to_top(54, bz, (j15x, j15y + 2 * PITCH), ox + sx(178.0) + 8 * 1.2, side=-3.0, esc_i=8)
    bl = pad_world(fx, fy, rot, *pad_local(PIN_BY_NAME["IO3"]))
    route_mcu_to_top(55, bl, (j16x, j16y), ox + sx(178.0) + 9 * 1.2, side=-3.0, esc_i=9)
    for i, (ni, gname, pin_i) in enumerate([(62, "IO47", 2), (60, "IO45", 3)]):
        src = pad_world(fx, fy, rot, *pad_local(PIN_BY_NAME[gname]))
        dst = pad_world(j18x, j18y, enc_rot, 0, pin_i * PITCH)
        route_mcu_to_top(ni, src, dst, ox + sx(178.0) + (10 + i) * 1.2, side=-3.0, esc_i=10 + i)
""",
    """    # MSP3520: CS=2 RST=3 DC=4 MOSI=5 SCK=6 LED=7; touch CS=10 DO=12 IRQ=13
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
""",
    "tft/enc routes",
)

must(
    """    # South: AXIS1→3 packed west toward POWER (ULN COM = +12V)
    _dip_y = max(mcu_wy1 + MODULE_MCU_CLEAR + 14.0, oy + 132.0)
    if _dip_y + 12.0 > iy1:
        _dip_y = iy1 - 12.0
    u5x, u5y = ox + 75.0, _dip_y
    u6x, u6y = ox + 115.0, _dip_y
    u7x, u7y = ox + 155.0, _dip_y

    # ULN2003: IN1-4 from GPIO; GND=8; COM=9=+12V; OUT1-4 → BYJ
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
    """    # South: SHIFT (2x 74HC595 DIP) then AXIS1→3 (ULN COM = +12V)
    _dip_y = max(mcu_wy1 + MODULE_MCU_CLEAR + 14.0, oy + 132.0)
    if _dip_y + 12.0 > iy1:
        _dip_y = iy1 - 12.0
    u10x, u10y = ox + 52.0, _dip_y
    u11x, u11y = ox + 66.0, _dip_y
    u5x, u5y = ox + 100.0, _dip_y
    u6x, u6y = ox + 135.0, _dip_y
    u7x, u7y = ox + 170.0, _dip_y

    # 74HC595: Q0=15,Q1=1..Q7=7; QH'=9; /SRCLR=10; SRCLK=11; RCLK=12; /OE=13; SER=14
    u10_nets = {
        15: (39, "SR_Q0"), 1: (40, "SR_Q1"), 2: (41, "SR_Q2"), 3: (42, "SR_Q3"),
        4: (43, "SR_Q4"), 5: (44, "SR_Q5"), 6: (45, "SR_Q6"), 7: (63, "SR_Q7"),
        8: (2, "GND"), 9: (38, "QH_U10"), 10: (4, "+3V3"), 11: (35, "SRCLK"),
        12: (36, "RCLK"), 13: (37, "OE_595"), 14: (34, "SER"), 16: (4, "+3V3"),
    }
    u11_nets = {
        15: (64, "SR_Q8"), 1: (65, "SR_Q9"), 2: (66, "SR_Q10"), 3: (67, "SR_Q11"),
        4: None, 5: None, 6: None, 7: None,
        8: (2, "GND"), 9: None, 10: (4, "+3V3"), 11: (35, "SRCLK"),
        12: (36, "RCLK"), 13: (37, "OE_595"), 14: (38, "QH_U10"), 16: (4, "+3V3"),
    }

    def uln_nets(in_ids, byj_ids):
        d = {
            1: in_ids[0], 2: in_ids[1], 3: in_ids[2], 4: in_ids[3],
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
    "DIP 595+ULN",
)

# R4 after field_jacks empty
must(
    "    field_jacks = []  # ESTOP/HOPPER/DOOR/SPARE removed (GPIO → BYJ)\n"
    "    # R4 OE_595 removed with 74HC595\n",
    """    field_jacks = []  # field optional — spare GPIO 7/8/14/15

    # R4 OE_595 pull-up 10k (boot Hi-Z) west of U10
    r4x, r4y = u10x - 12.0, _dip_y - 4.0
    a('\\t(footprint "ESP32_Carrier:R_Axial_4k7_BUP"')
    a('\\t\\t(layer "F.Cu")')
    a(f'\\t\\t(uuid "{uid()}")')
    a(f"\\t\\t(at {r4x} {r4y})")
    a('\\t\\t(property "Reference" "R4"')
    a("\\t\\t\\t(at 0 -2.8 0)")
    a('\\t\\t\\t(layer "F.SilkS")')
    a("\\t\\t\\t(effects (font (size 0.8 0.8) (thickness 0.12)))")
    a(f'\\t\\t\\t(uuid "{uid()}")')
    a("\\t\\t)")
    a('\\t\\t(property "Value" "10k"')
    a("\\t\\t\\t(at 0 2.6 0)")
    a('\\t\\t\\t(layer "F.SilkS")')
    a("\\t\\t\\t(effects (font (size 0.75 0.75) (thickness 0.1)))")
    a(f'\\t\\t\\t(uuid "{uid()}")')
    a("\\t\\t)")
    a("\\t\\t(attr through_hole)")
    fp_silk_rect(-3.2, -1.5, 3.2, 1.5, "F.SilkS")
    a('\\t\\t(pad "1" thru_hole rect')
    a("\\t\\t\\t(at -3.75 0)")
    a("\\t\\t\\t(size 1.6 1.6)")
    a("\\t\\t\\t(drill 0.8)")
    a('\\t\\t\\t(layers "*.Cu" "*.Mask")')
    a('\\t\\t\\t(net 37 "OE_595")')
    a(f'\\t\\t\\t(uuid "{uid()}")')
    a("\\t\\t)")
    a('\\t\\t(pad "2" thru_hole circle')
    a("\\t\\t\\t(at 3.75 0)")
    a("\\t\\t\\t(size 1.6 1.6)")
    a("\\t\\t\\t(drill 0.8)")
    a('\\t\\t\\t(layers "*.Cu" "*.Mask")')
    a('\\t\\t\\t(net 4 "+3V3")')
    a(f'\\t\\t\\t(uuid "{uid()}")')
    a("\\t\\t)")
    a("\\t)")
    gr_text("R4 OE_595 pull-up 10k", r4x - 6, r4y + 4.5, "Cmts.User", 0.6)

""",
    "R4 emit",
)

must(
    '("C21", "CP_Radial_D6_100u_25V", "100u/25V", u5x - 14.0, _dip_y + 6.0, "ULN"),',
    '("C21", "CP_Radial_D6_100u_25V", "100u/25V", u10x - 12.0, _dip_y + 6.0, "ULN"),',
    "C21 place",
)

must(
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
    """    c21x, c21y = u10x - 12.0, _dip_y + 6.0
    shift_boxes = [
        _dip16_aabb(u10x, u10y, dip_rot),
        _dip16_aabb(u11x, u11y, dip_rot),
        _axial_aabb(r4x, r4y, half=3.8, hy=1.8),
        _radial_aabb(c21x, c21y, 3.55, 1.25),
    ]
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
    "clusters shift+axis",
)

must(
    '    cluster_outline("C: HMI  J17 LCD + J23 TP + J18 ENC + J15 BZ", *_union_aabb(hmi_boxes, pad=0.2), face="F", pad=0)\n'
    '    cluster_outline("U: BUP-30S  J14 + R1 4k7", *_union_aabb(bup_boxes, pad=0.2), face="F", pad=0)\n'
    '    cluster_outline("B: BLOWER  J16 AOD4184 + R3/D2", *_union_aabb(blower_boxes, pad=0.2), face="F", pad=0)\n',
    '    cluster_outline("C: HMI  J17 LCD + J23 TP + J18 ENC + J15 BZ", *_union_aabb(hmi_boxes, pad=0.2), face="F", pad=0)\n'
    '    cluster_outline("U: BUP-30S  J14 + R1 4k7", *_union_aabb(bup_boxes, pad=0.2), face="F", pad=0)\n'
    '    cluster_outline("B: BLOWER  J16 AOD4184 + R3/D2", *_union_aabb(blower_boxes, pad=0.2), face="F", pad=0)\n'
    '    cluster_outline("5: SHIFT  U10/U11 595 DIP + R4 + C21", *_union_aabb(shift_boxes, pad=0.2), face="F", pad=0)\n',
    "cluster outline SHIFT",
)

# schematic notes + embed
if '_embed_from_lib("74HC595")' not in t:
    must(
        '            _embed_from_lib("ULN2003AN"),\n',
        '            _embed_from_lib("74HC595"),\n'
        '            _embed_from_lib("ULN2003AN"),\n',
        "embed 595",
    )

must(
    """    parts.append(text("BOTTOM: U5-U7 ULN2003 GPIO direct | TOP: J5-J7 28BYJ", 20.32, 185.0, 1.27))
    parts.append(text("ULN IN = BYJ*_IN_* from IO (no 74HC595)", 20.32, 190.5, 1.0))
    parts.append(text("U5/U6/U7 COM(9)=+12V; phases → J5-J7", 20.32, 195.58, 1.0))
""",
    """    parts.append(text("BOTTOM: U10/U11 74HC595 DIP + U5-U7 ULN | TOP: J5-J7 28BYJ", 20.32, 185.0, 1.27))
    parts.append(text("SER/SRCLK/RCLK/OE=IO10-13; buy DIP IC not LED-bar module; R4 OE PU", 20.32, 190.5, 1.0))
    parts.append(text("U10 Q0-3->U5; Q4-7->U6; U11 Q0-3->U7; COM=+12V", 20.32, 195.58, 1.0))
""",
    "sch notes",
)

must(
    '    parts += wire_path(u1_pin(PIN_BY_NAME["IO47"]), (j18_pin(3)[0] - 8, u1_pin(PIN_BY_NAME["IO47"])[1]), j18_pin(3))\n'
    '    parts.append(label("ENC_A", j18_pin(3)[0] - 6, j18_pin(3)[1]))\n'
    '    parts += wire_path(u1_pin(PIN_BY_NAME["IO45"]), (j18_pin(4)[0] - 6, u1_pin(PIN_BY_NAME["IO45"])[1]), j18_pin(4))\n',
    '    parts += wire_path(u1_pin(PIN_BY_NAME["IO38"]), (j18_pin(3)[0] - 8, u1_pin(PIN_BY_NAME["IO38"])[1]), j18_pin(3))\n'
    '    parts.append(label("ENC_A", j18_pin(3)[0] - 6, j18_pin(3)[1]))\n'
    '    parts += wire_path(u1_pin(PIN_BY_NAME["IO41"]), (j18_pin(4)[0] - 6, u1_pin(PIN_BY_NAME["IO41"])[1]), j18_pin(4))\n',
    "sch ENC pins",
)

must(
    '            "J18 ENC: wall-mount EC11 cable → GND/3V3/A/B; CLK=IO47 DT=IO45; no SW",\n',
    '            "J18 ENC: wall-mount EC11 → GND/3V3/A/B; CLK=IO38 DT=IO41; no SW",\n',
    "sch ENC text",
)

# readme BOM
must(
    "# ESP32-S3 Baseboard — BOM (ULN2003 direct GPIO)",
    "# ESP32-S3 Baseboard — BOM (ULN2003 + 74HC595 DIP)",
    "readme title",
)

# Fix deleted line and add 595 rows in write_readme — replace GPIO table section
old_readme_gpio = """| U5–U7 | **ULN2003AN** DIP-16 | 28BYJ-48 phase drivers; COM=+12V; IN←GPIO |
| R1 | 4k7 | BUP NPN pull-up → OPTO_IN4 |
| R2/R3 | 10k | EN_TMC PU / BLOWER PD |
| C20 | 470µ | Bulk @ TMC |
| C21 | 100µ | Shared ULN COM bulk |
| ~~J2~~ | — | **XOÁ** (Mot trên U3) |
| J5–J7 | **1×05** | 28BYJ-48 |
| J8/J10/J12 | 1×04 endstop | HOME; VCC/GND NC; SIG+SNS → opto |
| J14 | 1×04 | BUP-30S |
| J15–J18/J23 | — | Buzzer / TFT LCD+TP / **EC11 ENC** |
| J17.8 LED | +3V3 | TFT backlight always on (no GPIO) |

**Deleted:** J2, J4/J9/J11/J13, J19–J22 field, U10/U11 74HC595, R4, U45–U48, U4/U9, DRV8871.
"""

new_readme_gpio = """| U10/U11 | **74HC595 DIP-16** | Shift → ULN (12 pha). **IC DIP**, không LED-thanh |
| R4 | 10k axial | `/OE` pull-up → +3V3 |
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
"""
if old_readme_gpio not in t:
    # try partial
    print("WARN readme block exact miss — trying alt")
else:
    must(old_readme_gpio, new_readme_gpio, "readme parts")

must(
    """| HOME OUT1-3 / BUP OUT4 | IO1,2,4,5 |
| BYJ1 ULN IN A–D | IO10–13 |
| BYJ2 ULN IN A–D | IO7,8,14,15 |
| BYJ3 ULN IN A–D | IO38,41,6,48 |
| TMC STEP/DIR/EN | IO16–18 |
| ENC_A / ENC_B | IO47 / IO45 |
| Buzzer / blower | IO9 / IO3 |
""",
    """| HOME OUT1-3 / BUP OUT4 | IO1,2,4,5 |
| SER / SRCLK / RCLK / OE_595 | IO10–13 |
| TMC STEP/DIR/EN | IO16–18 |
| TFT SPI + BL + touch | IO39/40/42/21/46/45 + MISO47 T_CS48 T_IRQ6 |
| ENC_A / ENC_B | IO38 / IO41 |
| Buzzer / blower | IO9 / IO3 |
| Spare | IO7,8,14,15 |
""",
    "readme gpio",
)

must(
    "        write_uln2003_footprint(),\n",
    "        write_uln2003_footprint(),\n"
    "        write_74hc595_footprint(),\n",
    "main 595 fp",
)

p.write_text(t, encoding="utf-8")
print("WROTE", p)
