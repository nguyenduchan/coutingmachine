#!/usr/bin/env python3
"""Add 6x NC limit-switch jacks (12V→opto), grouped with each DC motor jack."""
from __future__ import annotations

from pathlib import Path

GEN = Path(__file__).resolve().parent / "gen_power_carrier.py"


def main() -> None:
    t = GEN.read_text(encoding="utf-8")

    if '_embed_from_lib("Conn_1x02_LimitSW")' not in t:
        t = t.replace(
            '_embed_from_lib("Conn_1x02_MotorDC"),',
            '_embed_from_lib("Conn_1x02_MotorDC"),\n'
            '            _embed_from_lib("Conn_1x02_LimitSW"),',
            1,
        )

    if 'PinHeader_1x02_LimitSW' not in t[t.find("def main") :]:
        t = t.replace(
            'write_pin_header_footprint(2, "PinHeader_1x02_MotorDC", ["M+", "M-"]),',
            'write_pin_header_footprint(2, "PinHeader_1x02_MotorDC", ["M+", "M-"]),\n'
            '        write_pin_header_footprint(2, "PinHeader_1x02_LimitSW", ["+12V", "SW"]),',
            1,
        )

    # --- Schematic: replace L298N block end to add limit jacks ---
    old_nc = '''        # ENA + 5V NC (ENA jumpered on module)
        parts.append(f'\\t(no_connect (at {ena[0]} {ena[1]}) (uuid "{uid()}"))')
        parts.append(f'\\t(no_connect (at {xu - 15.24} {yu - 2.54}) (uuid "{uid()}"))')

    used = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27}'''

    # Check if already patched
    if "LIM NC @12V" in t and "J8" in t and "l298n_place" in t:
        print("schematic may already have limits — checking")
    else:
        # Expand l298n_place and add limit symbols after each motor
        old_place = '''    l298n_place = [
        # (ref_u, ref_j, x_u, y_u, x_j, y_j, in1_esp_pin, in2_esp_pin, label)
        ("U5", "J5", 95.25, 203.2, 165.1, 203.2, 11, 14, "M1 IO21/22"),
        ("U6", "J6", 95.25, 241.3, 165.1, 241.3, 15, 18, "M2 IO23/13"),
        ("U7", "J7", 95.25, 279.4, 165.1, 279.4, 19, 20, "M3 IO12/14"),
    ]
    for mi, (ref_u, ref_j, xu, yu, xj, yj, pin_in1, pin_in2, lab) in enumerate(l298n_place):'''

        new_place = '''    l298n_place = [
        # motor + 2x limit NC @12V -> opto IN1..IN6
        # (U, Jmot, Jmin, Jmax, xu, yu, xj, yj, in1, in2, u4_in_min, u4_in_max, label)
        ("U5", "J5", "J8", "J9", 95.25, 203.2, 165.1, 203.2, 11, 14, 3, 4, "TRUC1 MOT+LIM"),
        ("U6", "J6", "J10", "J11", 95.25, 241.3, 165.1, 241.3, 15, 18, 5, 6, "TRUC2 MOT+LIM"),
        ("U7", "J7", "J12", "J13", 95.25, 279.4, 165.1, 279.4, 19, 20, 7, 8, "TRUC3 MOT+LIM"),
    ]
    for mi, (ref_u, ref_j, jmin, jmax, xu, yu, xj, yj, pin_in1, pin_in2, u4min, u4max, lab) in enumerate(l298n_place):'''

        if old_place not in t:
            raise SystemExit("l298n_place block not found")
        t = t.replace(old_place, new_place, 1)

        insert_lim = '''
        # Limit MIN/MAX jacks (NC): +12V --[NC SW]-- OPTO_INx ; field GND_I = GND (shared 12V)
        xj_min, xj_max = xj + 25.4, xj + 50.8
        for jref, xjl, u4p, tag in [
            (jmin, xj_min, u4min, "MIN"),
            (jmax, xj_max, u4max, "MAX"),
        ]:
            ju = uid()
            p12 = (xjl, yj - 1.27)
            psw = (xjl, yj + 1.27)
            parts += [
                f'\\t(symbol (lib_id "ESP32_Carrier:Conn_1x02_LimitSW") (at {xjl} {yj} 0) (unit 1)',
                f'\\t\\t(uuid "{ju}")',
                f'\\t\\t(property "Reference" "{jref}" (at {xjl} {yj - 7.62} 0)',
                "\\t\\t\\t(effects (font (size 1.27 1.27)))",
                "\\t\\t)",
                f'\\t\\t(property "Value" "LIM_{tag}_NC" (at {xjl} {yj + 7.62} 0)',
                "\\t\\t\\t(effects (font (size 1.27 1.27)))",
                "\\t\\t)",
                f'\\t\\t(property "Footprint" "ESP32_Carrier:PinHeader_1x02_LimitSW" (at {xjl} {yj} 0)',
                "\\t\\t\\t(effects (font (size 1.27 1.27)) (hide yes))",
                "\\t\\t)",
                f'\\t\\t(property "Datasheet" "~" (at {xjl} {yj} 0)',
                "\\t\\t\\t(effects (font (size 1.27 1.27)) (hide yes))",
                "\\t\\t)",
                f'\\t\\t(pin "1" (uuid "{uid()}"))',
                f'\\t\\t(pin "2" (uuid "{uid()}"))',
                "\\t\\t(instances",
                f'\\t\\t\\t(project "esp32_baseboard" (path "/{sch_uuid}" (reference "{jref}") (unit 1)))',
                "\\t\\t)",
                "\\t)",
            ]
            parts += wire_path(p12, (p12[0], y12), (u3_vm[0], y12))
            # SW -> U4 INx (same net as J4 field IN)
            uin = u4_pin(u4p)
            parts += wire_path(psw, (psw[0], psw[1] + 5.08), (uin[0] - 20.32, psw[1] + 5.08), (uin[0] - 20.32, uin[1]), uin)
            parts.append(label(f"OPTO_IN{u4p - 2}", psw[0], psw[1] + 5.08))

        # ENA + 5V NC (ENA jumpered on module)
        parts.append(f'\\t(no_connect (at {ena[0]} {ena[1]}) (uuid "{uid()}"))')
        parts.append(f'\\t(no_connect (at {xu - 15.24} {yu - 2.54}) (uuid "{uid()}"))')

    used = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27}'''

        # Problem: insert_lim uses escaped backslashes wrongly for writing into file.
        # Build as raw Python source for gen_power_carrier.py
        insert_lim = r'''
        # Limit MIN/MAX jacks (NC): +12V --[NC SW]-- OPTO_INx ; field GND_I shared with GND
        xj_min, xj_max = xj + 25.4, xj + 50.8
        for jref, xjl, u4p, tag in [
            (jmin, xj_min, u4min, "MIN"),
            (jmax, xj_max, u4max, "MAX"),
        ]:
            ju = uid()
            p12 = (xjl, yj - 1.27)
            psw = (xjl, yj + 1.27)
            parts += [
                f'\t(symbol (lib_id "ESP32_Carrier:Conn_1x02_LimitSW") (at {xjl} {yj} 0) (unit 1)',
                f'\t\t(uuid "{ju}")',
                f'\t\t(property "Reference" "{jref}" (at {xjl} {yj - 7.62} 0)',
                "\t\t\t(effects (font (size 1.27 1.27)))",
                "\t\t)",
                f'\t\t(property "Value" "LIM_{tag}_NC" (at {xjl} {yj + 7.62} 0)',
                "\t\t\t(effects (font (size 1.27 1.27)))",
                "\t\t)",
                f'\t\t(property "Footprint" "ESP32_Carrier:PinHeader_1x02_LimitSW" (at {xjl} {yj} 0)',
                "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
                "\t\t)",
                f'\t\t(property "Datasheet" "~" (at {xjl} {yj} 0)',
                "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
                "\t\t)",
                f'\t\t(pin "1" (uuid "{uid()}"))',
                f'\t\t(pin "2" (uuid "{uid()}"))',
                "\t\t(instances",
                f'\t\t\t(project "esp32_baseboard" (path "/{sch_uuid}" (reference "{jref}") (unit 1)))',
                "\t\t)",
                "\t)",
            ]
            parts += wire_path(p12, (p12[0], y12), (u3_vm[0], y12))
            uin = u4_pin(u4p)
            parts += wire_path(psw, (psw[0], psw[1] + 5.08), (uin[0] - 20.32, psw[1] + 5.08), (uin[0] - 20.32, uin[1]), uin)
            parts.append(label(f"OPTO_IN{u4p - 2}", psw[0], psw[1] + 5.08))

        # ENA + 5V NC (ENA jumpered on module)
        parts.append(f'\t(no_connect (at {ena[0]} {ena[1]}) (uuid "{uid()}"))')
        parts.append(f'\t(no_connect (at {xu - 15.24} {yu - 2.54}) (uuid "{uid()}"))')

    used = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27}'''

        if old_nc not in t:
            # try without the used line in old_nc - match just the NC block
            raise SystemExit("old_nc block not found — dump nearby")
        t = t.replace(old_nc, insert_lim, 1)

        # u4_pin is defined AFTER the L298N block currently - need to move or define earlier
        # Check order: L298N block is AFTER opto wiring which defines u4_pin. Good!

    # Stitch note in opto sch: add wire GND_I to GND after opto gnd wire
    if "GND_I shared 12V" not in t:
        stitch = '''    parts += wire_path(
        u4_pin(11),
        (u4_pin(11)[0] + 12, u4_pin(11)[1]),
        (u4_pin(11)[0] + 12, ygnd),
        (u1_gnd_l[0], ygnd),
    )
    parts.append(text("GND_I=GND (limit SW @12V shared)", 220.0, 63.5, 1.0))
'''
        old_gnd = '''    parts += wire_path(
        u4_pin(11),
        (u4_pin(11)[0] + 12, u4_pin(11)[1]),
        (u4_pin(11)[0] + 12, ygnd),
        (u1_gnd_l[0], ygnd),
    )
'''
        if old_gnd in t:
            t = t.replace(old_gnd, stitch, 1)

    # --- PCB: replace motor-only jack with grouped MOT+MIN+MAX ---
    if "TRUC1 MOT+LIM" not in t and "J8" not in t[t.find("l298n_pcb") : t.find("l298n_pcb") + 800]:
        old_pcb_hdr = '''    l298n_pcb = [
        # (ref, jref, ux, uy, jx, jy, net_in1, net_in2, net_ma, net_mb, gpio_in1, gpio_in2)
        ("U5", "J5", ox + 148.0, oy + 50.0, ox + 125.0, oy + 12.0, 40, 41, 34, 35, "IO21", "IO22"),
        ("U6", "J6", ox + 148.0, oy + 100.0, ox + 140.0, oy + 12.0, 42, 43, 36, 37, "IO23", "IO13"),
        ("U7", "J7", ox + 148.0, oy + 150.0, ox + 155.0, oy + 12.0, 44, 45, 38, 39, "IO12", "IO14"),
    ]'''
        new_pcb_hdr = '''    l298n_pcb = [
        # (U, Jmot, Jmin, Jmax, ux, uy, jx, jy, ni1, ni2, nma, nmb, g1, g2, net_min, net_max)
        # opto nets: IN1=25 .. IN6=30
        ("U5", "J5", "J8", "J9", ox + 148.0, oy + 50.0, ox + 70.0, oy + 42.0, 40, 41, 34, 35, "IO21", "IO22", 25, 26),
        ("U6", "J6", "J10", "J11", ox + 148.0, oy + 100.0, ox + 105.0, oy + 42.0, 42, 43, 36, 37, "IO23", "IO13", 27, 28),
        ("U7", "J7", "J12", "J13", ox + 148.0, oy + 150.0, ox + 140.0, oy + 42.0, 44, 45, 38, 39, "IO12", "IO14", 29, 30),
    ]'''
        if old_pcb_hdr not in t:
            raise SystemExit("l298n_pcb header missing")
        t = t.replace(old_pcb_hdr, new_pcb_hdr, 1)

        t = t.replace(
            "for mi, (uref, jref, ux, uy, jx, jy, ni1, ni2, nma, nmb, g1, g2) in enumerate(l298n_pcb):",
            "for mi, (uref, jref, jmin, jmax, ux, uy, jx, jy, ni1, ni2, nma, nmb, g1, g2, nmin, nmax) in enumerate(l298n_pcb):",
            1,
        )

        # Replace TOP motor jack section through end of motor routes with group version
        old_top = '''        # TOP motor jack 1x2
        gr_box(jx - 3, jy - 3, jx + 5, jy + PITCH + 3, "F.SilkS")
        gr_text(f"{jref} GA12-N20", jx - 2, jy - 4.5, "F.SilkS", 0.8)
        gr_text("M+ | M-", jx - 2, jy + PITCH + 4.5, "F.SilkS", 0.7)
        a('\\t(footprint "ESP32_Carrier:PinHeader_1x02_MotorDC"')'''

        # We'll insert a helper block by replacing from TOP motor through track motor outs ending
        marker_start = "        # TOP motor jack 1x2\n"
        marker_end = "        track(jmm[0] + 2.0, jmm[1], jmm[0], jmm[1], nmb, \"F.Cu\", 0.6)\n\n    a(\")\")"
        if marker_start not in t or marker_end not in t:
            raise SystemExit(f"PCB top markers missing start={marker_start in t} end={marker_end in t}")

        i0 = t.find(marker_start)
        i1 = t.find(marker_end)
        if i0 < 0 or i1 < 0 or i1 < i0:
            raise SystemExit("PCB replace range bad")
        i1_end = i1 + len(marker_end) - len('\n\n    a(")")')  # keep a(")")

        new_top = r'''        # TOP group: MOT + LIM_MIN + LIM_MAX (NC @12V -> opto)
        jx_min, jx_max = jx + 8.0, jx + 16.0
        gr_box(jx - 4, jy - 5, jx_max + 6, jy + PITCH + 5, "F.SilkS")
        gr_text(f"TRUC{mi + 1} MOT+LIM NC", jx - 3, jy - 6.5, "F.SilkS", 0.85)
        gr_text(f"{jref} MOT  {jmin} MIN  {jmax} MAX", jx - 3, jy + PITCH + 6.5, "F.SilkS", 0.7)

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

        # Routes: +12V/GND; IN from ESP32; OUT via to TOP jack; limit SW to opto
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
        # Limit +12V and SW -> U4 IN (F.Cu / via)
        for atx, neti, ch in [
            (jx_min, nmin, 2 * mi),
            (jx_max, nmax, 2 * mi + 1),
        ]:
            p12 = (atx, jy)
            psw = (atx, jy + PITCH)
            track(p12[0], p12[1], p12[0], oy + 20.0, 1, "F.Cu", 0.5)
            track(p12[0], oy + 20.0, ox + 20.0, oy + 20.0, 1, "F.Cu", 0.5)
            # SW to opto U4 IN pad (field row)
            upt = pad_world(ox4, oy4, rot4, xs_opto[ch + 2], -hx_o)
            via(psw[0], psw[1], neti, 0.4, 0.8)
            xlane = ox + bw - 4.0 - ch * 1.2
            track(psw[0], psw[1], xlane, psw[1], neti, "F.Cu", 0.35)
            track(xlane, psw[1], xlane, upt[1], neti, "F.Cu", 0.35)
            track(xlane, upt[1], upt[0], upt[1], neti, "F.Cu", 0.35)

'''
        # Also need to remove duplicate route block that was before TOP motor jack
        # The old code had routes AFTER the motor jack. Looking at structure:
        # 1) L298N footprint
        # 2) TOP motor jack  
        # 3) Routes including p_vs...
        # My new_top includes routes. But old code still has routes BEFORE marker_start!
        
        # Find routes block before TOP motor - remove duplicate by cutting from "# Routes:" before TOP
        # Actually looking at original: Routes come AFTER motor jack. So marker_start to marker_end includes jack+routes.
        # But wait - looking at my earlier read, order is:
        # TOP motor jack ... a(")") for footprint
        # # Routes: ... track motor
        # So marker_start through motor track end is correct.
        # BUT there's also earlier:
        #        # Routes: +12V/GND...
        # that starts AFTER motor jack in original. Good.

        # Problem: between L298N footprint end and TOP motor jack there is nothing.
        # After my replace, we still have OLD route block that starts with "# Routes:" BEFORE we replaced?
        # Looking at original lines 3062-3097 - routes are AFTER motor jack, included in our replace range.
        # But wait - in the file I read, order is:
        # 3013 TOP motor
        # 3062 Routes
        # So marker_start to marker_end covers both. Good.
        
        # However NEW code also has duplicate - I included routes in new_top but the OLD code between
        # footprint and TOP motor doesn't have routes. The section BEFORE marker_start ends with a(")") of L298N.
        # Then TOP motor. Then routes. So we need to NOT leave the old "# Routes" that was after motor...
        # which is inside the replace range. Good.

        # One issue: old code had routes block that started with p_vs AFTER motor - we're replacing that.
        # But ALSO looking at 3062 - there was a routes section. And BEFORE my new_top I had already
        # the routes in the original AFTER jack. Replace covers jack+routes.

        # CRITICAL: original also has this BETWEEN footprint and TOP:
        # Actually no routes between them.
        
        # Another issue: new_top still references code that was BEFORE marker - the old
        # "# Routes:" block starting at 3062 is inside replace. But lines 3062-3073 were
        # DUPLICATE of what I'm putting in new_top - and the OLD file has routes AFTER jack
        # starting with "# Routes: +12V/GND from via-farm" then ALSO the motor routes.
        # Wait - looking again at read output 3062-3097 - that's AFTER motor jack.
        # But ALSO 3062 says routes including p_vs - and there's NO separate routes before TOP.
        # However in the FIRST version there was routes after jack only.
        
        # Hmm but looking at 3062 in the read - the routes come right after motor jack a(")").
        # There's ALSO earlier in the conversation an older structure where routes were after.
        # Fine.

        # BUT: looking at current file around 3060 - the routes block includes p_vs computation
        # that DUPLICATES - and BEFORE the TOP motor jack in current file... Let me re-read.

        # From earlier read 3055-3097:
        # motor pads end a(")")
        # # Routes: ...
        # So currently Routes are AFTER motor jack. marker_start is "# TOP motor jack".
        # So range includes TOP jack AND we need to include Routes until last motor track.
        # marker_end is the last motor track. Good - Routes are between start and end.

        t = t[:i0] + new_top + t[i1 + len("        track(jmm[0] + 2.0, jmm[1], jmm[0], jmm[1], nmb, \"F.Cu\", 0.6)\n") :]
        # This leaves "\n    a(\")\")" from marker_end remnant... 
        # i1 points to start of marker_end. We want to keep from a(")") onward.
        # marker_end = '        track(...)\n\n    a(")")'
        # So after replace, continue from '    a(")")'
        pass

    # Fix the PCB replace more carefully
    # Re-read after partial? Let's do PCB replace in a cleaner second pass below.

    # Update J4 silk
    t = t.replace(
        'gr_text("GND VCC IN1-8 cach ly", j4x + 8, j4y + 1.2, "F.SilkS", 0.7)',
        'gr_text("IN1-6=hanh trinh; IN7-8 free", j4x + 8, j4y + 1.2, "F.SilkS", 0.65)',
        1,
    )

    # Stitch GND_I to GND on PCB
    if "GND_I stitch shared 12V" not in t:
        t = t.replace(
            '    track(u1_gnd_l[0], u4_gndo[1], u1_gnd_l[0], u1_gnd_l[1], 2, "B.Cu", 0.5)\n'
            "    # --- 3x L298N BOTTOM",
            '    track(u1_gnd_l[0], u4_gndo[1], u1_gnd_l[0], u1_gnd_l[1], 2, "B.Cu", 0.5)\n'
            "    # GND_I stitch shared 12V (limit NC loop uses +12V / GND_I)\n"
            "    u4_gndi = pad_world(ox4, oy4, rot4, xs_opto[0], -hx_o)\n"
            '    track(u4_gndi[0], u4_gndi[1], u1_gnd_l[0], u4_gndi[1], 33, "B.Cu", 0.5)\n'
            "    # merge field GND_I onto system GND for shared 12V limits\n"
            '    track(u4_gndi[0], u4_gndi[1], u4_gndo[0], u4_gndi[1], 2, "B.Cu", 0.5)\n'
            "    # --- 3x L298N BOTTOM",
            1,
        )
        # Wait - net 33 is OPTO_GND_I and net 2 is GND - can't connect different nets with a track
        # in KiCad without short. Better: assign U4 GND_I pad to net 2 (GND) instead of 33,
        # and J4 GND_I also to GND. Or keep 33 and change all GND_I to net 2.

    # Better approach: change in_nets[0] from (33, "/OPTO_GND_I") to (2, "GND")
    t = t.replace(
        '    in_nets = [\n'
        '        (33, "/OPTO_GND_I"),\n'
        '        (24, "/OPTO_VCC_I"),',
        '    in_nets = [\n'
        '        (2, "GND"),  # shared 12V field for NC limits (was /OPTO_GND_I)\n'
        '        (24, "/OPTO_VCC_I"),',
        1,
    )

    # README
    old_readme_axes = """| U5 | J5 M+/M- | IO21 / IO22 | Vs=+12V |
| U6 | J6 M+/M- | IO23 / IO13 | Vs=+12V |
| U7 | J7 M+/M- | IO12 / IO14 | Vs=+12V |

ENA: de jumper tren module (full enable). Moi L298N dung channel A (OUT1/OUT2).
GA12-N20: 1 dong co / jack 2 chan mat tren."""

    new_readme_axes = """| Truc | Driver | Nhom jack TOP | Motor GPIO | Limit -> Opto |
|------|--------|---------------|------------|---------------|
| 1 | U5 | **J5** MOT, **J8** MIN, **J9** MAX | IO21/22 | IN1/IN2 (GPIO15/2) |
| 2 | U6 | **J6** MOT, **J10** MIN, **J11** MAX | IO23/13 | IN3/IN4 (GPIO4/16) |
| 3 | U7 | **J7** MOT, **J12** MIN, **J13** MAX | IO12/14 | IN5/IN6 (GPIO17/5) |

ENA: jumper tren module. Channel A (OUT1/OUT2).

### Cong tac hanh trinh (NC, 12V, opto)

```
+12V --[NC limit SW]-- jack SW -- OPTO_INx -- LED -- GND (field = system GND)
```

- Thuong dong (NC) de chong nhieu: cham min/max → mo mach → opto tat.
- Moi truc: 2 giac 2 chan (+12V / SW) gom silk voi giac motor.
- J4 IN7/IN8 con trong; IN1-6 dung cho hanh trinh (co the song song J4)."""

    if old_readme_axes in t:
        t = t.replace(old_readme_axes, new_readme_axes, 1)

    t = t.replace(
        "| **Top** | J2 NEMA17, J3 sensor, J4 OPTO, **J5/J6/J7 GA12-N20** |",
        "| **Top** | J2 NEMA, J3 sensor, J4 OPTO, **3 nhom TRUC (MOT+MIN+MAX)** |",
        1,
    )

    GEN.write_text(t, encoding="utf-8")
    print("Pass1 written — now fix PCB top block if needed")


if __name__ == "__main__":
    main()
