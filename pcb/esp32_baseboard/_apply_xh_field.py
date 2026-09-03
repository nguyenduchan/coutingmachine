# -*- coding: utf-8 -*-
"""Apply JST-XH field I/O + J31A/J31B split to gen_power_carrier.py / gen_submodules.py."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
CARRIER = ROOT / "gen_power_carrier.py"
SUB = ROOT / "gen_submodules.py"


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"MISSING [{label}]:\n{old[:120]!r}...")
    return text.replace(old, new, 1)


def patch_carrier(t: str) -> str:
    t = _replace_once(
        t,
        'ENC_PINS = len(ENC_HEADER)\nENC_FP = "PinHeader_1x04_ENC"\nENC_SYM = "Conn_1x04_ENC"',
        'ENC_PINS = len(ENC_HEADER)\nENC_FP = ENC_XH_FP\nENC_SYM = "Conn_JST_XH_04_ENC"',
        "ENC_FP",
    )

    # Symbol lib: emit both M2 plugs
    t = _replace_once(
        t,
        """    _emit_conn_header_sym(
        OPTO4_SYM, OPTO4_FP, OPTO4_HEADER, "M2 SOCK",
        "J31 female: plug M2 OPTO4 (4xPC817 + 2k2/10k)",
    )""",
        """    _emit_conn_header_sym(
        "Conn_JST_XH_06", OPTO_IN_FP, OPTO_IN_HEADER, "M2 IN",
        "J31A XH-6 keyed — M2 field IN + SNS/GND",
    )
    _emit_conn_header_sym(
        "Conn_JST_XH_05", OPTO_OUT_FP, OPTO_OUT_HEADER, "M2 OUT",
        "J31B XH-5 keyed — M2 OUT + 3V3",
    )
    _emit_conn_header_sym(
        ENDSTOP_SYM, ENDSTOP_FP, ENDSTOP_HEADER, "HOME XH2",
        "Dry NC limit JST-XH 2P SIG/SNS",
    )""",
        "OPTO symbols",
    )

    # Replace _hdr_1xn with pitch/keyed-aware version
    old_hdr = '''    def _hdr_1xn(fp, ref, val, atx, aty, pads, hrot=0):
        n = len(pads)
        a(f'\\t(footprint "ESP32_Carrier:{fp}"')
        a('\\t\\t(layer "F.Cu")')
        a(f'\\t\\t(uuid "{uid()}")')
        a(f"\\t\\t(at {atx} {aty} {hrot})")
        a(f'\\t\\t(property "Reference" "{ref}"')
        a(f"\\t\\t\\t(at 0 -3.8 {hrot})")
        a('\\t\\t\\t(layer "F.SilkS")')
        a("\\t\\t\\t(effects (font (size 0.9 0.9) (thickness 0.12)))")
        a(f'\\t\\t\\t(uuid "{uid()}")')
        a("\\t\\t)")
        a(f'\\t\\t(property "Value" "{val}"')
        a(f"\\t\\t\\t(at 0 {(n - 1) * PITCH + 3.8} {hrot})")
        a('\\t\\t\\t(layer "F.Fab")')
        a("\\t\\t\\t(effects (font (size 0.8 0.8) (thickness 0.1)))")
        a(f'\\t\\t\\t(uuid "{uid()}")')
        a("\\t\\t)")
        a("\\t\\t(attr through_hole)")
        for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
            a("\\t\\t(fp_rect")
            a("\\t\\t\\t(start -1.8 -1.8)")
            a(f"\\t\\t\\t(end 1.8 {(n - 1) * PITCH + 1.8})")
            a(f"\\t\\t\\t(stroke (width {w}) (type solid))")
            a("\\t\\t\\t(fill none)")
            a(f'\\t\\t\\t(layer "{layer}")')
            a(f'\\t\\t\\t(uuid "{uid()}")')
            a("\\t\\t)")
        for pi, (neti, netn, lab) in enumerate(pads):
            y = pi * PITCH
            a(f'\\t\\t(fp_text user "{lab}"')
            a(f"\\t\\t\\t(at 3.2 {y} {hrot})")
            a('\\t\\t\\t(layer "F.SilkS")')
            a("\\t\\t\\t(effects (font (size 0.7 0.7) (thickness 0.1)) (justify left))")
            a(f'\\t\\t\\t(uuid "{uid()}")')
            a("\\t\\t)")
            if pi == 0:
                a('\\t\\t(fp_text user "1"')
                a(f"\\t\\t\\t(at -2.6 {y} {hrot})")
                a('\\t\\t\\t(layer "F.SilkS")')
                a("\\t\\t\\t(effects (font (size 0.7 0.7) (thickness 0.1)))")
                a(f'\\t\\t\\t(uuid "{uid()}")')
                a("\\t\\t)")
            shape = "rect" if pi == 0 else "circle"
            a(f'\\t\\t(pad "{pi + 1}" thru_hole {shape}')
            a(f"\\t\\t\\t(at 0 {y})")
            a("\\t\\t\\t(size 1.7 1.7)")
            a("\\t\\t\\t(drill 1.0)")
            a('\\t\\t\\t(layers "*.Cu" "*.Mask")')
            if neti:
                a(f'\\t\\t\\t(net {neti} "{netn}")')
            a(f'\\t\\t\\t(uuid "{uid()}")')
            a("\\t\\t)")
        a("\\t)")'''

    new_hdr = '''    def _hdr_1xn(fp, ref, val, atx, aty, pads, hrot=0, pitch=None, keyed=False):
        if pitch is None:
            pitch = PITCH
        n = len(pads)
        span = (n - 1) * pitch
        pad_sz = 1.6 if keyed else 1.7
        drill = 0.9 if keyed else 1.0
        half = 3.2 if keyed else 1.8
        a(f'\\t(footprint "ESP32_Carrier:{fp}"')
        a('\\t\\t(layer "F.Cu")')
        a(f'\\t\\t(uuid "{uid()}")')
        a(f"\\t\\t(at {atx} {aty} {hrot})")
        a(f'\\t\\t(property "Reference" "{ref}"')
        a(f"\\t\\t\\t(at 0 {-3.0 if keyed else -3.8} {hrot})")
        a('\\t\\t\\t(layer "F.SilkS")')
        a("\\t\\t\\t(effects (font (size 0.9 0.9) (thickness 0.12)))")
        a(f'\\t\\t\\t(uuid "{uid()}")')
        a("\\t\\t)")
        a(f'\\t\\t(property "Value" "{val}"')
        a(f"\\t\\t\\t(at 0 {span + 3.0} {hrot})")
        a('\\t\\t\\t(layer "F.Fab")')
        a("\\t\\t\\t(effects (font (size 0.8 0.8) (thickness 0.1)))")
        a(f'\\t\\t\\t(uuid "{uid()}")')
        a("\\t\\t)")
        a("\\t\\t(attr through_hole)")
        for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
            a("\\t\\t(fp_rect")
            a(f"\\t\\t\\t(start {-half} {-2.0 if keyed else -1.8})")
            a(f"\\t\\t\\t(end {half} {span + (2.0 if keyed else 1.8)})")
            a(f"\\t\\t\\t(stroke (width {w}) (type solid))")
            a("\\t\\t\\t(fill none)")
            a(f'\\t\\t\\t(layer "{layer}")')
            a(f'\\t\\t\\t(uuid "{uid()}")')
            a("\\t\\t)")
        if keyed:
            a("\\t\\t(fp_line")
            a("\\t\\t\\t(start -3.2 -0.6)")
            a("\\t\\t\\t(end -4.2 0)")
            a('\\t\\t\\t(stroke (width 0.15) (type solid))')
            a('\\t\\t\\t(layer "F.SilkS")')
            a(f'\\t\\t\\t(uuid "{uid()}")')
            a("\\t\\t)")
            a("\\t\\t(fp_line")
            a("\\t\\t\\t(start -4.2 0)")
            a("\\t\\t\\t(end -3.2 0.6)")
            a('\\t\\t\\t(stroke (width 0.15) (type solid))')
            a('\\t\\t\\t(layer "F.SilkS")')
            a(f'\\t\\t\\t(uuid "{uid()}")')
            a("\\t\\t)")
            fp_silk_text("KEY", -5.2, 0, hrot, 0.65)
        for pi, (neti, netn, lab) in enumerate(pads):
            y = pi * pitch
            a(f'\\t\\t(fp_text user "{lab}"')
            a(f"\\t\\t\\t(at {4.2 if keyed else 3.2} {y} {hrot})")
            a('\\t\\t\\t(layer "F.SilkS")')
            a("\\t\\t\\t(effects (font (size 0.65 0.65) (thickness 0.1)) (justify left))")
            a(f'\\t\\t\\t(uuid "{uid()}")')
            a("\\t\\t)")
            if pi == 0 and not keyed:
                a('\\t\\t(fp_text user "1"')
                a(f"\\t\\t\\t(at -2.6 {y} {hrot})")
                a('\\t\\t\\t(layer "F.SilkS")')
                a("\\t\\t\\t(effects (font (size 0.7 0.7) (thickness 0.1)))")
                a(f'\\t\\t\\t(uuid "{uid()}")')
                a("\\t\\t)")
            shape = "rect" if pi == 0 else "circle"
            a(f'\\t\\t(pad "{pi + 1}" thru_hole {shape}')
            a(f"\\t\\t\\t(at 0 {y})")
            a(f"\\t\\t\\t(size {pad_sz} {pad_sz})")
            a(f"\\t\\t\\t(drill {drill})")
            a('\\t\\t\\t(layers "*.Cu" "*.Mask")')
            if neti:
                a(f'\\t\\t\\t(net {neti} "{netn}")')
            a(f'\\t\\t\\t(uuid "{uid()}")')
            a("\\t\\t)")
        a("\\t)")'''

    t = _replace_once(t, old_hdr, new_hdr, "_hdr_1xn")

    # J31 → J31A + J31B
    old_j31 = '''    # ===== J31 OPTO4 female (M2: 4xPC817 + 2k2/10k on daughter) =====
    j31x, j31y = FP["j31x"], FP["j31y"]
    j31_nets = [
        (25, "/OPTO_IN1", "IN1"),
        (26, "/OPTO_IN2", "IN2"),
        (27, "/OPTO_IN3", "IN3"),
        (28, "/OPTO_IN4", "IN4"),
        (46, "+12V_SNS", "SNS"),
        (2, "GND", "GND"),
        (16, "/OPTO_OUT1", "OUT1"),
        (17, "/OPTO_OUT2", "OUT2"),
        (18, "/OPTO_OUT3", "OUT3"),
        (19, "/OPTO_OUT4", "OUT4"),
        (4, "+3V3", "3V3"),
    ]
    a(f'\\t(footprint "ESP32_Carrier:{OPTO4_FP}"')
    a('\\t\\t(layer "F.Cu")')
    a(f'\\t\\t(uuid "{uid()}")')
    a(f"\\t\\t(at {j31x} {j31y})")
    a('\\t\\t(property "Reference" "J31"')
    a('\\t\\t\\t(at 0 -2.8 0)')
    a('\\t\\t\\t(layer "F.SilkS")')
    a("\\t\\t\\t(effects (font (size 0.9 0.9) (thickness 0.12)))")
    a(f'\\t\\t\\t(uuid "{uid()}")')
    a("\\t\\t)")
    a('\\t\\t(property "Value" "M2_OPTO4"')
    a(f'\\t\\t\\t(at 0 {(OPTO4_PINS - 1) * PITCH + 2.8} 0)')
    a('\\t\\t\\t(layer "F.Fab")')
    a("\\t\\t\\t(effects (font (size 0.7 0.7) (thickness 0.1)))")
    a(f'\\t\\t\\t(uuid "{uid()}")')
    a("\\t\\t)")
    a("\\t\\t(attr through_hole)")
    # Shroud outline + key at pin1 — mate with KF2510 / Dupont keyed housing
    fp_silk_rect(-2.4, -2.2, 2.4, (OPTO4_PINS - 1) * PITCH + 2.2, "F.SilkS")
    a("\\t\\t(fp_line")
    a("\\t\\t\\t(start -2.4 -0.8)")
    a("\\t\\t\\t(end -3.4 0)")
    a('\\t\\t\\t(stroke (width 0.15) (type solid))')
    a('\\t\\t\\t(layer "F.SilkS")')
    a(f'\\t\\t\\t(uuid "{uid()}")')
    a("\\t\\t)")
    a("\\t\\t(fp_line")
    a("\\t\\t\\t(start -3.4 0)")
    a("\\t\\t\\t(end -2.4 0.8)")
    a('\\t\\t\\t(stroke (width 0.15) (type solid))')
    a('\\t\\t\\t(layer "F.SilkS")')
    a(f'\\t\\t\\t(uuid "{uid()}")')
    a("\\t\\t)")
    fp_silk_text("KEY", -4.5, 0, 0, 0.65)
    for i, (ni, nn, lab) in enumerate(j31_nets):
        y = i * PITCH
        a(f'\\t\\t(fp_text user "{lab}"')
        a(f"\\t\\t\\t(at 3.5 {y} 0)")
        a('\\t\\t\\t(layer "F.SilkS")')
        a('\\t\\t\\t(effects (font (size 0.6 0.6) (thickness 0.1)) (justify left))')
        a(f'\\t\\t\\t(uuid "{uid()}")')
        a("\\t\\t)")
        shape = "rect" if i == 0 else "circle"
        a(f'\\t\\t(pad "{i + 1}" thru_hole {shape}')
        a(f"\\t\\t\\t(at 0 {y})")
        a("\\t\\t\\t(size 1.7 1.7)")
        a("\\t\\t\\t(drill 1.0)")
        a('\\t\\t\\t(layers "*.Cu" "*.Mask")')
        a(f'\\t\\t\\t(net {ni} "{nn}")')
        a(f'\\t\\t\\t(uuid "{uid()}")')
        a("\\t\\t)")
    a("\\t)")
    gr_text("J31 M2 KEYED housing (KF2510)", j31x - 8, j31y - 4.5, "F.SilkS", 0.65)

    def _opto_in_pad_ch(ch_i: int):
        """World coords of J31 INx pad (pins 1-4)."""
        return (j31x, j31y + ch_i * PITCH)'''

    new_j31 = '''    # ===== J31A/J31B M2 OPTO4 (XH keyed: IN-6 + OUT-5) =====
    j31ax, j31ay = FP["j31ax"], FP["j31ay"]
    j31bx, j31by = FP["j31bx"], FP["j31by"]
    j31x, j31y = j31ax, j31ay  # legacy alias = J31A
    _hdr_1xn(
        OPTO_IN_FP, "J31A", "M2_IN",
        j31ax, j31ay,
        [
            (25, "/OPTO_IN1", "IN1"),
            (26, "/OPTO_IN2", "IN2"),
            (27, "/OPTO_IN3", "IN3"),
            (28, "/OPTO_IN4", "IN4"),
            (46, "+12V_SNS", "SNS"),
            (2, "GND", "GND"),
        ],
        pitch=XH_PITCH, keyed=True,
    )
    _hdr_1xn(
        OPTO_OUT_FP, "J31B", "M2_OUT",
        j31bx, j31by,
        [
            (16, "/OPTO_OUT1", "OUT1"),
            (17, "/OPTO_OUT2", "OUT2"),
            (18, "/OPTO_OUT3", "OUT3"),
            (19, "/OPTO_OUT4", "OUT4"),
            (4, "+3V3", "3V3"),
        ],
        pitch=XH_PITCH, keyed=True,
    )
    gr_text("J31A/B M2 JST-XH KEYED", j31ax - 6, j31ay - 4.5, "F.SilkS", 0.65)

    def _opto_in_pad_ch(ch_i: int):
        """World coords of J31A INx pad (pins 1-4)."""
        return (j31ax, j31ay + ch_i * XH_PITCH)'''

    # Problem: _hdr_1xn is defined AFTER J31 block currently.
    # So we cannot call _hdr_1xn before its definition.
    # Keep inline emit OR move J31 after _hdr_1xn.
    # Fix: leave J31 where it is but use inline emit (copy of J30 style), not _hdr_1xn.
    # Revert new_j31 to inline without _hdr_1xn.

    new_j31 = '''    # ===== J31A/J31B M2 OPTO4 (XH keyed: IN-6 + OUT-5) =====
    j31ax, j31ay = FP["j31ax"], FP["j31ay"]
    j31bx, j31by = FP["j31bx"], FP["j31by"]
    j31x, j31y = j31ax, j31ay  # legacy alias = J31A

    def _emit_xh_sock(fp, ref, val, ax, ay, pad_rows):
        n = len(pad_rows)
        span = (n - 1) * XH_PITCH
        a(f'\\t(footprint "ESP32_Carrier:{fp}"')
        a('\\t\\t(layer "F.Cu")')
        a(f'\\t\\t(uuid "{uid()}")')
        a(f"\\t\\t(at {ax} {ay})")
        a(f'\\t\\t(property "Reference" "{ref}"')
        a('\\t\\t\\t(at 0 -3.0 0)')
        a('\\t\\t\\t(layer "F.SilkS")')
        a("\\t\\t\\t(effects (font (size 0.9 0.9) (thickness 0.12)))")
        a(f'\\t\\t\\t(uuid "{uid()}")')
        a("\\t\\t)")
        a(f'\\t\\t(property "Value" "{val}"')
        a(f'\\t\\t\\t(at 0 {span + 3.0} 0)')
        a('\\t\\t\\t(layer "F.Fab")')
        a("\\t\\t\\t(effects (font (size 0.7 0.7) (thickness 0.1)))")
        a(f'\\t\\t\\t(uuid "{uid()}")')
        a("\\t\\t)")
        a("\\t\\t(attr through_hole)")
        fp_silk_rect(-3.2, -2.0, 3.2, span + 2.0, "F.SilkS")
        a("\\t\\t(fp_line")
        a("\\t\\t\\t(start -3.2 -0.6)")
        a("\\t\\t\\t(end -4.2 0)")
        a('\\t\\t\\t(stroke (width 0.15) (type solid))')
        a('\\t\\t\\t(layer "F.SilkS")')
        a(f'\\t\\t\\t(uuid "{uid()}")')
        a("\\t\\t)")
        a("\\t\\t(fp_line")
        a("\\t\\t\\t(start -4.2 0)")
        a("\\t\\t\\t(end -3.2 0.6)")
        a('\\t\\t\\t(stroke (width 0.15) (type solid))')
        a('\\t\\t\\t(layer "F.SilkS")')
        a(f'\\t\\t\\t(uuid "{uid()}")')
        a("\\t\\t)")
        fp_silk_text("KEY", -5.2, 0, 0, 0.65)
        for i, (ni, nn, lab) in enumerate(pad_rows):
            y = i * XH_PITCH
            a(f'\\t\\t(fp_text user "{lab}"')
            a(f"\\t\\t\\t(at 4.2 {y} 0)")
            a('\\t\\t\\t(layer "F.SilkS")')
            a('\\t\\t\\t(effects (font (size 0.6 0.6) (thickness 0.1)) (justify left))')
            a(f'\\t\\t\\t(uuid "{uid()}")')
            a("\\t\\t)")
            shape = "rect" if i == 0 else "circle"
            a(f'\\t\\t(pad "{i + 1}" thru_hole {shape}')
            a(f"\\t\\t\\t(at 0 {y})")
            a("\\t\\t\\t(size 1.6 1.6)")
            a("\\t\\t\\t(drill 0.9)")
            a('\\t\\t\\t(layers "*.Cu" "*.Mask")')
            a(f'\\t\\t\\t(net {ni} "{nn}")')
            a(f'\\t\\t\\t(uuid "{uid()}")')
            a("\\t\\t)")
        a("\\t)")

    _emit_xh_sock(
        OPTO_IN_FP, "J31A", "M2_IN", j31ax, j31ay,
        [
            (25, "/OPTO_IN1", "IN1"),
            (26, "/OPTO_IN2", "IN2"),
            (27, "/OPTO_IN3", "IN3"),
            (28, "/OPTO_IN4", "IN4"),
            (46, "+12V_SNS", "SNS"),
            (2, "GND", "GND"),
        ],
    )
    _emit_xh_sock(
        OPTO_OUT_FP, "J31B", "M2_OUT", j31bx, j31by,
        [
            (16, "/OPTO_OUT1", "OUT1"),
            (17, "/OPTO_OUT2", "OUT2"),
            (18, "/OPTO_OUT3", "OUT3"),
            (19, "/OPTO_OUT4", "OUT4"),
            (4, "+3V3", "3V3"),
        ],
    )
    gr_text("J31A/B M2 JST-XH KEYED", j31ax - 6, j31ay - 4.5, "F.SilkS", 0.65)

    def _opto_in_pad_ch(ch_i: int):
        """World coords of J31A INx pad (pins 1-4)."""
        return (j31ax, j31ay + ch_i * XH_PITCH)'''

    t = _replace_once(t, old_j31, new_j31, "J31 split")

    # HOME XH-2
    t = _replace_once(
        t,
        """        _hdr_1xn(
            ENDSTOP_FP, jref, f"END_{tag}", lx, ly,
            [
                (None, "", "VCC"),
                (None, "", "GND"),
                (ni, nn, "SIG"),
                (46, "+12V_SNS", "SNS"),
            ],
        )""",
        """        _hdr_1xn(
            ENDSTOP_FP, jref, f"END_{tag}", lx, ly,
            [
                (ni, nn, "SIG"),
                (46, "+12V_SNS", "SNS"),
            ],
            pitch=XH_PITCH, keyed=True,
        )""",
        "HOME XH2",
    )

    # J14 → XH4 (replace footprint string + PITCH→XH_PITCH in that block only)
    t = _replace_once(
        t,
        '    a(\'\\t(footprint "ESP32_Carrier:PinHeader_1x04_BUP30S"\'',
        '    a(f\'\\t(footprint "ESP32_Carrier:{BUP_XH_FP}"\'',
        "J14 fp",
    )
    # Fix BUP pad pitch: in bup_pads loop `y = i * PITCH` — change nearby silk too
    t = _replace_once(
        t,
        '    gr_text("Brn +12 Blu GND Blk OUT Wht CTRL", j14x - 3, j14y + 3 * PITCH + 4.5, "F.SilkS", 0.65)\n'
        '    gr_text("R1 4k7 pullup NPN", r1x - 5, r1y + 3.5, "F.SilkS", 0.7)\n'
        "    bup_pads = [\n"
        '        (1, "+12V", 46, "+12V_SNS"),\n'
        '        (2, "GND", 2, "GND"),\n'
        '        (3, "OUT", 28, "/OPTO_IN4"),\n'
        '        (4, "CTRL", 0, ""),  # jumper to +12V or GND by user\n'
        "    ]\n",
        '    gr_text("Brn +12 Blu GND Blk OUT Wht CTRL", j14x - 3, j14y + 3 * XH_PITCH + 4.5, "F.SilkS", 0.65)\n'
        '    gr_text("R1 4k7 pullup NPN", r1x - 5, r1y + 3.5, "F.SilkS", 0.7)\n'
        "    bup_pads = [\n"
        '        (1, "+12V", 46, "+12V_SNS"),\n'
        '        (2, "GND", 2, "GND"),\n'
        '        (3, "OUT", 28, "/OPTO_IN4"),\n'
        '        (4, "CTRL", 0, ""),  # jumper to +12V or GND by user\n'
        "    ]\n",
        "J14 silk pitch",
    )
    t = _replace_once(
        t,
        '    a(f"\\t\\t\\t(at 0 {3 * PITCH + 3.8} 0)")\n'
        '    a(\'\\t\\t\\t(layer "F.Fab")\')\n'
        '    a("\\t\\t\\t(effects (font (size 0.9 0.9) (thickness 0.12)))")\n'
        '    a(f\'\\t\\t\\t(uuid "{uid()}")\')\n'
        '    a("\\t\\t)")\n'
        '    a("\\t\\t(attr through_hole)")\n'
        '    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):\n'
        '        a("\\t\\t(fp_rect")\n'
        '        a("\\t\\t\\t(start -1.8 -1.8)")\n'
        '        a(f"\\t\\t\\t(end 1.8 {3 * PITCH + 1.8})")\n',
        '    a(f"\\t\\t\\t(at 0 {3 * XH_PITCH + 3.8} 0)")\n'
        '    a(\'\\t\\t\\t(layer "F.Fab")\')\n'
        '    a("\\t\\t\\t(effects (font (size 0.9 0.9) (thickness 0.12)))")\n'
        '    a(f\'\\t\\t\\t(uuid "{uid()}")\')\n'
        '    a("\\t\\t)")\n'
        '    a("\\t\\t(attr through_hole)")\n'
        '    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):\n'
        '        a("\\t\\t(fp_rect")\n'
        '        a("\\t\\t\\t(start -3.2 -2.0)")\n'
        '        a(f"\\t\\t\\t(end 3.2 {3 * XH_PITCH + 2.0})")\n',
        "J14 shroud",
    )
    t = _replace_once(
        t,
        "    for i, (num, lab, neti, netn) in enumerate(bup_pads):\n"
        "        y = i * PITCH\n",
        "    for i, (num, lab, neti, netn) in enumerate(bup_pads):\n"
        "        y = i * XH_PITCH\n",
        "J14 pad pitch",
    )
    # R1 offset + BUP track pads
    t = _replace_once(
        t,
        "    r1x, r1y = j14x, j14y + 5.2 * PITCH\n",
        "    r1x, r1y = j14x, j14y + 5.2 * XH_PITCH\n",
        "R1 pos",
    )
    t = _replace_once(
        t,
        "    p12 = (j14x, j14y)\n"
        "    pg = (j14x, j14y + PITCH)\n"
        "    po = (j14x, j14y + 2 * PITCH)\n",
        "    p12 = (j14x, j14y)\n"
        "    pg = (j14x, j14y + XH_PITCH)\n"
        "    po = (j14x, j14y + 2 * XH_PITCH)\n",
        "BUP tracks",
    )

    # J15 buzzer XH3
    t = _replace_once(
        t,
        '    a(\'\\t(footprint "ESP32_Carrier:PinHeader_1x03_Buzzer"\'',
        '    a(f\'\\t(footprint "ESP32_Carrier:{BZ_XH_FP}"\'',
        "J15 fp",
    )
    t = _replace_once(
        t,
        '    a(f"\\t\\t\\t(at 0 {2 * PITCH + 3.8} 0)")\n'
        '    a(\'\\t\\t\\t(layer "F.Fab")\')\n'
        '    a("\\t\\t\\t(effects (font (size 0.8 0.8) (thickness 0.1)))")\n'
        '    a(f\'\\t\\t\\t(uuid "{uid()}")\')\n'
        '    a("\\t\\t)")\n'
        '    a("\\t\\t(attr through_hole)")\n'
        '    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):\n'
        '        a("\\t\\t(fp_rect")\n'
        '        a("\\t\\t\\t(start -1.8 -1.8)")\n'
        '        a(f"\\t\\t\\t(end 1.8 {2 * PITCH + 1.8})")\n'
        '        a(f"\\t\\t\\t(stroke (width {w}) (type solid))")\n'
        '        a("\\t\\t\\t(fill none)")\n'
        '        a(f\'\\t\\t\\t(layer "{layer}")\')\n'
        '        a(f\'\\t\\t\\t(uuid "{uid()}")\')\n'
        '        a("\\t\\t)")\n'
        "    for i, (ni, nn, lab) in enumerate(\n"
        '        [(3, "+5V", "VCC5"), (2, "GND", "GND"), (54, "/BUZZER", "SIG")]\n'
        "    ):\n"
        "        y = i * PITCH\n",
        '    a(f"\\t\\t\\t(at 0 {2 * XH_PITCH + 3.8} 0)")\n'
        '    a(\'\\t\\t\\t(layer "F.Fab")\')\n'
        '    a("\\t\\t\\t(effects (font (size 0.8 0.8) (thickness 0.1)))")\n'
        '    a(f\'\\t\\t\\t(uuid "{uid()}")\')\n'
        '    a("\\t\\t)")\n'
        '    a("\\t\\t(attr through_hole)")\n'
        '    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):\n'
        '        a("\\t\\t(fp_rect")\n'
        '        a("\\t\\t\\t(start -3.2 -2.0)")\n'
        '        a(f"\\t\\t\\t(end 3.2 {2 * XH_PITCH + 2.0})")\n'
        '        a(f"\\t\\t\\t(stroke (width {w}) (type solid))")\n'
        '        a("\\t\\t\\t(fill none)")\n'
        '        a(f\'\\t\\t\\t(layer "{layer}")\')\n'
        '        a(f\'\\t\\t\\t(uuid "{uid()}")\')\n'
        '        a("\\t\\t)")\n'
        "    for i, (ni, nn, lab) in enumerate(\n"
        '        [(3, "+5V", "VCC5"), (2, "GND", "GND"), (54, "/BUZZER", "SIG")]\n'
        "    ):\n"
        "        y = i * XH_PITCH\n",
        "J15 XH",
    )

    # J16 blower XH4
    t = _replace_once(
        t,
        '    a(\'\\t(footprint "ESP32_Carrier:PinHeader_1x04_MOSFET"\'',
        '    a(f\'\\t(footprint "ESP32_Carrier:{BLW_XH_FP}"\'',
        "J16 fp",
    )
    t = _replace_once(
        t,
        '    a(f"\\t\\t\\t(at 0 {3 * PITCH + 3.8} 0)")\n'
        '    a(\'\\t\\t\\t(layer "F.Fab")\')\n'
        '    a("\\t\\t\\t(effects (font (size 0.8 0.8) (thickness 0.1)))")\n'
        '    a(f\'\\t\\t\\t(uuid "{uid()}")\')\n'
        '    a("\\t\\t)")\n'
        '    a("\\t\\t(attr through_hole)")\n'
        '    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):\n'
        '        a("\\t\\t(fp_rect")\n'
        '        a("\\t\\t\\t(start -1.8 -1.8)")\n'
        '        a(f"\\t\\t\\t(end 1.8 {3 * PITCH + 1.8})")\n'
        '        a(f"\\t\\t\\t(stroke (width {w}) (type solid))")\n'
        '        a("\\t\\t\\t(fill none)")\n'
        '        a(f\'\\t\\t\\t(layer "{layer}")\')\n'
        '        a(f\'\\t\\t\\t(uuid "{uid()}")\')\n'
        '        a("\\t\\t)")\n'
        "    for i, (ni, nn, lab) in enumerate(\n"
        "        [\n"
        '            (55, "/BLOWER", "PWM"),\n'
        '            (2, "GND", "GND"),\n'
        '            (1, "+12V", "+12V"),\n'
        '            (61, "/BLW_RET", "FAN-"),\n'
        "        ]\n"
        "    ):\n"
        "        y = i * PITCH\n",
        '    a(f"\\t\\t\\t(at 0 {3 * XH_PITCH + 3.8} 0)")\n'
        '    a(\'\\t\\t\\t(layer "F.Fab")\')\n'
        '    a("\\t\\t\\t(effects (font (size 0.8 0.8) (thickness 0.1)))")\n'
        '    a(f\'\\t\\t\\t(uuid "{uid()}")\')\n'
        '    a("\\t\\t)")\n'
        '    a("\\t\\t(attr through_hole)")\n'
        '    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):\n'
        '        a("\\t\\t(fp_rect")\n'
        '        a("\\t\\t\\t(start -3.2 -2.0)")\n'
        '        a(f"\\t\\t\\t(end 3.2 {3 * XH_PITCH + 2.0})")\n'
        '        a(f"\\t\\t\\t(stroke (width {w}) (type solid))")\n'
        '        a("\\t\\t\\t(fill none)")\n'
        '        a(f\'\\t\\t\\t(layer "{layer}")\')\n'
        '        a(f\'\\t\\t\\t(uuid "{uid()}")\')\n'
        '        a("\\t\\t)")\n'
        "    for i, (ni, nn, lab) in enumerate(\n"
        "        [\n"
        '            (55, "/BLOWER", "PWM"),\n'
        '            (2, "GND", "GND"),\n'
        '            (1, "+12V", "+12V"),\n'
        '            (61, "/BLW_RET", "FAN-"),\n'
        "        ]\n"
        "    ):\n"
        "        y = i * XH_PITCH\n",
        "J16 XH",
    )
    t = _replace_once(
        t,
        "    j16_pwm = (j16x, j16y)\n"
        "    j16_gnd = (j16x, j16y + PITCH)\n"
        "    j16_12v = (j16x, j16y + 2 * PITCH)\n",
        "    j16_pwm = (j16x, j16y)\n"
        "    j16_gnd = (j16x, j16y + XH_PITCH)\n"
        "    j16_12v = (j16x, j16y + 2 * XH_PITCH)\n",
        "j16 pads",
    )

    # J18 ENC XH — change pitch in span + pads + route
    t = _replace_once(
        t,
        "    span_e = (ENC_PINS - 1) * PITCH\n"
        '    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):\n'
        '        a("\\t\\t(fp_rect")\n'
        '        a("\\t\\t\\t(start -1.8 -1.8)")\n'
        '        a(f"\\t\\t\\t(end 1.8 {span_e + 1.8})")\n',
        "    span_e = (ENC_PINS - 1) * XH_PITCH\n"
        '    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):\n'
        '        a("\\t\\t(fp_rect")\n'
        '        a("\\t\\t\\t(start -3.2 -2.0)")\n'
        '        a(f"\\t\\t\\t(end 3.2 {span_e + 2.0})")\n',
        "J18 shroud",
    )
    t = _replace_once(
        t,
        '    a(f"\\t\\t\\t(at 0 {(ENC_PINS - 1) * PITCH + 3.8} {enc_rot})")\n',
        '    a(f"\\t\\t\\t(at 0 {(ENC_PINS - 1) * XH_PITCH + 3.8} {enc_rot})")\n',
        "J18 value y",
    )
    t = _replace_once(
        t,
        "    for i, (ni, nn, lab) in enumerate(j18_nets):\n"
        "        y = i * PITCH\n",
        "    for i, (ni, nn, lab) in enumerate(j18_nets):\n"
        "        y = i * XH_PITCH\n",
        "J18 pad pitch",
    )
    t = _replace_once(
        t,
        "    route_mcu_to_top(54, bz, (j15x, j15y + 2 * PITCH), ox + sx(178.0) + 8 * 1.2, side=-3.0, esc_i=8)\n",
        "    route_mcu_to_top(54, bz, (j15x, j15y + 2 * XH_PITCH), ox + sx(178.0) + 8 * 1.2, side=-3.0, esc_i=8)\n",
        "buzzer route",
    )
    t = _replace_once(
        t,
        "        dst = pad_world(j18x, j18y, enc_rot, 0, pin_i * PITCH)\n",
        "        dst = pad_world(j18x, j18y, enc_rot, 0, pin_i * XH_PITCH)\n",
        "enc route",
    )
    t = _replace_once(
        t,
        "    route_mcu_to_top(4, u1_3v3, pad_world(j18x, j18y, enc_rot, 0, PITCH), ox + sx(192.0), y_off=-2.0, side=-3.0, esc_i=12)\n",
        "    route_mcu_to_top(4, u1_3v3, pad_world(j18x, j18y, enc_rot, 0, XH_PITCH), ox + sx(192.0), y_off=-2.0, side=-3.0, esc_i=12)\n",
        "enc 3v3",
    )

    # Eco boxes
    t = _replace_once(
        t,
        "        _hdr_aabb(j18x, j18y, ENC_PINS, enc_rot),\n"
        "        _hdr_aabb(j15x, j15y, 3),\n",
        "        _hdr_aabb(j18x, j18y, ENC_PINS, enc_rot, pitch=XH_PITCH),\n"
        "        _hdr_aabb(j15x, j15y, 3, pitch=XH_PITCH),\n",
        "hmi aabb",
    )
    t = _replace_once(
        t,
        "        _hdr_aabb(j14x, j14y, 4),\n",
        "        _hdr_aabb(j14x, j14y, 4, pitch=XH_PITCH),\n",
        "bup aabb",
    )
    t = _replace_once(
        t,
        "        _hdr_aabb(j16x, j16y, 4),\n",
        "        _hdr_aabb(j16x, j16y, 4, pitch=XH_PITCH),\n",
        "blw aabb",
    )
    t = _replace_once(
        t,
        "            _hdr_aabb(hj[1], hj[2], 4),\n",
        "            _hdr_aabb(hj[1], hj[2], 2, pitch=XH_PITCH),\n",
        "home aabb",
    )
    t = _replace_once(
        t,
        "    opto_boxes = [\n"
        "        _hdr_aabb(j31x, j31y, OPTO4_PINS),\n"
        "    ]\n",
        "    opto_boxes = [\n"
        "        _hdr_aabb(j31ax, j31ay, OPTO_IN_PINS, pitch=XH_PITCH),\n"
        "        _hdr_aabb(j31bx, j31by, OPTO_OUT_PINS, pitch=XH_PITCH),\n"
        "    ]\n",
        "opto aabb",
    )
    t = _replace_once(
        t,
        '    cluster_outline("4: OPTO  J31(M2 OPTO4)", *_union_aabb(opto_boxes, pad=0.2), face="F", pad=0)\n',
        '    cluster_outline("4: OPTO  J31A/B(M2)", *_union_aabb(opto_boxes, pad=0.2), face="F", pad=0)\n',
        "opto cluster",
    )

    # main() footprint writers
    t = _replace_once(
        t,
        """        write_pin_header_footprint(3, "PinHeader_1x03_Buzzer", [p[1] for p in BUZZER_HEADER]),
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
        write_jst_xh_04_socket(),
        write_pin_header_footprint(OPTO4_PINS, OPTO4_FP, [p[1] for p in OPTO4_HEADER]),""",
        """        write_pin_header_footprint(5, BYJ_FP, [p[1] for p in BYJ_HEADER]),
        write_pin_header_footprint(6, "PinHeader_1x06_595CTRL",
                                  ["LDEN", "GND", "VCC", "LDSI", "LDSTR", "LDSCK"]),
        write_pin_header_footprint(24, "PinHeader_1x24_595Q",
                                  [f"{i//8+1}_Q{i%8}" for i in range(24)]),
        write_pin_header_footprint(2, "PinHeader_1x02_LimitSW", ["+12V", "SW"]),
        *write_all_jst_xh_sockets(),""",
        "main fps",
    )

    # Docstring header
    t = _replace_once(
        t,
        "Jacks: J8/J10/J12 HOME endstop 1×04 (2 NC), J14 BUP, J15 buzzer, J16 AOD4184,\n"
        "       J17+J23 TFT+touch, J18 EC11, J15 buzzer. ULN via Shopee 74HC595-24IO module (3x595) east of ESP32.",
        "Jacks: J8/J10/J12 HOME XH-2, J14 BUP XH-4, J15 buzzer XH-3, J16 AOD4184 XH-4,\n"
        "       J17+J23 TFT, J18 ENC XH-4, J31A/B M2. ULN via 74HC595-24IO (3x595) east of ESP32.",
        "docstring",
    )

    return t


def patch_submodules(t: str) -> str:
    # Make _hdr_male_xh generic n-pin
    t = _replace_once(
        t,
        '''def _hdr_male_xh(a, ref: str, labels: list[str], x: float, y: float, nets: list[tuple[int, str]]):
    """JST-XH male plug (pitch 2.5) — mates keyed female on carrier J30."""
    n = len(labels)
    span = (n - 1) * XH_PITCH
    a(f'\\t(footprint "ESP32_Carrier:JST_XH_04_Plug"')
    a('\\t\\t(layer "F.Cu")')
    a(f'\\t\\t(uuid "{uid()}")')
    a(f"\\t\\t(at {x} {y})")
    a(f'\\t\\t(property "Reference" "{ref}"')
    a(f"\\t\\t\\t(at 0 {{-2.8}} 0)")
    a('\\t\\t\\t(layer "F.SilkS")')
    a("\\t\\t\\t(effects (font (size 0.9 0.9) (thickness 0.12)))")
    a(f'\\t\\t\\t(uuid "{uid()}")')
    a("\\t\\t)")
    a('\\t\\t(property "Value" "JST-XH4_to_J30"')
    a(f"\\t\\t\\t(at 0 {{span + 2.8}} 0)")
    a('\\t\\t\\t(layer "F.Fab")')
    a("\\t\\t\\t(effects (font (size 0.7 0.7) (thickness 0.1)))")
    a(f'\\t\\t\\t(uuid "{uid()}")')
    a("\\t\\t)")
    a("\\t\\t(attr through_hole)")
    a("\\t\\t(fp_rect")
    a("\\t\\t\\t(start -3.0 -1.8)")
    a(f"\\t\\t\\t(end 3.0 {{span + 1.8}})")
    a('\\t\\t\\t(stroke (width 0.12) (type solid))')
    a("\\t\\t\\t(fill none)")
    a('\\t\\t\\t(layer "F.SilkS")')
    a(f'\\t\\t\\t(uuid "{uid()}")')
    a("\\t\\t)")
    a("\\t\\t(fp_line (start -3.0 -0.5) (end -4.0 0)")
    a('\\t\\t\\t(stroke (width 0.15) (type solid)) (layer "F.SilkS")')
    a(f'\\t\\t\\t(uuid "{uid()}")')
    a("\\t\\t)")
    for i, (lab, (ni, nn)) in enumerate(zip(labels, nets)):
        yi = i * XH_PITCH
        a(f'\\t\\t(fp_text user "{{lab}}"')
        a(f"\\t\\t\\t(at 3.5 {{yi}} 0)")
        a('\\t\\t\\t(layer "F.SilkS")')
        a('\\t\\t\\t(effects (font (size 0.65 0.65) (thickness 0.1)) (justify left))')
        a(f'\\t\\t\\t(uuid "{{uid()}}")')
        a("\\t\\t)")
        shape = "rect" if i == 0 else "circle"
        a(f'\\t\\t(pad "{{i + 1}}" thru_hole {{shape}}')
        a(f"\\t\\t\\t(at 0 {{yi}})")
        a("\\t\\t\\t(size 1.6 1.6)")
        a("\\t\\t\\t(drill 0.9)")
        a('\\t\\t\\t(layers "*.Cu" "*.Mask")')
        a(f'\\t\\t\\t(net {{ni}} "{{nn}}")')
        a(f'\\t\\t\\t(uuid "{{uid()}}")')
        a("\\t\\t)")
    a("\\t)")''',
        '''def _hdr_male_xh(a, ref: str, labels: list[str], x: float, y: float, nets: list[tuple[int, str]], mate: str = "J30"):
    """JST-XH male plug (pitch 2.5) — mates keyed female on carrier."""
    n = len(labels)
    span = (n - 1) * XH_PITCH
    a(f'\\t(footprint "ESP32_Carrier:JST_XH_{n:02d}_Plug"')
    a('\\t\\t(layer "F.Cu")')
    a(f'\\t\\t(uuid "{uid()}")')
    a(f"\\t\\t(at {x} {y})")
    a(f'\\t\\t(property "Reference" "{ref}"')
    a(f"\\t\\t\\t(at 0 {{-2.8}} 0)")
    a('\\t\\t\\t(layer "F.SilkS")')
    a("\\t\\t\\t(effects (font (size 0.9 0.9) (thickness 0.12)))")
    a(f'\\t\\t\\t(uuid "{uid()}")')
    a("\\t\\t)")
    a(f'\\t\\t(property "Value" "JST-XH{n}_to_{mate}"')
    a(f"\\t\\t\\t(at 0 {{span + 2.8}} 0)")
    a('\\t\\t\\t(layer "F.Fab")')
    a("\\t\\t\\t(effects (font (size 0.7 0.7) (thickness 0.1)))")
    a(f'\\t\\t\\t(uuid "{uid()}")')
    a("\\t\\t)")
    a("\\t\\t(attr through_hole)")
    a("\\t\\t(fp_rect")
    a("\\t\\t\\t(start -3.0 -1.8)")
    a(f"\\t\\t\\t(end 3.0 {{span + 1.8}})")
    a('\\t\\t\\t(stroke (width 0.12) (type solid))')
    a("\\t\\t\\t(fill none)")
    a('\\t\\t\\t(layer "F.SilkS")')
    a(f'\\t\\t\\t(uuid "{uid()}")')
    a("\\t\\t)")
    a("\\t\\t(fp_line (start -3.0 -0.5) (end -4.0 0)")
    a('\\t\\t\\t(stroke (width 0.15) (type solid)) (layer "F.SilkS")')
    a(f'\\t\\t\\t(uuid "{uid()}")')
    a("\\t\\t)")
    for i, (lab, (ni, nn)) in enumerate(zip(labels, nets)):
        yi = i * XH_PITCH
        a(f'\\t\\t(fp_text user "{{lab}}"')
        a(f"\\t\\t\\t(at 3.5 {{yi}} 0)")
        a('\\t\\t\\t(layer "F.SilkS")')
        a('\\t\\t\\t(effects (font (size 0.65 0.65) (thickness 0.1)) (justify left))')
        a(f'\\t\\t\\t(uuid "{{uid()}}")')
        a("\\t\\t)")
        shape = "rect" if i == 0 else "circle"
        a(f'\\t\\t(pad "{{i + 1}}" thru_hole {{shape}}')
        a(f"\\t\\t\\t(at 0 {{yi}})")
        a("\\t\\t\\t(size 1.6 1.6)")
        a("\\t\\t\\t(drill 0.9)")
        a('\\t\\t\\t(layers "*.Cu" "*.Mask")')
        a(f'\\t\\t\\t(net {{ni}} "{{nn}}")')
        a(f'\\t\\t\\t(uuid "{{uid()}}")')
        a("\\t\\t)")
    a("\\t)")''',
        "hdr_male_xh generic",
    )

    # Rewrite M2 header section (P1 XH6 + P2 XH5)
    old_m2_hdr = '''    _silk(a, "M2 OPTO4", ox + 1.5, oy + 2.0, 1.0)
    _silk(a, "J31 pin1=IN1 KEY — use KF2510 housing", ox + 1.5, oy + h - 1.5, 0.6)
    hx, hy = ox + 4.0, oy + 4.0
    labs = [
        "IN1", "IN2", "IN3", "IN4", "SNS", "GND",
        "OUT1", "OUT2", "OUT3", "OUT4", "3V3",
    ]
    hdr_nets = [
        (1, "OPTO_IN1"), (2, "OPTO_IN2"), (3, "OPTO_IN3"), (4, "OPTO_IN4"),
        (5, "+12V_SNS"), (6, "GND"),
        (7, "OPTO_OUT1"), (8, "OPTO_OUT2"), (9, "OPTO_OUT3"), (10, "OPTO_OUT4"),
        (11, "+3V3"),
    ]
    _hdr_male(a, "P1", 11, labs, hx, hy, hdr_nets)'''

    new_m2_hdr = '''    _silk(a, "M2 OPTO4", ox + 1.5, oy + 2.0, 1.0)
    _silk(a, "P1→J31A XH6  P2→J31B XH5 KEYED", ox + 1.5, oy + h - 1.5, 0.55)
    hx, hy = ox + 4.0, oy + 4.0
    _hdr_male_xh(
        a, "P1",
        ["IN1", "IN2", "IN3", "IN4", "SNS", "GND"],
        hx, hy,
        [
            (1, "OPTO_IN1"), (2, "OPTO_IN2"), (3, "OPTO_IN3"), (4, "OPTO_IN4"),
            (5, "+12V_SNS"), (6, "GND"),
        ],
        mate="J31A",
    )
    hx2 = hx + 10.0
    _hdr_male_xh(
        a, "P2",
        ["OUT1", "OUT2", "OUT3", "OUT4", "3V3"],
        hx2, hy,
        [
            (7, "OPTO_OUT1"), (8, "OPTO_OUT2"), (9, "OPTO_OUT3"), (10, "OPTO_OUT4"),
            (11, "+3V3"),
        ],
        mate="J31B",
    )'''
    t = _replace_once(t, old_m2_hdr, new_m2_hdr, "M2 dual XH")

    t = t.replace(
        "**J31 / M2 P1 (1×11):** 1–4=`OPTO_INx` 5=`+12V_SNS` 6=`GND` 7–10=`OPTO_OUTx` 11=`+3V3`",
        "**J31A / M2 P1 (XH-6):** 1–4=`OPTO_INx` 5=`+12V_SNS` 6=`GND`  \n"
        "**J31B / M2 P2 (XH-5):** 1–4=`OPTO_OUTx` 5=`+3V3`",
    )
    t = t.replace(
        "  J31 1×11 Opto4      (female on carrier)",
        "  J31A XH-6 + J31B XH-5 Opto4 (female on carrier)",
    )
    return t


def main() -> None:
    c = CARRIER.read_text(encoding="utf-8")
    c2 = patch_carrier(c)
    CARRIER.write_text(c2, encoding="utf-8")
    print("OK", CARRIER.name)

    s = SUB.read_text(encoding="utf-8")
    s2 = patch_submodules(s)
    SUB.write_text(s2, encoding="utf-8")
    print("OK", SUB.name)


if __name__ == "__main__":
    main()
