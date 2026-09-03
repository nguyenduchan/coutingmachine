#!/usr/bin/env python3
"""Patch gen_power_carrier.py: J30/J31 sockets + motor-kick passives."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
P = ROOT / "gen_power_carrier.py"
text = P.read_text(encoding="utf-8")


def L(*lines: str) -> str:
    return "\n".join(lines) + "\n"


# Tab escape for KiCad sexpr strings inside gen_power_carrier source:
# we need the characters: a(f'\t(footprint ...
TAB = "\\t"  # two chars backslash+t in output source

J30_BLOCK = L(
    "    # --- J30 POWER_PROT female (M1 plugs: D3+F1+D1 live on daughter) ---",
    "    # Path: J1.+12V_RAW -> J30.1 -> [M1] -> J30.3=+12V ; J30.2/4=GND",
    '    j30x, j30y = FP["j30x"], FP["j30y"]',
    f'    a(f\'{TAB}(footprint "ESP32_Carrier:{{POWER_PROT_FP}}"\')',
    f"    a('{TAB}{TAB}(layer \"F.Cu\")')",
    f'    a(f\'{TAB}{TAB}(uuid "{{uid()}}")\')',
    f'    a(f"{TAB}{TAB}(at {{j30x}} {{j30y}})")',
    f"    a('{TAB}{TAB}(property \"Reference\" \"J30\"')",
    f"    a('{TAB}{TAB}{TAB}(at 0 -2.8 0)')",
    f"    a('{TAB}{TAB}{TAB}(layer \"F.SilkS\")')",
    f'    a("{TAB}{TAB}{TAB}(effects (font (size 0.9 0.9) (thickness 0.12)))")',
    f'    a(f\'{TAB}{TAB}{TAB}(uuid "{{uid()}}")\')',
    f'    a("{TAB}{TAB})")',
    f"    a('{TAB}{TAB}(property \"Value\" \"M1_POWER_PROT\"')",
    f'    a(f\'{TAB}{TAB}{TAB}(at 0 {{(POWER_PROT_PINS - 1) * PITCH + 2.8}} 0)\')',
    f"    a('{TAB}{TAB}{TAB}(layer \"F.Fab\")')",
    f'    a("{TAB}{TAB}{TAB}(effects (font (size 0.7 0.7) (thickness 0.1)))")',
    f'    a(f\'{TAB}{TAB}{TAB}(uuid "{{uid()}}")\')',
    f'    a("{TAB}{TAB})")',
    f'    a("{TAB}{TAB}(attr through_hole)")',
    '    fp_silk_rect(-1.8, -1.8, 1.8, (POWER_PROT_PINS - 1) * PITCH + 1.8, "F.SilkS")',
    "    for i, (num, name) in enumerate(POWER_PROT_HEADER):",
    "        y = i * PITCH",
    "        net_map = {",
    '            "RAW": (57, "+12V_RAW"),',
    '            "GND": (2, "GND"),',
    '            "+12V": (1, "+12V"),',
    "        }",
    "        ni, nn = net_map[name]",
    f'        a(f\'{TAB}{TAB}(fp_text user "{{name}}"\')',
    f'        a(f"{TAB}{TAB}{TAB}(at 3.5 {{y}} 0)")',
    f"        a('{TAB}{TAB}{TAB}(layer \"F.SilkS\")')",
    f"        a('{TAB}{TAB}{TAB}(effects (font (size 0.65 0.65) (thickness 0.1)) (justify left))')",
    f'        a(f\'{TAB}{TAB}{TAB}(uuid "{{uid()}}")\')',
    f'        a("{TAB}{TAB})")',
    '        shape = "rect" if i == 0 else "circle"',
    f'        a(f\'{TAB}{TAB}(pad "{{num}}" thru_hole {{shape}}\')',
    f'        a(f"{TAB}{TAB}{TAB}(at 0 {{y}})")',
    f'        a("{TAB}{TAB}{TAB}(size 1.7 1.7)")',
    f'        a("{TAB}{TAB}{TAB}(drill 1.0)")',
    f"        a('{TAB}{TAB}{TAB}(layers \"*.Cu\" \"*.Mask\")')",
    f'        a(f\'{TAB}{TAB}{TAB}(net {{ni}} "{{nn}}")\')',
    f'        a(f\'{TAB}{TAB}{TAB}(uuid "{{uid()}}")\')',
    f'        a("{TAB}{TAB})")',
    f'    a("{TAB})")',
    '    gr_text("J30 M1 POWER_PROT (D3+F1+D1)", j30x - 6, j30y - 4.5, "F.SilkS", 0.7)',
    "",
)

start = text.find("    # --- D3 Schottky reverse-polarity (series) + F1 PTC + D1 TVS ---")
end = text.find("    # --- U2 MP1584EN BOTTOM ---")
if start < 0 or end < 0:
    raise SystemExit(f"power block markers missing start={start} end={end}")
text = text[:start] + J30_BLOCK + text[end:]

text = text.replace(
    '    f1x, f1y = FP["f1x"], FP["f1y"]\n    d1x, d1y = FP["d1x"], FP["d1y"]\n',
    '    f1x, f1y = FP["f1x"], FP["f1y"]  # legacy; +12V farm uses J30\n',
)

old_pads = """    j1_raw = pad_world(jx, jy, j1_rot, -TB_PITCH / 2, 0)
    j1_12 = pad_world(f1x, f1y, rot, 2.55, 0)  # +12V after F1 PTC (alias for farm/star)
    j1_gnd = pad_world(jx, jy, j1_rot, TB_PITCH / 2, 0)
    d3_a = pad_world(d3x, d3y, rot, -3.75, 0)   # anode ← RAW
    d3_k = pad_world(d3x, d3y, rot, 3.75, 0)    # cathode → PRE
    f1_in = pad_world(f1x, f1y, rot, -2.55, 0)  # +12V_PRE
    d1_gnd = pad_world(d1x, d1y, rot, -3.75, 0)
    d1_12v = pad_world(d1x, d1y, rot, 3.75, 0)"""

new_pads = """    j1_raw = pad_world(jx, jy, j1_rot, -TB_PITCH / 2, 0)
    j1_gnd = pad_world(jx, jy, j1_rot, TB_PITCH / 2, 0)
    # J30: pin1 RAW, pin2 GND, pin3 +12V (protected), pin4 GND
    j30_raw = (j30x, j30y)
    j30_gnd = (j30x, j30y + PITCH)
    j1_12 = (j30x, j30y + 2 * PITCH)  # +12V after M1
    j30_gnd2 = (j30x, j30y + 3 * PITCH)"""

if old_pads not in text:
    raise SystemExit("pad block not found")
text = text.replace(old_pads, new_pads)

old_wire = """    # === +12V 3A via farm: AFTER D3 + F1 (not raw J1) ===
    # J1 RAW → D3 → +12V_PRE → F1 → +12V farm; D1 TVS on +12V
    # Keep RAW/12V/GND local around J1 — no long diagonals.
    y_raw = j1_raw[1] - 3.0
    track_h(j1_raw[0], d3_a[0], y_raw, 57, 1.5)
    via(d3_a[0], y_raw, 57, 0.4, 0.8)
    track_v(d3_a[0], y_raw, d3_a[1], 57, 1.5)
    # D3 cathode → F1 in on +12V_PRE
    track_h(d3_k[0], f1_in[0], d3_k[1], 68, 1.5)
    track_v(f1_in[0], d3_k[1], f1_in[1], 68, 1.5)
    track_v(j1_12[0], j1_12[1], d1_12v[1], 1, 1.0)
    via(j1_12[0], d1_12v[1], 1, 0.4, 0.8)
    track_h(j1_12[0], d1_12v[0], d1_12v[1], 1, 0.8)
    # GND to TVS on offset Y — same pad-row Y would short across +12V stub
    y_d1g = d1_gnd[1] + 2.0
    track_v(j1_gnd[0], j1_gnd[1], y_d1g, 2, 0.8)
    via(j1_gnd[0], y_d1g, 2, 0.4, 0.8)
    track_h(j1_gnd[0], d1_gnd[0], y_d1g, 2, 0.8)
    via(d1_gnd[0], y_d1g, 2, 0.4, 0.8)
    track_v(d1_gnd[0], y_d1g, d1_gnd[1], 2, 0.8)

    # Via farm immediately WEST of F1 (short stub — do not span TFT corridor)
    farm_cx = j1_12[0] - 4.0
    farm_cy = j1_12[1]"""

new_wire = """    # === +12V 3A via farm: AFTER J30/M1 (not raw J1) ===
    # J1 RAW → J30.1 → [M1 D3+F1+D1] → J30.3=+12V farm
    y_raw = j1_raw[1] - 3.0
    track_h(j1_raw[0], j30_raw[0], y_raw, 57, 1.5)
    via(j30_raw[0], y_raw, 57, 0.4, 0.8)
    track_v(j30_raw[0], y_raw, j30_raw[1], 57, 1.5)
    # GND star → J30 pins 2+4
    y_jg = j1_gnd[1] + 2.0
    track_v(j1_gnd[0], j1_gnd[1], y_jg, 2, 0.8)
    via(j1_gnd[0], y_jg, 2, 0.4, 0.8)
    track_h(j1_gnd[0], j30_gnd[0], y_jg, 2, 0.8)
    via(j30_gnd[0], y_jg, 2, 0.4, 0.8)
    track_v(j30_gnd[0], y_jg, j30_gnd[1], 2, 0.8)
    track_v(j30_gnd[0], j30_gnd[1], j30_gnd2[1], 2, 0.5)

    # Via farm immediately WEST of J30.+12V
    farm_cx = j1_12[0] - 4.0
    farm_cy = j1_12[1]"""

if old_wire not in text:
    raise SystemExit("power wire block not found")
text = text.replace(old_wire, new_wire)

J31_BLOCK = L(
    "    # ===== J31 OPTO4 female (M2: 4xPC817 + 2k2/10k on daughter) =====",
    '    j31x, j31y = FP["j31x"], FP["j31y"]',
    "    j31_nets = [",
    '        (25, "/OPTO_IN1", "IN1"),',
    '        (26, "/OPTO_IN2", "IN2"),',
    '        (27, "/OPTO_IN3", "IN3"),',
    '        (28, "/OPTO_IN4", "IN4"),',
    '        (46, "+12V_SNS", "SNS"),',
    '        (2, "GND", "GND"),',
    '        (16, "/OPTO_OUT1", "OUT1"),',
    '        (17, "/OPTO_OUT2", "OUT2"),',
    '        (18, "/OPTO_OUT3", "OUT3"),',
    '        (19, "/OPTO_OUT4", "OUT4"),',
    '        (4, "+3V3", "3V3"),',
    "    ]",
    f'    a(f\'{TAB}(footprint "ESP32_Carrier:{{OPTO4_FP}}"\')',
    f"    a('{TAB}{TAB}(layer \"F.Cu\")')",
    f'    a(f\'{TAB}{TAB}(uuid "{{uid()}}")\')',
    f'    a(f"{TAB}{TAB}(at {{j31x}} {{j31y}})")',
    f"    a('{TAB}{TAB}(property \"Reference\" \"J31\"')",
    f"    a('{TAB}{TAB}{TAB}(at 0 -2.8 0)')",
    f"    a('{TAB}{TAB}{TAB}(layer \"F.SilkS\")')",
    f'    a("{TAB}{TAB}{TAB}(effects (font (size 0.9 0.9) (thickness 0.12)))")',
    f'    a(f\'{TAB}{TAB}{TAB}(uuid "{{uid()}}")\')',
    f'    a("{TAB}{TAB})")',
    f"    a('{TAB}{TAB}(property \"Value\" \"M2_OPTO4\"')",
    f'    a(f\'{TAB}{TAB}{TAB}(at 0 {{(OPTO4_PINS - 1) * PITCH + 2.8}} 0)\')',
    f"    a('{TAB}{TAB}{TAB}(layer \"F.Fab\")')",
    f'    a("{TAB}{TAB}{TAB}(effects (font (size 0.7 0.7) (thickness 0.1)))")',
    f'    a(f\'{TAB}{TAB}{TAB}(uuid "{{uid()}}")\')',
    f'    a("{TAB}{TAB})")',
    f'    a("{TAB}{TAB}(attr through_hole)")',
    '    fp_silk_rect(-1.8, -1.8, 1.8, (OPTO4_PINS - 1) * PITCH + 1.8, "F.SilkS")',
    "    for i, (ni, nn, lab) in enumerate(j31_nets):",
    "        y = i * PITCH",
    f'        a(f\'{TAB}{TAB}(fp_text user "{{lab}}"\')',
    f'        a(f"{TAB}{TAB}{TAB}(at 3.5 {{y}} 0)")',
    f"        a('{TAB}{TAB}{TAB}(layer \"F.SilkS\")')",
    f"        a('{TAB}{TAB}{TAB}(effects (font (size 0.6 0.6) (thickness 0.1)) (justify left))')",
    f'        a(f\'{TAB}{TAB}{TAB}(uuid "{{uid()}}")\')',
    f'        a("{TAB}{TAB})")',
    '        shape = "rect" if i == 0 else "circle"',
    f'        a(f\'{TAB}{TAB}(pad "{{i + 1}}" thru_hole {{shape}}\')',
    f'        a(f"{TAB}{TAB}{TAB}(at 0 {{y}})")',
    f'        a("{TAB}{TAB}{TAB}(size 1.7 1.7)")',
    f'        a("{TAB}{TAB}{TAB}(drill 1.0)")',
    f"        a('{TAB}{TAB}{TAB}(layers \"*.Cu\" \"*.Mask\")')",
    f'        a(f\'{TAB}{TAB}{TAB}(net {{ni}} "{{nn}}")\')',
    f'        a(f\'{TAB}{TAB}{TAB}(uuid "{{uid()}}")\')',
    f'        a("{TAB}{TAB})")',
    f'    a("{TAB})")',
    '    gr_text("J31 M2 OPTO4 (PC817x4)", j31x - 8, j31y - 4.5, "F.SilkS", 0.7)',
    "",
    "    def _opto_in_pad_ch(ch_i: int):",
    '        """World coords of J31 INx pad (pins 1-4)."""',
    "        return (j31x, j31y + ch_i * PITCH)",
    "",
)

s2 = text.find("    # ===== Discrete PC817 ×4 + 2k2 LED + 10k pull-up (BOTTOM) =====")
e2 = text.find("    # --- U5-U7 ULN2003 driver modules; HOME endstop J8/J10/J12 ---")
if s2 < 0 or e2 < 0:
    raise SystemExit(f"opto markers missing {s2} {e2}")
text = text[:s2] + J31_BLOCK + text[e2:]

old_power = """    power_boxes = [
        local_rect_world_aabb(jx, jy, j1_rot, -5.5, -4.5, 5.5, 4.5),
        local_rect_world_aabb(d3x, d3y, rot, -4.0, -2.5, 4.0, 2.5),
        local_rect_world_aabb(f1x, f1y, rot, -5.0, -5.0, 5.0, 5.0),
        local_rect_world_aabb(d1x, d1y, rot, -4.0, -2.5, 4.0, 2.5),
        local_rect_world_aabb(
            mx, my, rot,
            -MP1584_W / 2 - 0.5, -MP1584_H / 2 - 0.5,
            MP1584_W / 2 + 0.5, MP1584_H / 2 + 0.5,
        ),
        local_rect_world_aabb(r10x, r10y, 0, -2.0, -1.2, 2.0, 1.2),
        local_rect_world_aabb(c10x, c10y, 0, -2.2, -2.2, 2.2, 2.2),
        local_rect_world_aabb(c11x, c11y, 0, -2.2, -2.2, 2.2, 2.2),
    ]"""
new_power = """    power_boxes = [
        local_rect_world_aabb(jx, jy, j1_rot, -5.5, -4.5, 5.5, 4.5),
        _hdr_aabb(j30x, j30y, POWER_PROT_PINS),
        local_rect_world_aabb(
            mx, my, rot,
            -MP1584_W / 2 - 0.5, -MP1584_H / 2 - 0.5,
            MP1584_W / 2 + 0.5, MP1584_H / 2 + 0.5,
        ),
        local_rect_world_aabb(r10x, r10y, 0, -2.0, -1.2, 2.0, 1.2),
        local_rect_world_aabb(c10x, c10y, 0, -2.2, -2.2, 2.2, 2.2),
        local_rect_world_aabb(c11x, c11y, 0, -2.2, -2.2, 2.2, 2.2),
    ]"""
if old_power not in text:
    raise SystemExit("power_boxes not found")
text = text.replace(old_power, new_power)

old_opto = """    opto_boxes = []
    for i, _ch in enumerate(OPTO_CH):
        col, row = i % 4, i // 4
        ux = opto_origin[0] + col * opto_col_pitch
        uy = opto_origin[1] + row * opto_row_pitch
        silk_hx = DIP4_BODY_W / 2 + 1.2
        opto_boxes.append(local_rect_world_aabb(
            ux, uy, rot4,
            -silk_hx, -DIP4_BODY_L / 2 - 0.5, silk_hx, DIP4_BODY_L / 2 + 0.5,
        ))
        opto_boxes.append(_axial_aabb(ux - 3.5, uy - 8.5))
        opto_boxes.append(_axial_aabb(ux + 3.5, uy + 8.5))"""
new_opto = """    opto_boxes = [
        _hdr_aabb(j31x, j31y, OPTO4_PINS),
    ]"""
if old_opto not in text:
    raise SystemExit("opto_boxes not found")
text = text.replace(old_opto, new_opto)

text = text.replace(
    'cluster_outline("1: POWER  J1+D3+F1+D1+U2+RC"',
    'cluster_outline("1: POWER  J1+J30(M1)+U2+RC"',
)
text = text.replace(
    'cluster_outline("4: OPTO  U41-U44 PC817 + R2k2/10k"',
    'cluster_outline("4: OPTO  J31(M2 OPTO4)"',
)

text = text.replace(
    """    _axial2("Diode_TVS_DO41", "D2", "1N5819", j16x + 8.0, j16y + 2.0,
            (1, "+12V"), (61, "/BLW_RET"), 0.9, 1.7, "D2 K(band)->+12V")""",
    """    _axial2("Diode_TVS_DO41", "D2", "SS24", j16x + 8.0, j16y + 2.0,
            (1, "+12V"), (61, "/BLW_RET"), 0.9, 1.7, "D2 SS24 flyback K->+12V")
    # D4 TVS across blower rail (clamp inductive kick)
    _axial2("Diode_TVS_DO41", "D4", "P6KE15A", j16x + 8.0, j16y + 2.0 + 6.0,
            (2, "GND"), (1, "+12V"), 0.9, 1.7, "D4 TVS blower +12V")""",
)

old_bulk = """    # --- Bulk: C20 SE of TMC; C21 near AXIS1 ULN COM ---
    bulk_places = [
        ("C20", "CP_Radial_D8_470u_25V", "470u/25V", tx + 12.0, ty + 16.0, "TMC"),
        ("C21", "CP_Radial_D6_100u_25V", "100u/25V", FP["c21x"], FP["c21y"], "ULN"),
    ]"""
new_bulk = """    # --- Bulk: C20 SE of TMC; C21 220u ULN ---
    bulk_places = [
        ("C20", "CP_Radial_D8_470u_25V", "470u/25V", tx + 12.0, ty + 16.0, "TMC"),
        ("C21", "CP_Radial_D6_100u_25V", "220u/25V", FP["c21x"], FP["c21y"], "ULN"),
    ]"""
if old_bulk not in text:
    raise SystemExit("bulk_places not found")
text = text.replace(old_bulk, new_bulk)

marker_after_bulk = """        track_v(pgdb[0], ygdb, pgdb[1], 2, 1.0)

    # ========== CLUSTER OUTLINES (all TOP / Eco1 cyan) =========="""
c24 = L(
    "        track_v(pgdb[0], ygdb, pgdb[1], 2, 1.0)",
    "",
    "    # HF ceramics near motor supplies (motor inductive kick)",
    "    for cref, cx, cy, ctag in (",
    '        ("C24", tx + 12.0, ty + 22.0, "TMC_HF"),',
    '        ("C25", FP["c21x"] + 8.0, FP["c21y"], "ULN_HF"),',
    "    ):",
    '        gr_text(f"{cref} 100n {ctag}", cx - 3, cy - 2.5, "Cmts.User", 0.55)',
    f"        a('{TAB}(footprint \"ESP32_Carrier:C_0805_100n\"')",
    f"        a('{TAB}{TAB}(layer \"F.Cu\")')",
    f'        a(f\'{TAB}{TAB}(uuid "{{uid()}}")\')',
    f'        a(f"{TAB}{TAB}(at {{cx}} {{cy}})")',
    f'        a(f\'{TAB}{TAB}(property "Reference" "{{cref}}"\')',
    f"        a('{TAB}{TAB}{TAB}(at 0 -1.8 0)')",
    f"        a('{TAB}{TAB}{TAB}(layer \"F.SilkS\")')",
    f"        a('{TAB}{TAB}{TAB}(effects (font (size 0.65 0.65) (thickness 0.1)))')",
    f'        a(f\'{TAB}{TAB}{TAB}(uuid "{{uid()}}")\')',
    f'        a("{TAB}{TAB})")',
    f"        a('{TAB}{TAB}(property \"Value\" \"100n\"')",
    f"        a('{TAB}{TAB}{TAB}(at 0 1.8 0)')",
    f"        a('{TAB}{TAB}{TAB}(layer \"F.SilkS\")')",
    f"        a('{TAB}{TAB}{TAB}(effects (font (size 0.6 0.6) (thickness 0.1)))')",
    f'        a(f\'{TAB}{TAB}{TAB}(uuid "{{uid()}}")\')',
    f'        a("{TAB}{TAB})")',
    f'        a("{TAB}{TAB}(attr smd)")',
    f"        a('{TAB}{TAB}(pad \"1\" smd roundrect (at -0.95 0) (size 0.9 1.25)')",
    f"        a('{TAB}{TAB}{TAB}(layers \"F.Cu\" \"F.Paste\" \"F.Mask\")')",
    f"        a('{TAB}{TAB}{TAB}(net 1 \"+12V\")')",
    f'        a(f\'{TAB}{TAB}{TAB}(uuid "{{uid()}}")\')',
    f'        a("{TAB}{TAB})")',
    f"        a('{TAB}{TAB}(pad \"2\" smd roundrect (at 0.95 0) (size 0.9 1.25)')",
    f"        a('{TAB}{TAB}{TAB}(layers \"F.Cu\" \"F.Paste\" \"F.Mask\")')",
    f"        a('{TAB}{TAB}{TAB}(net 2 \"GND\")')",
    f'        a(f\'{TAB}{TAB}{TAB}(uuid "{{uid()}}")\')',
    f'        a("{TAB}{TAB})")',
    f'        a("{TAB})")',
    "",
    "    # ========== CLUSTER OUTLINES (all TOP / Eco1 cyan) ==========",
)
if marker_after_bulk not in text:
    raise SystemExit("after-bulk marker not found")
text = text.replace(marker_after_bulk, c24.rstrip("\n") + "\n")

text = text.replace(
    """        _axial_aabb(j16x - 8.0, j16y + 2.0),
        _axial_aabb(j16x + 8.0, j16y + 2.0),
    ]""",
    """        _axial_aabb(j16x - 8.0, j16y + 2.0),
        _axial_aabb(j16x + 8.0, j16y + 2.0),
        _axial_aabb(j16x + 8.0, j16y + 8.0),
    ]""",
)
text = text.replace(
    """        _radial_aabb(tx + 12.0, ty + 16.0, 4.4, 1.75),
    ]""",
    """        _radial_aabb(tx + 12.0, ty + 16.0, 4.4, 1.75),
        local_rect_world_aabb(tx + 12.0, ty + 22.0, 0, -1.5, -1.0, 1.5, 1.0),
    ]""",
)
text = text.replace(
    """        if i == 0:
            boxes.append(_radial_aabb(c21x, c21y, 3.55, 1.25))""",
    """        if i == 0:
            boxes.append(_radial_aabb(c21x, c21y, 3.55, 1.25))
            boxes.append(local_rect_world_aabb(c21x + 8.0, c21y, 0, -1.5, -1.0, 1.5, 1.0))""",
)

text = text.replace(
    '        write_pin_header_footprint(4, "PinHeader_1x04_BUP30S", ["+12V", "GND", "OUT", "CTRL"]),\n',
    '        write_pin_header_footprint(4, "PinHeader_1x04_BUP30S", ["+12V", "GND", "OUT", "CTRL"]),\n'
    "        write_pin_header_footprint(POWER_PROT_PINS, POWER_PROT_FP, [p[1] for p in POWER_PROT_HEADER]),\n"
    "        write_pin_header_footprint(OPTO4_PINS, OPTO4_FP, [p[1] for p in OPTO4_HEADER]),\n",
)

if "gen_submodules" not in text:
    text = text.replace(
        "    # E11.14 — every non-mount part must sit in an Eco1 cluster\n",
        "    from gen_submodules import main as gen_submodules_main\n"
        "    gen_submodules_main()\n"
        "    # E11.14 — every non-mount part must sit in an Eco1 cluster\n",
    )

text = text.replace(
    "  12V-3A PSU --J1--> D3 Schottky (reverse) --> F1 PTC --> +12V (D1 TVS to GND)",
    "  12V-3A PSU --J1--> J30(M1: D3+F1+D1) --> +12V ; field via J31(M2 OPTO4)",
)

# Sanity: J30 a() lines must contain backslash-t
idx = text.find("J30 POWER_PROT")
sample = text[idx : idx + 350]
if "a(f'\\t(footprint" not in sample:
    raise SystemExit("bad J30 escape:\n" + sample)

P.write_text(text, encoding="utf-8")
print("OK patched", P, "bytes", len(text))
