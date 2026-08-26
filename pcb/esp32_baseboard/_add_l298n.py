#!/usr/bin/env python3
"""Add 3x L298N (bottom) + 3x 2-pin motor jacks (top) for GA12-N20 @ 12V."""
from __future__ import annotations

from pathlib import Path

GEN = Path(__file__).resolve().parent / "gen_power_carrier.py"
HERE = Path(__file__).resolve().parent

CONST = '''
# L298N green module ~43x43 mm (Shopee) — one GA12-N20 per module on channel A
# ENA left jumpered on module (full enable); ESP32 drives IN1/IN2 only
L298N_W = 43.0
L298N_H = 43.0
# (ref_suffix, IN1_gpio, IN2_gpio, mot_net_a, mot_net_b)
L298N_MOTORS = [
    ("5", 21, 22, 34, 35),  # U5 / J5  IO21 IO22
    ("6", 23, 13, 36, 37),  # U6 / J6  IO23 IO13
    ("7", 12, 14, 38, 39),  # U7 / J7  IO12 IO14
]
'''

FP = r'''
def write_l298n_footprint() -> Path:
    """THT landing for L298N green module (channel A + power). VERIFY pitch."""
    pads = [
        ("1", "Vs", -8.0, -16.0),
        ("2", "GND", 0.0, -16.0),
        ("3", "5V", 8.0, -16.0),
        ("4", "ENA", -18.0, -6.0),
        ("5", "IN1", -18.0, 0.0),
        ("6", "IN2", -18.0, 6.0),
        ("7", "OUT1", 18.0, -4.0),
        ("8", "OUT2", 18.0, 4.0),
    ]
    lines: list[str] = []
    a = lines.append
    a('(footprint "L298N_Module"')
    a("\t(version 20260206)")
    a('\t(generator "gen_power_carrier.py")')
    a('\t(generator_version "1.0")')
    a('\t(layer "F.Cu")')
    a('\t(descr "L298N dual H-bridge module ~43x43mm. Channel A for GA12-N20. Verify Shopee module.")')
    a('\t(tags "L298N DC motor driver GA12-N20")')
    a('\t(property "Reference" "U**"')
    a(f'\t\t(at 0 {-L298N_H / 2 - 1.8} 0)')
    a('\t\t(layer "F.SilkS")')
    a("\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a("\t)")
    a('\t(property "Value" "L298N_Module"')
    a(f'\t\t(at 0 {L298N_H / 2 + 1.8} 0)')
    a('\t\t(layer "F.Fab")')
    a("\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a("\t)")
    a("\t(attr through_hole)")
    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
        a("\t(fp_rect")
        a(f"\t\t(start {-L298N_W / 2} {-L298N_H / 2})")
        a(f"\t\t(end {L298N_W / 2} {L298N_H / 2})")
        a(f"\t\t(stroke (width {w}) (type solid))")
        a("\t\t(fill none)")
        a(f'\t\t(layer "{layer}")')
        a("\t)")
    a('\t(fp_text user "L298N"')
    a("\t\t(at 0 0 0)")
    a('\t\t(layer "F.SilkS")')
    a('\t\t(effects (font (size 1.2 1.2) (thickness 0.15)))')
    a("\t)")
    a('\t(fp_text user "ENA=JMP"')
    a("\t\t(at -10 12 0)")
    a('\t\t(layer "F.SilkS")')
    a('\t\t(effects (font (size 0.7 0.7) (thickness 0.1)))')
    a("\t)")
    for i, (num, name, x, y) in enumerate(pads):
        a(f'\t(fp_text user "{name}"')
        a(f"\t\t(at {x} {y - 2.2} 0)")
        a('\t\t(layer "F.SilkS")')
        a('\t\t(effects (font (size 0.7 0.7) (thickness 0.1)))')
        a("\t)")
        shape = "rect" if i == 0 else "circle"
        a(f'\t(pad "{num}" thru_hole {shape}')
        a(f"\t\t(at {x} {y})")
        a("\t\t(size 2.0 2.0)")
        a("\t\t(drill 1.1)")
        a('\t\t(layers "*.Cu" "*.Mask")')
        a("\t)")
    a(")")
    out = PRETTY / "L298N_Module.kicad_mod"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


'''

SYM = r'''
    # --- L298N (channel A) ---
    a('\t(symbol "L298N_Module"')
    a("\t\t(exclude_from_sim no)")
    a("\t\t(in_bom yes)")
    a("\t\t(on_board yes)")
    a("\t\t(in_pos_files yes)")
    a('\t\t(property "Reference" "U"')
    a("\t\t\t(at 0 12.7 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Value" "L298N_Module"')
    a("\t\t\t(at 0 -12.7 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Footprint" "ESP32_Carrier:L298N_Module"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Description" "L298N for GA12-N20 @12V (ENA jumper)"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(symbol "L298N_Module_0_1"')
    a("\t\t\t(rectangle")
    a("\t\t\t\t(start -10.16 10.16)")
    a("\t\t\t\t(end 10.16 -10.16)")
    a("\t\t\t\t(stroke (width 0.254) (type default))")
    a("\t\t\t\t(fill (type background))")
    a("\t\t\t)")
    a('\t\t\t(text "L298N"')
    a("\t\t\t\t(at 0 0 0)")
    a("\t\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t\t)")
    a("\t\t)")
    a('\t\t(symbol "L298N_Module_1_1"')
    for num, name, etype, x, y, rot in [
        ("1", "Vs", "power_in", -15.24, 7.62, 0),
        ("2", "GND", "passive", -15.24, 2.54, 0),
        ("3", "5V", "passive", -15.24, -2.54, 0),
        ("5", "IN1", "input", -15.24, -7.62, 0),
        ("6", "IN2", "input", 15.24, -7.62, 180),
        ("7", "OUT1", "passive", 15.24, 5.08, 180),
        ("8", "OUT2", "passive", 15.24, 0.0, 180),
        ("4", "ENA", "input", 15.24, -5.08, 180),
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

'''


def main() -> None:
    text = GEN.read_text(encoding="utf-8")

    if "L298N_W" not in text:
        anchor = '    ("10", "IN8"),\n]\n'
        if anchor not in text:
            raise SystemExit("OPTO_FIELD end missing")
        text = text.replace(anchor, anchor + "\n" + CONST, 1)

    if "def write_l298n_footprint" not in text:
        text = text.replace(
            "def write_mini560_footprint() -> Path:",
            FP + "def write_mini560_footprint() -> Path:",
            1,
        )

    if 'symbol "L298N_Module"' not in text:
        marker = "    # --- PC817 8CH opto"
        if marker not in text:
            raise SystemExit("PC817 symbol marker missing")
        text = text.replace(marker, SYM + marker, 1)

    if "write_l298n_footprint()" not in text:
        text = text.replace(
            "write_pc817_8ch_footprint(),",
            "write_pc817_8ch_footprint(),\n"
            "        write_l298n_footprint(),\n"
            '        write_pin_header_footprint(2, "PinHeader_1x02_MotorDC", ["M+", "M-"]),',
            1,
        )

    if '_embed_from_lib("L298N_Module")' not in text:
        text = text.replace(
            '_embed_from_lib("Conn_1x10_OptoField"),',
            '_embed_from_lib("Conn_1x10_OptoField"),\n'
            '            _embed_from_lib("L298N_Module"),\n'
            '            _embed_from_lib("Conn_1x02_MotorDC"),',
            1,
        )

    # paper A2 + title
    text = text.replace('\t(paper "A3")', '\t(paper "A2")', 1)
    text = text.replace(
        'ESP32 Baseboard - Mini560 + TMC2209 NEMA17',
        'ESP32 Baseboard - Mini560 + TMC + Opto + 3x L298N',
        1,
    )
    text = text.replace(
        'BOTTOM: J1 U2 U3 U1 | TOP: J2 NEMA17 J3 sensor',
        'BOTTOM: J1 U2 U3 U4 U5-7 U1 | TOP: J2 J3 J4 J5-7',
        1,
    )

    if "L298N U5" not in text and 'reference "U5"' not in text and "ref_u, ref_j, xu, yu" not in text:
        sch = (HERE / "_l298n_sch.txt").read_text(encoding="utf-8")
        # fix jack pin coords to match Conn_1x02 (local y +/- 1.27)
        sch = sch.replace("jmp = (xj, yj - 2.54)  # M+", "jmp = (xj, yj - 1.27)  # M+")
        sch = sch.replace("jmm = (xj, yj + 2.54)  # M-", "jmm = (xj, yj + 1.27)  # M-")
        marker = "    used = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 16, 17, 21, 22, 23, 24, 25, 26, 27}"
        if marker not in text:
            raise SystemExit("used marker missing")
        text = text.replace(
            marker,
            sch
            + "\n    used = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27}",
            1,
        )

    if "/MotDC1_A" not in text:
        text = text.replace(
            '        33: "/OPTO_GND_I",\n    }',
            '        33: "/OPTO_GND_I",\n'
            '        34: "/MotDC1_A",\n'
            '        35: "/MotDC1_B",\n'
            '        36: "/MotDC2_A",\n'
            '        37: "/MotDC2_B",\n'
            '        38: "/MotDC3_A",\n'
            '        39: "/MotDC3_B",\n'
            '        40: "/DC1_IN1",\n'
            '        41: "/DC1_IN2",\n'
            '        42: "/DC2_IN1",\n'
            '        43: "/DC2_IN2",\n'
            '        44: "/DC3_IN1",\n'
            '        45: "/DC3_IN2",\n'
            "    }",
            1,
        )

    if '"IO21": (40' not in text:
        text = text.replace(
            '"IO19": (23, "/OPTO_OUT8"),\n        }',
            '"IO19": (23, "/OPTO_OUT8"),\n'
            '            "IO21": (40, "/DC1_IN1"),\n'
            '            "IO22": (41, "/DC1_IN2"),\n'
            '            "IO23": (42, "/DC2_IN1"),\n'
            '            "IO13": (43, "/DC2_IN2"),\n'
            '            "IO12": (44, "/DC3_IN1"),\n'
            '            "IO14": (45, "/DC3_IN2"),\n'
            "        }",
            1,
        )

    # power net class motor DC
    if '"/MotDC1_A"' not in text:
        text = text.replace(
            "    a('\\t\\t(add_net \"/MotB2\")')\n    a(\"\\t)\")",
            "    a('\\t\\t(add_net \"/MotB2\")')\n"
            "    a('\\t\\t(add_net \"/MotDC1_A\")')\n"
            "    a('\\t\\t(add_net \"/MotDC1_B\")')\n"
            "    a('\\t\\t(add_net \"/MotDC2_A\")')\n"
            "    a('\\t\\t(add_net \"/MotDC2_B\")')\n"
            "    a('\\t\\t(add_net \"/MotDC3_A\")')\n"
            "    a('\\t\\t(add_net \"/MotDC3_B\")')\n"
            '    a("\\t)")',
            1,
        )
        # fallback raw string style in file
        if '"/MotDC1_A"' not in text:
            text = text.replace(
                "a('\\t\\t(add_net \"/MotB2\")')\n    a(\"\\t)\")",
                "FAIL",
                1,
            )
            # try exact file content
            old = '    a(\'\\t\\t(add_net "/MotB2")\')\n    a("\\t)")'
            # Actual file uses double quotes differently
            old2 = '''    a('\\t\\t(add_net "/MotB2")')
    a("\\t)")'''
            # Read exact lines around MotB2
            pass

    # board size
    text = text.replace("bw, bh = 130.0, 145.0", "bw, bh = 175.0, 175.0", 1)

    # top silk
    if "J5/J6/J7" not in text:
        text = text.replace(
            'gr_text("MAT TREN / TOP - NEMA17 & CAM BIEN", ox + 60, oy + 4.5, "F.SilkS", 1.0)',
            'gr_text("MAT TREN / TOP - NEMA17 SENSOR OPTO GA12", ox + 70, oy + 4.5, "F.SilkS", 1.0)',
            1,
        )

    if "U5 L298N" not in text and "l298n_pcb" not in text:
        pcb = (HERE / "_l298n_pcb.txt").read_text(encoding="utf-8")
        marker = (
            '    track(u1_gnd_l[0], u4_gndo[1], u1_gnd_l[0], u1_gnd_l[1], 2, "B.Cu", 0.5)\n\n'
            '    a(")")'
        )
        if marker not in text:
            raise SystemExit("pcb insert marker missing")
        text = text.replace(
            marker,
            '    track(u1_gnd_l[0], u4_gndo[1], u1_gnd_l[0], u1_gnd_l[1], 2, "B.Cu", 0.5)\n'
            + pcb
            + '\n    a(")")',
            1,
        )

    # readme
    if "3x L298N" not in text[text.find("def write_readme") : text.find("def write_project")]:
        text = text.replace(
            "# ESP32 Baseboard - Mini560 + TMC2209 + PC817 Opto8",
            "# ESP32 Baseboard - Mini560 + TMC2209 + PC817 + 3x L298N",
            1,
        )
        text = text.replace(
            "| **Bottom** | J1 12V, U2 Mini560, U3 TMC2209, **U4 PC817 8ch**, U1 ESP32 |\n"
            "| **Top** | J2 NEMA17, J3 sensor, **J4 OPTO field IN** |",
            "| **Bottom** | J1, U2 Mini560, U3 TMC2209, U4 PC817, **U5/U6/U7 L298N**, U1 ESP32 |\n"
            "| **Top** | J2 NEMA17, J3 sensor, J4 OPTO, **J5/J6/J7 GA12-N20** |",
            1,
        )
        insert_doc = '''
## 3x L298N + GA12-N20 (12V)

Module: [Shopee L298N](https://shopee.vn/Module-%C4%90i%E1%BB%81u-Khi%E1%BB%83n-%C4%90%E1%BB%99ng-C%C6%A1-L298N-xanh-l%C3%A1-i.951399259.23780828147)

| Driver | Motor jack (TOP) | ESP32 IN1/IN2 | Power |
|--------|------------------|---------------|-------|
| U5 | J5 M+/M- | IO21 / IO22 | Vs=+12V |
| U6 | J6 M+/M- | IO23 / IO13 | Vs=+12V |
| U7 | J7 M+/M- | IO12 / IO14 | Vs=+12V |

ENA: de jumper tren module (full enable). Moi L298N dung channel A (OUT1/OUT2).
GA12-N20: 1 dong co / jack 2 chan mat tren.

'''
        text = text.replace(
            "**Do module that truoc khi fab** (pitch/kich thuoc ~100x28mm).",
            "**Do module that truoc khi fab** (pitch/kich thuoc ~100x28mm)." + insert_doc,
            1,
        )

    GEN.write_text(text, encoding="utf-8")
    print("L298N patch applied to", GEN)

    # verify MotB2 net class insert
    t2 = GEN.read_text(encoding="utf-8")
    if "/MotDC1_A" not in t2.split("net_class")[2] if "net_class" in t2 else True:
        # find MotB2 add_net line
        idx = t2.find('add_net "/MotB2"')
        if idx > 0 and 'add_net "/MotDC1_A"' not in t2[idx : idx + 400]:
            old = '    a(\'\\t\\t(add_net "/MotB2")\')\n    a("\\t)")'
            # Actual content in file:
            snippet = t2[idx - 20 : idx + 80]
            print("DEBUG MotB2 context:", repr(snippet))
            new_block = (
                'a(\'\\t\\t(add_net "/MotB2")\')\n'
                "    a('\\t\\t(add_net \"/MotDC1_A\")')\n"
                "    a('\\t\\t(add_net \"/MotDC1_B\")')\n"
                "    a('\\t\\t(add_net \"/MotDC2_A\")')\n"
                "    a('\\t\\t(add_net \"/MotDC2_B\")')\n"
                "    a('\\t\\t(add_net \"/MotDC3_A\")')\n"
                "    a('\\t\\t(add_net \"/MotDC3_B\")')\n"
                '    a("\\t)")'
            )
            # try common patterns
            for old_try in [
                '    a(\'\\t\\t(add_net "/MotB2")\')\n    a("\\t)")',
                "    a('\\t\\t(add_net \"/MotB2\")')\n    a(\"\\t)\")",
            ]:
                if old_try in t2:
                    t2 = t2.replace(old_try, "    " + new_block if not new_block.startswith("a") else "    " + new_block, 1)
                    GEN.write_text(t2, encoding="utf-8")
                    print("net_class MotDC patched")
                    break
            else:
                # line-based
                lines = t2.splitlines(keepends=True)
                out = []
                for line in lines:
                    out.append(line)
                    if 'add_net "/MotB2"' in line and "/MotDC1_A" not in "".join(out[-5:]):
                        out.append("    a('\\t\\t(add_net \"/MotDC1_A\")')\n")
                        out.append("    a('\\t\\t(add_net \"/MotDC1_B\")')\n")
                        out.append("    a('\\t\\t(add_net \"/MotDC2_A\")')\n")
                        out.append("    a('\\t\\t(add_net \"/MotDC2_B\")')\n")
                        out.append("    a('\\t\\t(add_net \"/MotDC3_A\")')\n")
                        out.append("    a('\\t\\t(add_net \"/MotDC3_B\")')\n")
                GEN.write_text("".join(out), encoding="utf-8")
                print("net_class MotDC patched (line insert)")


if __name__ == "__main__":
    main()
