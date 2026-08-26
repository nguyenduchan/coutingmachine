#!/usr/bin/env python3
"""Star-topology 12V isolation: MOT vs SNS branches, bulk caps, RC filter."""
from __future__ import annotations

from pathlib import Path

GEN = Path(__file__).resolve().parent / "gen_power_carrier.py"


def main() -> None:
    t = GEN.read_text(encoding="utf-8")

    # --- nets ---
    if '"+12V_SNS"' not in t.split("nets = {")[1][:800]:
        t = t.replace(
            '        45: "/DC3_IN2",\n    }',
            '        45: "/DC3_IN2",\n'
            '        46: "+12V_SNS",\n'
            "    }",
            1,
        )

    # net class
    if 'add_net "+12V_SNS"' not in t:
        t = t.replace(
            "    a('\\t\\t(add_net \"+12V\")')\n",
            "    a('\\t\\t(add_net \"+12V\")')\n"
            "    a('\\t\\t(add_net \"+12V_SNS\")')\n",
            1,
        )

    # --- footprints for filter + bulk ---
    if "def write_star_power_passives" not in t:
        fp = r'''
def write_star_power_passives() -> list[Path]:
    """Bulk 470u, SNS 47u, 100nF, 10R 1206 for star-power isolation."""
    outs: list[Path] = []

    def _radial(name: str, d: float, pitch: float, descr: str) -> Path:
        lines: list[str] = []
        a = lines.append
        a(f'(footprint "{name}"')
        a("\t(version 20260206)")
        a('\t(generator "gen_power_carrier.py")')
        a('\t(layer "F.Cu")')
        a(f'\t(descr "{descr}")')
        a('\t(property "Reference" "C**" (at 0 -{:.1f} 0)'.format(d / 2 + 1.5))
        a('\t\t(layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))')
        a(f'\t(property "Value" "{name}" (at 0 {d / 2 + 1.5} 0)')
        a('\t\t(layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))')
        a("\t(attr through_hole)")
        a(f"\t(fp_circle (center 0 0) (end {d / 2} 0) (stroke (width 0.12) (type solid)) (fill none) (layer \"F.SilkS\"))")
        a(f'\t(pad "1" thru_hole rect (at {-pitch / 2} 0) (size 1.8 1.8) (drill 0.9) (layers "*.Cu" "*.Mask"))')
        a(f'\t(pad "2" thru_hole circle (at {pitch / 2} 0) (size 1.8 1.8) (drill 0.9) (layers "*.Cu" "*.Mask"))')
        a(")")
        out = PRETTY / f"{name}.kicad_mod"
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return out

    outs.append(_radial("CP_Radial_D8_470u_25V", 8.0, 3.5, "470uF 25V bulk near motor driver"))
    outs.append(_radial("CP_Radial_D6_47u_25V", 6.3, 2.5, "47uF 25V SNS rail"))

    # 100nF 0805
    lines = []
    a = lines.append
    a('(footprint "C_0805_100n"')
    a("\t(version 20260206)")
    a('\t(generator "gen_power_carrier.py")')
    a('\t(layer "F.Cu")')
    a('\t(descr "100nF 0805 ceramic")')
    a('\t(property "Reference" "C**" (at 0 -1.8 0) (layer "F.SilkS") (effects (font (size 0.7 0.7) (thickness 0.1))))')
    a('\t(property "Value" "100n" (at 0 1.8 0) (layer "F.Fab") (effects (font (size 0.7 0.7) (thickness 0.1))))')
    a("\t(attr smd)")
    a('\t(fp_rect (start -1.1 -0.7) (end 1.1 0.7) (stroke (width 0.1) (type solid)) (fill none) (layer "F.CrtYd"))')
    a('\t(pad "1" smd roundrect (at -0.95 0) (size 0.8 1.2) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))')
    a('\t(pad "2" smd roundrect (at 0.95 0) (size 0.8 1.2) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))')
    a(")")
    p = PRETTY / "C_0805_100n.kicad_mod"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    outs.append(p)

    # 10R 1206
    lines = []
    a = lines.append
    a('(footprint "R_1206_10R"')
    a("\t(version 20260206)")
    a('\t(generator "gen_power_carrier.py")')
    a('\t(layer "F.Cu")')
    a('\t(descr "10 ohm 1206 series SNS filter")')
    a('\t(property "Reference" "R**" (at 0 -1.8 0) (layer "F.SilkS") (effects (font (size 0.7 0.7) (thickness 0.1))))')
    a('\t(property "Value" "10R" (at 0 1.8 0) (layer "F.Fab") (effects (font (size 0.7 0.7) (thickness 0.1))))')
    a("\t(attr smd)")
    a('\t(fp_rect (start -1.7 -0.9) (end 1.7 0.9) (stroke (width 0.1) (type solid)) (fill none) (layer "F.CrtYd"))')
    a('\t(pad "1" smd roundrect (at -1.4 0) (size 1.0 1.5) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))')
    a('\t(pad "2" smd roundrect (at 1.4 0) (size 1.0 1.5) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))')
    a(")")
    p = PRETTY / "R_1206_10R.kicad_mod"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    outs.append(p)
    return outs


'''
        # Fix f-string issues in the radial helper - I used broken format. Rewrite cleaner.
        fp = '''
def write_star_power_passives() -> list:
    """Bulk 470u, SNS 47u, 100nF 0805, 10R 1206."""
    outs = []

    def _radial(name: str, d: float, pitch: float, descr: str):
        r = d / 2
        lines = [
            f'(footprint "{name}"',
            "\t(version 20260206)",
            '\t(generator "gen_power_carrier.py")',
            '\t(layer "F.Cu")',
            f'\t(descr "{descr}")',
            f'\t(property "Reference" "C**" (at 0 {-r - 1.5} 0)',
            '\t\t(layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))',
            f'\t(property "Value" "{name}" (at 0 {r + 1.5} 0)',
            '\t\t(layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))',
            "\t(attr through_hole)",
            f'\t(fp_circle (center 0 0) (end {r} 0) (stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))',
            f'\t(pad "1" thru_hole rect (at {-pitch / 2} 0) (size 1.8 1.8) (drill 0.9) (layers "*.Cu" "*.Mask"))',
            f'\t(pad "2" thru_hole circle (at {pitch / 2} 0) (size 1.8 1.8) (drill 0.9) (layers "*.Cu" "*.Mask"))',
            ")",
        ]
        out = PRETTY / f"{name}.kicad_mod"
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return out

    outs.append(_radial("CP_Radial_D8_470u_25V", 8.0, 3.5, "470uF 25V bulk near motor driver"))
    outs.append(_radial("CP_Radial_D6_47u_25V", 6.3, 2.5, "47uF 25V SNS rail"))

    c0805 = """(footprint "C_0805_100n"
\t(version 20260206)
\t(generator "gen_power_carrier.py")
\t(layer "F.Cu")
\t(descr "100nF 0805")
\t(property "Reference" "C**" (at 0 -1.8 0) (layer "F.SilkS") (effects (font (size 0.7 0.7) (thickness 0.1))))
\t(property "Value" "100n" (at 0 1.8 0) (layer "F.Fab") (effects (font (size 0.7 0.7) (thickness 0.1))))
\t(attr smd)
\t(fp_rect (start -1.1 -0.7) (end 1.1 0.7) (stroke (width 0.1) (type solid)) (fill none) (layer "F.CrtYd"))
\t(pad "1" smd roundrect (at -0.95 0) (size 0.8 1.2) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))
\t(pad "2" smd roundrect (at 0.95 0) (size 0.8 1.2) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))
)
"""
    p = PRETTY / "C_0805_100n.kicad_mod"
    p.write_text(c0805, encoding="utf-8")
    outs.append(p)

    r1206 = """(footprint "R_1206_10R"
\t(version 20260206)
\t(generator "gen_power_carrier.py")
\t(layer "F.Cu")
\t(descr "10 ohm 1206 SNS series filter")
\t(property "Reference" "R**" (at 0 -1.8 0) (layer "F.SilkS") (effects (font (size 0.7 0.7) (thickness 0.1))))
\t(property "Value" "10R" (at 0 1.8 0) (layer "F.Fab") (effects (font (size 0.7 0.7) (thickness 0.1))))
\t(attr smd)
\t(fp_rect (start -1.7 -0.9) (end 1.7 0.9) (stroke (width 0.1) (type solid)) (fill none) (layer "F.CrtYd"))
\t(pad "1" smd roundrect (at -1.4 0) (size 1.0 1.5) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))
\t(pad "2" smd roundrect (at 1.4 0) (size 1.0 1.5) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))
)
"""
    p = PRETTY / "R_1206_10R.kicad_mod"
    p.write_text(r1206, encoding="utf-8")
    outs.append(p)
    return outs


'''
        t = t.replace(
            "def write_l298n_footprint() -> Path:",
            fp + "def write_l298n_footprint() -> Path:",
            1,
        )

    if "write_star_power_passives()" not in t[t.find("def main") :]:
        t = t.replace(
            "        write_r_axial_4k7_bup(),",
            "        write_r_axial_4k7_bup(),\n"
            "        *write_star_power_passives(),",
            1,
        )

    # --- Change sensor +12V labels to +12V_SNS in schematic ---
    # Limit SW labels
    t = t.replace(
        '            parts.append(label("+12V", p12[0], p12[1] - 2.54))',
        '            parts.append(label("+12V_SNS", p12[0], p12[1] - 2.54))',
        1,
    )
    # BUP J14 / R1 (BUP pullup stays on SNS)
    t = t.replace(
        '    parts.append(label("+12V", j14_12[0] - 5.08, j14_12[1]))\n'
        '    parts += wire_path(j14_gnd, (j14_gnd[0] - 5.08, j14_gnd[1]))\n'
        '    parts.append(label("GND", j14_gnd[0] - 5.08, j14_gnd[1]))\n'
        '    parts += wire_path(j14_out, (j14_out[0] + 5.08, j14_out[1]))\n'
        '    parts.append(label("OPTO_IN7", j14_out[0] + 5.08, j14_out[1]))\n'
        '    parts += wire_path(r1_a, (r1_a[0], r1_a[1] - 2.54))\n'
        '    parts.append(label("+12V", r1_a[0], r1_a[1] - 2.54))',
        '    parts.append(label("+12V_SNS", j14_12[0] - 5.08, j14_12[1]))\n'
        '    parts += wire_path(j14_gnd, (j14_gnd[0] - 5.08, j14_gnd[1]))\n'
        '    parts.append(label("GND", j14_gnd[0] - 5.08, j14_gnd[1]))\n'
        '    parts += wire_path(j14_out, (j14_out[0] + 5.08, j14_out[1]))\n'
        '    parts.append(label("OPTO_IN7", j14_out[0] + 5.08, j14_out[1]))\n'
        '    parts += wire_path(r1_a, (r1_a[0], r1_a[1] - 2.54))\n'
        '    parts.append(label("+12V_SNS", r1_a[0], r1_a[1] - 2.54))',
        1,
    )

    # Schematic filter block before used=
    if "STAR POWER FILTER" not in t:
        filt = r'''
    # --- STAR POWER: RC filter +12V -> +12V_SNS ---
    parts.append(text("STAR: +12V_MOT (rong) / +12V_SNS qua R10=10R + C47u||100n", 20.32, 304.8, 1.0))
    # Net labels only: document filter (R10 C_SNS placed on PCB)
    parts.append(label("+12V", 38.1, 312.42))
    parts.append(label("+12V_SNS", 63.5, 312.42))
    parts.append(text("R10 10R + C10 47u + C11 100n (tren PCB)", 38.1, 317.5, 1.0))
    parts.append(text("Bulk 470u tai moi L298N/TMC (tren PCB)", 38.1, 322.58, 1.0))

'''
        marker = "    used = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27}"
        if marker not in t:
            raise SystemExit("used marker missing")
        t = t.replace(marker, filt + marker, 1)

    # --- PCB: limit/BUP +12V use net 46; rewrite star routes ---
    t = t.replace(
        '            [(1, "+12V", "+12"), (nmin, f"/OPTO_IN{2 * mi + 1}", "SW")],',
        '            [(46, "+12V_SNS", "+12S"), (nmin, f"/OPTO_IN{2 * mi + 1}", "SW")],',
        1,
    )
    t = t.replace(
        '            [(1, "+12V", "+12"), (nmax, f"/OPTO_IN{2 * mi + 2}", "SW")],',
        '            [(46, "+12V_SNS", "+12S"), (nmax, f"/OPTO_IN{2 * mi + 2}", "SW")],',
        1,
    )
    # BUP jack +12V and R1 pullup
    t = t.replace(
        '        (1, "+12V", 1, "+12V"),\n'
        '        (2, "GND", 2, "GND"),\n'
        '        (3, "OUT", 31, "/OPTO_IN7"),',
        '        (1, "+12V", 46, "+12V_SNS"),\n'
        '        (2, "GND", 2, "GND"),\n'
        '        (3, "OUT", 31, "/OPTO_IN7"),',
        1,
    )
    t = t.replace(
        '    a(\'\\t\\t\\t(net 1 "+12V")\')\n'
        '    a(f\'\\t\\t\\t(uuid "{uid()}")\')\n'
        '    a("\\t\\t)")\n'
        '    a(\'\\t\\t(pad "2" thru_hole circle\')\n'
        '    a("\\t\\t\\t(at 3.75 0)")\n'
        '    a("\\t\\t\\t(size 1.6 1.6)")\n'
        '    a("\\t\\t\\t(drill 0.8)")\n'
        '    a(\'\\t\\t\\t(layers "*.Cu" "*.Mask")\')\n'
        '    a(\'\\t\\t\\t(net 31 "/OPTO_IN7")\')',
        '    a(\'\\t\\t\\t(net 46 "+12V_SNS")\')\n'
        '    a(f\'\\t\\t\\t(uuid "{uid()}")\')\n'
        '    a("\\t\\t)")\n'
        '    a(\'\\t\\t(pad "2" thru_hole circle\')\n'
        '    a("\\t\\t\\t(at 3.75 0)")\n'
        '    a("\\t\\t\\t(size 1.6 1.6)")\n'
        '    a("\\t\\t\\t(drill 0.8)")\n'
        '    a(\'\\t\\t\\t(layers "*.Cu" "*.Mask")\')\n'
        '    a(\'\\t\\t\\t(net 31 "/OPTO_IN7")\')',
        1,
    )

    # Limit power tracks currently use net 1 to t_vm - change to SNS star (net 46) later in PCB block

    # Insert star power PCB block before final a(")") of write_pcb — replace old via farm / motor power stitching
    if "STAR POWER ISOLATION" not in t:
        star = r'''
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
        ("C21", ox + 148.0 - 28, oy + 50.0, "U5"),
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

'''
        # Insert before final a(")") of pcb — but AFTER l298n/BUP so j14x and l298n_pcb exist
        marker = '    a(")")\n    out = ROOT / "esp32_baseboard.kicad_pcb"'
        if marker not in t:
            raise SystemExit("pcb end missing")
        t = t.replace(marker, star + "\n" + marker, 1)

    # Fix limit group power feed: was net 1 to t_vm — change those tracks to SNS
    # The loop uses net 1 for p12 to oy+22 to t_vm — replace with sns rail
    old_lim_pwr = '''            track(p12[0], p12[1], p12[0], oy + 22.0, 1, "F.Cu", 0.5)
            track(p12[0], oy + 22.0, t_vm[0], oy + 22.0, 1, "F.Cu", 0.5)
            via(t_vm[0], oy + 22.0, 1, 0.4, 0.8)'''
    new_lim_pwr = '''            # +12V_SNS from star SNS rail (not motor bus)
            track(p12[0], p12[1], sns_x if "sns_x" in dir() else (ox + 30), p12[1], 46, "F.Cu", 0.5)'''
    # sns_x is defined AFTER the l298n loop in star block — order problem!
    # Star block is AFTER l298n, so limit tracks still use old motor feed.
    # Better: remove old limit +12V tracks to motor (they'll get SNS from star block loop)
    if old_lim_pwr in t:
        t = t.replace(old_lim_pwr, "            pass  # +12V_SNS fed from star SNS rail below", 1)

    # BUP tracks that pull +12V from t_vm — remove / replace
    old_bup = '''    track(p12[0], p12[1], p12[0] - 4, p12[1], 1, "F.Cu", 0.5)
    track(p12[0] - 4, p12[1], p12[0] - 4, oy + 22.0, 1, "F.Cu", 0.5)
    track(p12[0] - 4, oy + 22.0, t_vm[0], oy + 22.0, 1, "F.Cu", 0.5)'''
    if old_bup in t:
        t = t.replace(old_bup, "    # BUP +12V_SNS from star rail (see STAR block)", 1)

    # L298N Vs still tracks to t_vm on net 1 — good for MOT star

    # README
    if "STAR POWER" not in t[t.find("def write_readme") : t.find("def write_project")]:
        doc = '''
## STAR POWER Isolation (chong nhieu motor)

J1 = **tam ngoi sao**. Khong daisy-chain 12V motor → sensor.

| Nhanh | Net | Be rong | Noi |
|-------|-----|---------|-----|
| Cong suat MOT | `+12V` | **2.5 mm** | TMC + 3x L298N + bulk 470u |
| Tin hieu SNS | `+12V_SNS` | **0.5 mm** | qua R10=10R + C10=47u\\|\\|C11=100n → limit + BUP |
| GND MOT | `GND` (duong rieng) | 2.5 mm | driver → J1- |
| GND SNS | `GND` (duong rieng) | 0.5 mm | filter/sensor → J1- |

Hai GND chi gap tai chan J1-. Bulk C20..C23 = 470uF/25V sat moi driver.

'''
        t = t.replace(
            "## Tai tao",
            doc + "## Tai tao",
            1,
        )

    GEN.write_text(t, encoding="utf-8")
    print("Star power patch written")


if __name__ == "__main__":
    main()
