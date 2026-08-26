#!/usr/bin/env python3
"""Replace PCB L298N top-jack section with MOT+MIN+MAX groups."""
from pathlib import Path

GEN = Path(__file__).resolve().parent / "gen_power_carrier.py"

NEW_BLOCK = r'''    l298n_pcb = [
        # (U, Jmot, Jmin, Jmax, ux, uy, jx, jy, ni1, ni2, nma, nmb, g1, g2, nmin, nmax)
        # opto nets IN1=25 .. IN6=30
        ("U5", "J5", "J8", "J9", ox + 148.0, oy + 50.0, ox + 70.0, oy + 42.0, 40, 41, 34, 35, "IO21", "IO22", 25, 26),
        ("U6", "J6", "J10", "J11", ox + 148.0, oy + 100.0, ox + 105.0, oy + 42.0, 42, 43, 36, 37, "IO23", "IO13", 27, 28),
        ("U7", "J7", "J12", "J13", ox + 148.0, oy + 150.0, ox + 140.0, oy + 42.0, 44, 45, 38, 39, "IO12", "IO14", 29, 30),
    ]
    esp_gpio_local = {
        "IO21": (0, 10 * PITCH),
        "IO22": (0, 13 * PITCH),
        "IO23": (0, 14 * PITCH),
        "IO13": (ROW_SPACING, 2 * PITCH),
        "IO12": (ROW_SPACING, 3 * PITCH),
        "IO14": (ROW_SPACING, 4 * PITCH),
    }

    def _hdr_1x2(fp, ref, val, atx, aty, pads):
        a(f'\t(footprint "ESP32_Carrier:{fp}"')
        a('\t\t(layer "F.Cu")')
        a(f'\t\t(uuid "{uid()}")')
        a(f"\t\t(at {atx} {aty})")
        a(f'\t\t(property "Reference" "{ref}"')
        a("\t\t\t(at 0 -3.8 0)")
        a('\t\t\t(layer "F.SilkS")')
        a("\t\t\t(effects (font (size 0.9 0.9) (thickness 0.12)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a(f'\t\t(property "Value" "{val}"')
        a(f"\t\t\t(at 0 {PITCH + 3.8} 0)")
        a('\t\t\t(layer "F.Fab")')
        a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.1)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a("\t\t(attr through_hole)")
        for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
            a("\t\t(fp_rect")
            a("\t\t\t(start -1.8 -1.8)")
            a(f"\t\t\t(end 1.8 {PITCH + 1.8})")
            a(f"\t\t\t(stroke (width {w}) (type solid))")
            a("\t\t\t(fill none)")
            a(f'\t\t\t(layer "{layer}")')
            a(f'\t\t\t(uuid "{uid()}")')
            a("\t\t)")
        for pi, (neti, netn, lab) in enumerate(pads):
            y = pi * PITCH
            a(f'\t\t(fp_text user "{lab}"')
            a(f"\t\t\t(at 3.2 {y} 0)")
            a('\t\t\t(layer "F.SilkS")')
            a("\t\t\t(effects (font (size 0.65 0.65) (thickness 0.1)) (justify left))")
            a(f'\t\t\t(uuid "{uid()}")')
            a("\t\t)")
            shape = "rect" if pi == 0 else "circle"
            a(f'\t\t(pad "{pi + 1}" thru_hole {shape}')
            a(f"\t\t\t(at 0 {y})")
            a("\t\t\t(size 1.7 1.7)")
            a("\t\t\t(drill 1.0)")
            a('\t\t\t(layers "*.Cu" "*.Mask")')
            a(f'\t\t\t(net {neti} "{netn}")')
            a(f'\t\t\t(uuid "{uid()}")')
            a("\t\t)")
        a("\t)")

    for mi, (uref, jref, jmin, jmax, ux, uy, jx, jy, ni1, ni2, nma, nmb, g1, g2, nmin, nmax) in enumerate(l298n_pcb):
        gr_box(ux - 22, uy - 22, ux + 22, uy + 22, "B.SilkS")
        gr_text(f"{uref} L298N GA12", ux - 20, uy + 24, "B.SilkS", 0.85)
        gr_text("Vs=12V ENA=JMP", ux - 20, uy + 21.5, "B.SilkS", 0.7)
        a('\t(footprint "ESP32_Carrier:L298N_Module"')
        a('\t\t(layer "B.Cu")')
        a(f'\t\t(uuid "{uid()}")')
        a(f"\t\t(at {ux} {uy} {rot})")
        a(f'\t\t(property "Reference" "{uref}"')
        a(f"\t\t\t(at 0 {-L298N_H / 2 - 1.8} {rot})")
        a('\t\t\t(layer "B.SilkS")')
        a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a('\t\t(property "Value" "L298N_Module"')
        a(f"\t\t\t(at 0 {L298N_H / 2 + 1.8} {rot})")
        a('\t\t\t(layer "B.Fab")')
        a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a("\t\t(attr through_hole)")
        for layer, w in (("B.CrtYd", 0.05), ("B.Fab", 0.1), ("B.SilkS", 0.12)):
            a("\t\t(fp_rect")
            a(f"\t\t\t(start {-L298N_W / 2} {-L298N_H / 2})")
            a(f"\t\t\t(end {L298N_W / 2} {L298N_H / 2})")
            a(f"\t\t\t(stroke (width {w}) (type solid))")
            a("\t\t\t(fill none)")
            a(f'\t\t\t(layer "{layer}")')
            a(f'\t\t\t(uuid "{uid()}")')
            a("\t\t)")
        l298_pads = [
            ("1", -8.0, -16.0, 1, "+12V"),
            ("2", 0.0, -16.0, 2, "GND"),
            ("3", 8.0, -16.0, 0, ""),
            ("4", -18.0, -6.0, 0, ""),
            ("5", -18.0, 0.0, ni1, f"/DC{mi + 1}_IN1"),
            ("6", -18.0, 6.0, ni2, f"/DC{mi + 1}_IN2"),
            ("7", 18.0, -4.0, nma, f"/MotDC{mi + 1}_A"),
            ("8", 18.0, 4.0, nmb, f"/MotDC{mi + 1}_B"),
        ]
        for i, (num, lx, ly, neti, netn) in enumerate(l298_pads):
            shape = "rect" if i == 0 else "circle"
            a(f'\t\t(pad "{num}" thru_hole {shape}')
            a(f"\t\t\t(at {lx} {ly})")
            a("\t\t\t(size 2.0 2.0)")
            a("\t\t\t(drill 1.1)")
            a('\t\t\t(layers "*.Cu" "*.Mask")')
            if neti:
                a(f'\t\t\t(net {neti} "{netn}")')
            a(f'\t\t\t(uuid "{uid()}")')
            a("\t\t)")
        a("\t)")

        # TOP group: MOT + LIM_MIN + LIM_MAX (NC @12V -> opto)
        jx_min, jx_max = jx + 8.0, jx + 16.0
        gr_box(jx - 4, jy - 5, jx_max + 6, jy + PITCH + 5, "F.SilkS")
        gr_text(f"TRUC{mi + 1} MOT+LIM NC", jx - 3, jy - 6.5, "F.SilkS", 0.85)
        gr_text(f"{jref} MOT  {jmin} MIN  {jmax} MAX", jx - 3, jy + PITCH + 6.5, "F.SilkS", 0.7)
        _hdr_1x2(
            "PinHeader_1x02_MotorDC",
            jref,
            "GA12_N20",
            jx,
            jy,
            [(nma, f"/MotDC{mi + 1}_A", "M+"), (nmb, f"/MotDC{mi + 1}_B", "M-")],
        )
        _hdr_1x2(
            "PinHeader_1x02_LimitSW",
            jmin,
            "LIM_MIN_NC",
            jx_min,
            jy,
            [(1, "+12V", "+12"), (nmin, f"/OPTO_IN{2 * mi + 1}", "SW")],
        )
        _hdr_1x2(
            "PinHeader_1x02_LimitSW",
            jmax,
            "LIM_MAX_NC",
            jx_max,
            jy,
            [(1, "+12V", "+12"), (nmax, f"/OPTO_IN{2 * mi + 2}", "SW")],
        )

        p_vs = pad_world(ux, uy, rot, -8.0, -16.0)
        p_gnd = pad_world(ux, uy, rot, 0.0, -16.0)
        p_in1 = pad_world(ux, uy, rot, -18.0, 0.0)
        p_in2 = pad_world(ux, uy, rot, -18.0, 6.0)
        p_o1 = pad_world(ux, uy, rot, 18.0, -4.0)
        p_o2 = pad_world(ux, uy, rot, 18.0, 4.0)
        track(p_vs[0], p_vs[1], t_vm[0], p_vs[1], 1, "B.Cu", 1.0)
        track(t_vm[0], p_vs[1], t_vm[0], t_vm[1], 1, "B.Cu", 1.0)
        track(p_gnd[0], p_gnd[1], u1_gnd_l[0], p_gnd[1], 2, "B.Cu", 1.0)
        track(u1_gnd_l[0], p_gnd[1], u1_gnd_l[0], u1_gnd_l[1], 2, "B.Cu", 1.0)
        lx1, ly1 = esp_gpio_local[g1]
        lx2, ly2 = esp_gpio_local[g2]
        e1 = pad_world(fx, fy, rot, lx1, ly1)
        e2 = pad_world(fx, fy, rot, lx2, ly2)
        xlane = ox + 110 + mi * 2.0
        track(e1[0], e1[1], xlane, e1[1], ni1, "B.Cu", 0.3)
        track(xlane, e1[1], xlane, p_in1[1], ni1, "B.Cu", 0.3)
        track(xlane, p_in1[1], p_in1[0], p_in1[1], ni1, "B.Cu", 0.3)
        xlane2 = ox + 112 + mi * 2.0
        track(e2[0], e2[1], xlane2, e2[1], ni2, "B.Cu", 0.3)
        track(xlane2, e2[1], xlane2, p_in2[1], ni2, "B.Cu", 0.3)
        track(xlane2, p_in2[1], p_in2[0], p_in2[1], ni2, "B.Cu", 0.3)
        via(p_o1[0], p_o1[1], nma, 0.4, 0.8)
        via(p_o2[0], p_o2[1], nmb, 0.4, 0.8)
        jmp = (jx, jy)
        jmm = (jx, jy + PITCH)
        track(p_o1[0], p_o1[1], jmp[0], p_o1[1], nma, "F.Cu", 0.6)
        track(jmp[0], p_o1[1], jmp[0], jmp[1], nma, "F.Cu", 0.6)
        track(p_o2[0], p_o2[1], jmm[0] + 2.0, p_o2[1], nmb, "F.Cu", 0.6)
        track(jmm[0] + 2.0, p_o2[1], jmm[0] + 2.0, jmm[1], nmb, "F.Cu", 0.6)
        track(jmm[0] + 2.0, jmm[1], jmm[0], jmm[1], nmb, "F.Cu", 0.6)
        for atx, neti, ch in [(jx_min, nmin, 2 * mi), (jx_max, nmax, 2 * mi + 1)]:
            p12 = (atx, jy)
            psw = (atx, jy + PITCH)
            track(p12[0], p12[1], p12[0], oy + 22.0, 1, "F.Cu", 0.5)
            track(p12[0], oy + 22.0, t_vm[0], oy + 22.0, 1, "F.Cu", 0.5)
            via(t_vm[0], oy + 22.0, 1, 0.4, 0.8)
            upt = pad_world(ox4, oy4, rot4, xs_opto[ch + 2], -hx_o)
            via(psw[0], psw[1], neti, 0.4, 0.8)
            xl = ox + bw - 4.0 - ch * 1.2
            track(psw[0], psw[1], xl, psw[1], neti, "F.Cu", 0.35)
            track(xl, psw[1], xl, upt[1], neti, "F.Cu", 0.35)
            track(xl, upt[1], upt[0], upt[1], neti, "F.Cu", 0.35)

'''


def main() -> None:
    t = GEN.read_text(encoding="utf-8")
    start = t.index("    l298n_pcb = [")
    end = t.index('    a(")")\n    out = ROOT / "esp32_baseboard.kicad_pcb"')
    t = t[:start] + NEW_BLOCK + "\n" + t[end:]

    # Remove bad cross-net stitch (GND_I already remapped to GND on pads)
    bad = (
        "    # GND_I stitch shared 12V (limit NC loop uses +12V / GND_I)\n"
        "    u4_gndi = pad_world(ox4, oy4, rot4, xs_opto[0], -hx_o)\n"
        '    track(u4_gndi[0], u4_gndi[1], u1_gnd_l[0], u4_gndi[1], 33, "B.Cu", 0.5)\n'
        "    # merge field GND_I onto system GND for shared 12V limits\n"
        '    track(u4_gndi[0], u4_gndi[1], u4_gndo[0], u4_gndi[1], 2, "B.Cu", 0.5)\n'
    )
    t = t.replace(bad, "", 1)

    # Fix broken readme table
    bad_rm = """| Driver | Motor jack (TOP) | ESP32 IN1/IN2 | Power |
|--------|------------------|---------------|-------|
| Truc | Driver | Nhom jack TOP | Motor GPIO | Limit -> Opto |
|------|--------|---------------|------------|---------------|"""
    good_rm = """| Truc | Driver | Nhom jack TOP | Motor GPIO | Limit -> Opto |
|------|--------|---------------|------------|---------------|"""
    t = t.replace(bad_rm, good_rm, 1)

    # J4 silk
    t = t.replace(
        'gr_text("GND VCC IN1-8 cach ly", j4x + 8, j4y + 1.2, "F.SilkS", 0.7)',
        'gr_text("IN1-6=hanh trinh; IN7-8 free", j4x + 8, j4y + 1.2, "F.SilkS", 0.65)',
        1,
    )

    # Fix schematic shadowing: motor jack uses ref_j but limit loop reuses jref — motor already uses ref_j
    # Fix OPTO_IN label: u4p 3->IN1 so u4p-2 is correct

    GEN.write_text(t, encoding="utf-8")
    print("PCB block replaced")


if __name__ == "__main__":
    main()
