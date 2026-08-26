#!/usr/bin/env python3
"""Add Autonics BUP-30S (NPN) jack + 4k7 pull-up to OPTO_IN7 / GPIO18."""
from __future__ import annotations

from pathlib import Path

GEN = Path(__file__).resolve().parent / "gen_power_carrier.py"

SYM = r'''
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
    a('\t\t(property "Description" "TOP: Autonics BUP-30S NPN 12V -> opto IN7"')
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

'''

FP_R = r'''
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
    a('\t\t(at 0 -2.5 0)')
    a('\t\t(layer "F.SilkS")')
    a("\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))")
    a("\t)")
    a('\t(property "Value" "4k7"')
    a('\t\t(at 0 2.5 0)')
    a('\t\t(layer "F.Fab")')
    a("\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))")
    a("\t)")
    a("\t(attr through_hole)")
    a("\t(fp_line (start -2.5 0) (end 2.5 0) (stroke (width 0.12) (type solid)) (layer \"F.SilkS\"))")
    a('\t(pad "1" thru_hole circle (at -3.75 0) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))')
    a('\t(pad "2" thru_hole circle (at 3.75 0) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))')
    a(")")
    out = PRETTY / "R_Axial_4k7_BUP.kicad_mod"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


'''

SCH = r'''
    # --- Autonics BUP-30S (NPN) @12V -> OPTO_IN7 / GPIO18 ---
    j14 = (215.9, 203.2)
    r1 = (241.3, 203.2)
    j14_uuid, r1_uuid = uid(), uid()
    parts.append(text("BUP-30S NPN: Nau=+12 Xanh=GND Den=OUT Trang=CTRL", 190.0, 185.0, 1.0))
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
    # pin world: at_y - local_y
    j14_12 = (j14[0], j14[1] - 3.81)
    j14_gnd = (j14[0], j14[1] - 1.27)
    j14_out = (j14[0], j14[1] + 1.27)
    j14_ctrl = (j14[0], j14[1] + 3.81)
    r1_a = (r1[0], r1[1] - 3.81)  # pin1 top -> +12V
    r1_b = (r1[0], r1[1] + 3.81)  # pin2 bot -> OUT/OPTO_IN7
    parts += wire_path(j14_12, (j14_12[0] - 5.08, j14_12[1]))
    parts.append(label("+12V", j14_12[0] - 5.08, j14_12[1]))
    parts += wire_path(j14_gnd, (j14_gnd[0] - 5.08, j14_gnd[1]))
    parts.append(label("GND", j14_gnd[0] - 5.08, j14_gnd[1]))
    parts += wire_path(j14_out, (j14_out[0] + 5.08, j14_out[1]), (r1_b[0], j14_out[1]), r1_b)
    parts.append(label("OPTO_IN7", j14_out[0] + 5.08, j14_out[1]))
    parts += wire_path(r1_a, (r1_a[0], j14_12[1]), (j14_12[0] - 2.54, j14_12[1]))
    # CTRL: leave as selectable jumper note (no default net) — NC with note
    parts.append(f'\t(no_connect (at {j14_ctrl[0]} {j14_ctrl[1]}) (uuid "{uid()}"))')
    parts.append(text("CTRL: LightON->+12V / DarkON->GND", j14[0] - 5, j14[1] + 12.7, 1.0))

'''

PCB = r'''
    # --- J14 BUP-30S + R1 4k7 pull-up (TOP) ---
    j14x, j14y = ox + 8.0, oy + 55.0
    r1x, r1y = j14x + 12.0, j14y + 1.5 * PITCH
    gr_box(j14x - 4, j14y - 5, j14x + 20, j14y + 3 * PITCH + 5, "F.SilkS")
    gr_text("J14 BUP-30S NPN", j14x - 3, j14y - 6.5, "F.SilkS", 0.85)
    gr_text("Brn +12 Blu GND Blk OUT Wht CTRL", j14x - 3, j14y + 3 * PITCH + 6.5, "F.SilkS", 0.65)
    gr_text("R1 4k7 pullup NPN", r1x - 2, r1y - 4, "F.SilkS", 0.7)
    bup_pads = [
        (1, "+12V", 1, "+12V"),
        (2, "GND", 2, "GND"),
        (3, "OUT", 31, "/OPTO_IN7"),
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
        a('\t\t\t(layer "F.SilkS")')
        a("\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1)) (justify left))")
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
    # R1 between +12V and OPTO_IN7
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
    a("\t\t\t(at 0 2.8 0)")
    a('\t\t\t(layer "F.Fab")')
    a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")
    a('\t\t(pad "1" thru_hole circle')
    a("\t\t\t(at -3.75 0)")
    a("\t\t\t(size 1.6 1.6)")
    a("\t\t\t(drill 0.8)")
    a('\t\t\t(layers "*.Cu" "*.Mask")')
    a('\t\t\t(net 1 "+12V")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(pad "2" thru_hole circle')
    a("\t\t\t(at 3.75 0)")
    a("\t\t\t(size 1.6 1.6)")
    a("\t\t\t(drill 0.8)")
    a('\t\t\t(layers "*.Cu" "*.Mask")')
    a('\t\t\t(net 31 "/OPTO_IN7")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t)")
    # Routes: +12V/GND from power; OUT to U4 IN7
    p12 = (j14x, j14y)
    pg = (j14x, j14y + PITCH)
    po = (j14x, j14y + 2 * PITCH)
    track(p12[0], p12[1], p12[0] - 4, p12[1], 1, "F.Cu", 0.5)
    track(p12[0] - 4, p12[1], p12[0] - 4, oy + 22.0, 1, "F.Cu", 0.5)
    track(p12[0] - 4, oy + 22.0, t_vm[0], oy + 22.0, 1, "F.Cu", 0.5)
    track(pg[0], pg[1], pg[0] - 6, pg[1], 2, "F.Cu", 0.5)
    track(pg[0] - 6, pg[1], pg[0] - 6, u1_gnd_l[1], 2, "F.Cu", 0.5)
    track(pg[0] - 6, u1_gnd_l[1], u1_gnd_l[0], u1_gnd_l[1], 2, "F.Cu", 0.5)
    via(pg[0] - 6, u1_gnd_l[1], 2, 0.4, 0.8)
    upt7 = pad_world(ox4, oy4, rot4, xs_opto[8], -hx_o)  # IN7 = index 8 (0=GND 1=VCC 2=IN1 ... 8=IN7)
    via(po[0], po[1], 31, 0.4, 0.8)
    xl = ox + bw - 3.0
    track(po[0], po[1], xl, po[1], 31, "F.Cu", 0.35)
    track(xl, po[1], xl, upt7[1], 31, "F.Cu", 0.35)
    track(xl, upt7[1], upt7[0], upt7[1], 31, "F.Cu", 0.35)
    # R1 already netted on pads; short stitches to nearby +12V / OUT pads
    track(r1x - 3.75, r1y, p12[0], r1y, 1, "F.Cu", 0.4)
    track(p12[0], r1y, p12[0], p12[1], 1, "F.Cu", 0.4)
    track(r1x + 3.75, r1y, po[0] + 4, r1y, 31, "F.Cu", 0.4)
    track(po[0] + 4, r1y, po[0] + 4, po[1], 31, "F.Cu", 0.4)
    track(po[0] + 4, po[1], po[0], po[1], 31, "F.Cu", 0.4)

'''


def main() -> None:
    t = GEN.read_text(encoding="utf-8")
    if "Conn_1x04_BUP30S" in t and "J14" in t and "BUP_30S" in t:
        print("Already patched?")
        # continue idempotent checks

    if 'symbol "Conn_1x04_BUP30S"' not in t:
        t = t.replace(
            "    # --- PC817 8CH opto (MCU OUT + power; field INs on separate Conn) ---",
            SYM + "    # --- PC817 8CH opto (MCU OUT + power; field INs on separate Conn) ---",
            1,
        )

    if "def write_r_axial_4k7_bup" not in t:
        t = t.replace(
            "def write_l298n_footprint() -> Path:",
            FP_R + "def write_l298n_footprint() -> Path:",
            1,
        )

    if '_embed_from_lib("Conn_1x04_BUP30S")' not in t:
        t = t.replace(
            '_embed_from_lib("Conn_1x02_LimitSW"),',
            '_embed_from_lib("Conn_1x02_LimitSW"),\n'
            '            _embed_from_lib("Conn_1x04_BUP30S"),\n'
            '            _embed_from_lib("R_BUP_Pullup"),',
            1,
        )

    if "write_r_axial_4k7_bup()" not in t:
        t = t.replace(
            'write_pin_header_footprint(2, "PinHeader_1x02_LimitSW", ["+12V", "SW"]),',
            'write_pin_header_footprint(2, "PinHeader_1x02_LimitSW", ["+12V", "SW"]),\n'
            '        write_pin_header_footprint(4, "PinHeader_1x04_BUP30S", ["+12V", "GND", "OUT", "CTRL"]),\n'
            "        write_r_axial_4k7_bup(),",
            1,
        )

    if "Autonics BUP-30S" not in t:
        # insert schematic before used=
        marker = "    used = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27}"
        if marker not in t:
            raise SystemExit("used marker missing")
        t = t.replace(marker, SCH + "\n" + marker, 1)

    if "J14 BUP-30S" not in t:
        marker = '    a(")")\n    out = ROOT / "esp32_baseboard.kicad_pcb"'
        if marker not in t:
            raise SystemExit("pcb end marker missing")
        t = t.replace(marker, PCB + "\n" + marker, 1)

    t = t.replace(
        'gr_text("IN1-6=hanh trinh; IN7-8 free", j4x + 8, j4y + 1.2, "F.SilkS", 0.65)',
        'gr_text("IN1-6=lim; IN7=BUP30S; IN8 free", j4x + 8, j4y + 1.2, "F.SilkS", 0.65)',
        1,
    )

    # readme
    if "BUP-30S" not in t[t.find("def write_readme") : t.find("def write_project")]:
        insert = '''
## Autonics BUP-30S (quang chu U, NPN)

Module: [Shopee BUP-30S](https://shopee.vn/C%E1%BA%A3m-bi%E1%BA%BFn-quang-Autonic-BUP-30-BUP-30S-BUP30-P-BUP-50S-i.131821169.2935543284)

| Jack | Day cam bien | Board |
|------|--------------|-------|
| J14.1 +12V | Nau (Brown) | +12V |
| J14.2 GND | Xanh (Blue) | GND |
| J14.3 OUT | Den (Black) | OPTO_IN7 (+ R1 4k7 pull-up) |
| J14.4 CTRL | Trang (White) | LightON jumper +12V / DarkON jumper GND |

```
+12V --[R1 4k7]-- OUT/OPTO_IN7 --[opto LED]-- GND
                    |
                 NPN OUT (Black) sink khi kich hoat
```

ESP32: OPTO_OUT7 → **GPIO18** (doc 0/1). Logic dao (LED tat khi NPN bat) — xu ly trong firmware.
J4 IN8 con trong.

'''
        t = t.replace(
            "- J4 IN7/IN8 con trong; IN1-6 dung cho hanh trinh (co the song song J4).",
            "- J4 IN1-6 = hanh trinh; **IN7 = BUP-30S (J14)**; IN8 con trong." + insert,
            1,
        )
        t = t.replace(
            "| **Top** | J2 NEMA, J3 sensor, J4 OPTO, **3 nhom TRUC (MOT+MIN+MAX)** |",
            "| **Top** | J2 NEMA, J3, J4 OPTO, 3 nhom TRUC, **J14 BUP-30S** |",
            1,
        )

    GEN.write_text(t, encoding="utf-8")
    print("BUP-30S patch applied")


if __name__ == "__main__":
    main()
