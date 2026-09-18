#!/usr/bin/env python3
"""Swap JLC-matched footprints on the live PCB and fan out U2.

Does not regenerate the board. U2 SOT-23-8 → genuine MP1584EN SOIC-8-EP
(pinout remap), C3/C10/C21/C20B → D6.3x8 (same pads), add R_FREQ 100k.
"""
from __future__ import annotations

import os
import re
import uuid
from pathlib import Path

from pcb_parse import NetTable, pad_net, seg_net

HERE = Path(__file__).resolve().parent
PCB = HERE / "esp32_baseboard.kicad_pcb"
PRETTY = HERE / "libraries" / "ESP32_Carrier.pretty"
OX, OY, BW, BH = 50.0, 50.0, 180.0, 120.0

U2_AT = (123.125, 102.125)
R_FREQ_AT = (128.90, 106.80)
CAP_REFS = ("C3", "C10", "C21", "C20B")
CAP_VALUES = {
    "C3": "47u/50V",
    "C10": "47u/50V",
    "C21": "47u/50V",
    "C20B": "47u/50V",
}

# MP1584EN SOIC-8-EP (datasheet top view)
U2_NETS = {
    "1": "/BUCK_SW",
    "3": "/BUCK_COMP",
    "4": "/BUCK_FB",
    "5": "GND",
    "6": "/BUCK_FREQ",
    "7": "+24V",
    "8": "/BUCK_BS",
    "9": "GND",
}
# Pad 2 = EN, floating (internal pull-up). Abs max 6 V — not VIN.

HIT_MM = 0.85


def uid() -> str:
    return str(uuid.uuid4())


def _block(text: str, start: int) -> str:
    d, i = 0, start
    while i < len(text):
        if text[i] == "(":
            d += 1
        elif text[i] == ")":
            d -= 1
            if d == 0:
                return text[start : i + 1]
        i += 1
    raise ValueError("unbalanced")


def find_fp(text: str, ref: str) -> tuple[int, str]:
    for m in re.finditer(r'\n\t\(footprint "', text):
        blk = _block(text, m.start() + 1)
        if f'(property "Reference" "{ref}"' in blk:
            return m.start() + 1, blk
    raise SystemExit(f"{ref} not found")


def instance_wrap(fp_name: str, at: tuple[float, float], rot: float,
                  ref: str, value: str, pad_nets: dict[str, str],
                  silk_extra: str = "") -> str:
    mod = (PRETTY / f"{fp_name}.kicad_mod").read_text(encoding="utf-8").strip()
    inner = mod[mod.find("\n") + 1 : -1].rstrip()
    keep: list[str] = []
    i = 0
    while i < len(inner):
        p = inner.find("(", i)
        if p < 0:
            break
        blk = _block(inner, p)
        if not (blk.startswith("(property ") or blk.startswith("(version ")
                or blk.startswith("(generator ") or blk.startswith("(layer ")
                or blk.startswith("(descr ") or blk.startswith("(tags ")):
            keep.append(blk)
        i = p + len(blk)
    body = "\n\t\t".join(keep)
    for num, net in pad_nets.items():
        body = re.sub(
            rf'(\(pad "{re.escape(num)}"[\s\S]*?\(layers [^)]+\))',
            rf'\1\n\t\t(net "{net}")',
            body,
            count=1,
        )
    rot_s = f" {rot:g}" if rot else ""
    extra = f"\n\t\t{silk_extra}" if silk_extra else ""
    return (
        f'\t(footprint "ESP32_Carrier:{fp_name}"\n'
        f'\t\t(layer "F.Cu")\n'
        f'\t\t(uuid "{uid()}")\n'
        f'\t\t(at {at[0]:g} {at[1]:g}{rot_s})\n'
        f'\t\t(property "Reference" "{ref}"\n'
        f'\t\t\t(at 0 -1.5 0)\n'
        f'\t\t\t(layer "F.SilkS")\n'
        f'\t\t\t(uuid "{uid()}")\n'
        f'\t\t\t(effects (font (size 0.8 0.8) (thickness 0.12))))\n'
        f'\t\t(property "Value" "{value}"\n'
        f'\t\t\t(at 0 1.5 0)\n'
        f'\t\t\t(layer "F.SilkS")\n'
        f'\t\t\t(uuid "{uid()}")\n'
        f'\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1))))\n'
        f'\t\t(attr smd)\n'
        f'\t\t{body}{extra}\n'
        f'\t)'
    )


def pad_xy(origin: tuple[float, float], local: tuple[float, float]) -> tuple[float, float]:
    return origin[0] + local[1 - 1], origin[1] + local[1]


def replace_fp(text: str, ref: str, new_blk: str) -> str:
    start, old = find_fp(text, ref)
    return text[:start] + new_blk + text[start + len(old):]


def strip_near_u2(text: str) -> str:
    """Drop segments whose endpoint sits on the old SOT-23-8 pads."""
    ux, uy = U2_AT
    old = [
        (ux - 1.1375, uy - 0.975),
        (ux - 1.1375, uy - 0.325),
        (ux - 1.1375, uy + 0.325),
        (ux - 1.1375, uy + 0.975),
        (ux + 1.1375, uy + 0.975),
        (ux + 1.1375, uy + 0.325),
        (ux + 1.1375, uy - 0.325),
        (ux + 1.1375, uy - 0.975),
    ]

    def hit(x: float, y: float) -> bool:
        return any((x - px) ** 2 + (y - py) ** 2 <= HIT_MM * HIT_MM for px, py in old)

    out = []
    i = 0
    n_drop = 0
    while True:
        p = text.find("\n\t(segment", i)
        if p < 0:
            out.append(text[i:])
            break
        out.append(text[i:p])
        blk = _block(text, p + 1)
        s = re.search(r"\(start\s+([-\d.]+)\s+([-\d.]+)\)", blk)
        e = re.search(r"\(end\s+([-\d.]+)\s+([-\d.]+)\)", blk)
        drop = False
        if s and e:
            drop = hit(float(s.group(1)), float(s.group(2))) or hit(
                float(e.group(1)), float(e.group(2))
            )
        if drop:
            n_drop += 1
        else:
            out.append("\n\t" + blk if False else text[p:p + 1 + len(blk)])
        i = p + 1 + len(blk)
    print(f"  stripped {n_drop} segments on old U2 pads")
    return "".join(out)


def seg(x1, y1, x2, y2, width, layer, net) -> str:
    if abs(x1 - x2) < 1e-6 and abs(y1 - y2) < 1e-6:
        return ""
    return (
        f'\n\t(segment\n'
        f'\t\t(start {x1:.4f} {y1:.4f})\n'
        f'\t\t(end {x2:.4f} {y2:.4f})\n'
        f'\t\t(width {width})\n'
        f'\t\t(layer "{layer}")\n'
        f'\t\t(net "{net}")\n'
        f'\t\t(uuid "{uid()}")\n'
        f'\t)'
    )


def via(x, y, net, size=0.8, drill=0.4) -> str:
    return (
        f'\n\t(via\n'
        f'\t\t(at {x:.4f} {y:.4f})\n'
        f'\t\t(size {size})\n'
        f'\t\t(drill {drill})\n'
        f'\t\t(layers "F.Cu" "B.Cu")\n'
        f'\t\t(net "{net}")\n'
        f'\t\t(uuid "{uid()}")\n'
        f'\t)'
    )


def manhattan(x1, y1, x2, y2, width, layer, net) -> str:
    if abs(x1 - x2) < 1e-6 or abs(y1 - y2) < 1e-6:
        return seg(x1, y1, x2, y2, width, layer, net)
    # jog in Y first (away from SOIC body for east-side pads)
    return (
        seg(x1, y1, x1, y2, width, layer, net)
        + seg(x1, y2, x2, y2, width, layer, net)
    )


def inject(text: str, block: str) -> str:
    idx = text.rstrip().rfind(")")
    return text[:idx] + block + "\n" + text[idx:]


def add_u2_fanout(text: str) -> str:
    ux, uy = U2_AT
    p = {
        "1": (ux - 2.475, uy - 1.905),  # SW
        "3": (ux - 2.475, uy + 0.635),  # COMP
        "4": (ux - 2.475, uy + 1.905),  # FB
        "5": (ux + 2.475, uy + 1.905),  # GND
        "6": (ux + 2.475, uy + 0.635),  # FREQ
        "7": (ux + 2.475, uy - 0.635),  # VIN
        "8": (ux + 2.475, uy - 1.905),  # BST
        "9": (ux, uy),                  # EP
    }
    rx, ry = R_FREQ_AT
    r1 = (rx - 0.95, ry)  # /BUCK_FREQ
    r2 = (rx + 0.95, ry)  # GND
    gnd_via = (127.70, 104.03)
    vin_via = (125.987, 108.214)  # existing +24V via at plane edge
    out = []
    # FREQ: U2.6 → R_FREQ.1
    out.append(manhattan(p["6"][0], p["6"][1], r1[0], r1[1], 0.25, "F.Cu", "/BUCK_FREQ"))
    # R_FREQ.2 → GND via
    out.append(manhattan(r2[0], r2[1], gnd_via[0], gnd_via[1], 0.25, "F.Cu", "GND"))
    # U2.5 GND → via → In1 plane
    out.append(seg(p["5"][0], p["5"][1], gnd_via[0], p["5"][1], 0.40, "F.Cu", "GND"))
    out.append(seg(gnd_via[0], p["5"][1], gnd_via[0], gnd_via[1], 0.40, "F.Cu", "GND"))
    out.append(via(*gnd_via, "GND"))
    # EP to same GND via (south then east)
    out.append(seg(p["9"][0], uy + 1.50, p["9"][0], 105.40, 0.40, "F.Cu", "GND"))
    out.append(seg(p["9"][0], 105.40, gnd_via[0], 105.40, 0.40, "F.Cu", "GND"))
    out.append(seg(gnd_via[0], 105.40, gnd_via[0], gnd_via[1], 0.40, "F.Cu", "GND"))
    # VIN → existing +24V via at y=108.214 (In2 plane starts here)
    out.append(seg(p["7"][0], p["7"][1], p["7"][0], vin_via[1], 0.50, "F.Cu", "+24V"))
    out.append(seg(p["7"][0], vin_via[1], vin_via[0], vin_via[1], 0.50, "F.Cu", "+24V"))
    # SW stub west toward D4/L1 (maze finishes)
    out.append(seg(p["1"][0], p["1"][1], p["1"][0] - 1.2, p["1"][1], 0.40, "F.Cu", "/BUCK_SW"))
    # BST stub west
    out.append(seg(p["8"][0], p["8"][1], p["8"][0] + 1.2, p["8"][1], 0.25, "F.Cu", "/BUCK_BS"))
    # COMP stub south
    out.append(seg(p["3"][0], p["3"][1], p["3"][0], p["3"][1] + 1.4, 0.25, "F.Cu", "/BUCK_COMP"))
    # FB stub south then east
    out.append(seg(p["4"][0], p["4"][1], p["4"][0], p["4"][1] + 1.6, 0.25, "F.Cu", "/BUCK_FB"))
    return inject(text, "".join(x for x in out if x))


def maze_repair(text: str) -> str:
    from maze_router import repair_open_pcb

    os.environ.setdefault("MAZE_EXPAND", "40000")
    for rnd in range(1, 4):
        text, repair = repair_open_pcb(text, OX, OY, BW, BH, uid_fn=uid)
        print(f"  maze {rnd}: +{len(repair.segments)} segs, {len(repair.failed)} failed")
        if not repair.segments:
            break
    return text


def apply_sch() -> None:
    sch = HERE / "esp32_baseboard.kicad_sch"
    t = sch.read_text(encoding="utf-8")
    t = t.replace(
        '(property "Footprint" "ESP32_Carrier:MP1584EN_SOT23-8"',
        '(property "Footprint" "ESP32_Carrier:MP1584EN_SOIC-8-EP"',
    )
    t = t.replace(
        """	(global_label "+24V"
		(shape input)
		(at 706.12 176.53 180)
		(effects (font (size 1.27 1.27)) (justify right))
		(uuid "a08e38be-9200-486a-81b3-15bbf7daba47")
	)""",
        """	(no_connect (at 706.12 176.53) (uuid "a08e38be-9200-486a-81b3-15bbf7daba47"))""",
    )
    t = t.replace(
        """	(global_label "+24V"
		(shape input)
		(at 706.12 186.69 180)
		(effects (font (size 1.27 1.27)) (justify right))
		(uuid "b8137243-40b5-47ac-8376-64845a71af68")
	)""",
        """	(global_label "/BUCK_FREQ"
		(shape input)
		(at 706.12 186.69 180)
		(effects (font (size 1.27 1.27)) (justify right))
		(uuid "b8137243-40b5-47ac-8376-64845a71af68")
	)""",
    )
    t = t.replace(
        """	(no_connect (at 706.12 189.23) (uuid "6e7ac84f-b271-4502-ac86-5d7867b586bc"))""",
        """	(global_label "+24V"
		(shape input)
		(at 706.12 189.23 180)
		(effects (font (size 1.27 1.27)) (justify right))
		(uuid "6e7ac84f-b271-4502-ac86-5d7867b586bc")
	)""",
    )
    pin8 = (
        '\t\t\t\t(pin passive line\n'
        '\t\t\t\t\t(at -5.08 -8.89 0)\n'
        '\t\t\t\t\t(length 2.54)\n'
        '\t\t\t\t\t(name "P8" (effects (font (size 1.27 1.27))))\n'
        '\t\t\t\t\t(number "8" (effects (font (size 1.27 1.27))))\n'
        '\t\t\t\t)\n'
        '\t\t\t)\n'
        '\t\t)\n'
        '\t(symbol "ESP32_Carrier:TMC2209_StepStick"'
    )
    pin8_new = (
        '\t\t\t\t(pin passive line\n'
        '\t\t\t\t\t(at -5.08 -8.89 0)\n'
        '\t\t\t\t\t(length 2.54)\n'
        '\t\t\t\t\t(name "P8" (effects (font (size 1.27 1.27))))\n'
        '\t\t\t\t\t(number "8" (effects (font (size 1.27 1.27))))\n'
        '\t\t\t\t)\n'
        '\t\t\t\t(pin passive line\n'
        '\t\t\t\t\t(at 5.08 0 180)\n'
        '\t\t\t\t\t(length 2.54)\n'
        '\t\t\t\t\t(name "EP" (effects (font (size 1.27 1.27))))\n'
        '\t\t\t\t\t(number "9" (effects (font (size 1.27 1.27))))\n'
        '\t\t\t\t)\n'
        '\t\t\t)\n'
        '\t\t)\n'
        '\t(symbol "ESP32_Carrier:TMC2209_StepStick"'
    )
    if pin8 not in t:
        raise SystemExit("U2 symbol pin 8 block not found")
    t = t.replace(pin8, pin8_new, 1)
    t = t.replace(
        '\t\t(pin "8" (uuid "de9f7b40-f36d-46f4-9c21-0c8c16c9741c"))\n'
        '\t\t(instances\n'
        '\t\t\t(project "esp32_baseboard"\n'
        '\t\t\t\t(path "/104f720f-6c0d-4cdd-b2ff-299bfce56fbe"\n'
        '\t\t\t\t\t(reference "U2") (unit 1)',
        '\t\t(pin "8" (uuid "de9f7b40-f36d-46f4-9c21-0c8c16c9741c"))\n'
        '\t\t(pin "9" (uuid "c3e1a7b0-4d2f-4a8e-9b11-7e6c2d8f0a41"))\n'
        '\t\t(instances\n'
        '\t\t\t(project "esp32_baseboard"\n'
        '\t\t\t\t(path "/104f720f-6c0d-4cdd-b2ff-299bfce56fbe"\n'
        '\t\t\t\t\t(reference "U2") (unit 1)',
    )
    tmc = '\t(symbol (lib_id "ESP32_Carrier:TMC2209_StepStick") (at 787.4 43.18 0) (unit 1)'
    extra = (
        '\t(global_label "GND"\n'
        '\t\t(shape input)\n'
        '\t\t(at 716.28 182.88 0)\n'
        '\t\t(effects (font (size 1.27 1.27)) (justify left))\n'
        '\t\t(uuid "e9c4b2a1-55d0-4f18-8c77-21ab90de3344")\n'
        '\t)\n'
        '\t(symbol (lib_id "ESP32_Carrier:GEN_R_0805_100k") (at 762 182.88 0) (unit 1)\n'
        '\t\t(exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)\n'
        '\t\t(uuid "aa11bb22-cc33-4d44-8e55-66778899aabb")\n'
        '\t\t(property "Reference" "R_FREQ" (at 762 176.53 0)\n'
        '\t\t\t(effects (font (size 1.27 1.27))))\n'
        '\t\t(property "Value" "100k" (at 762 189.23 0)\n'
        '\t\t\t(effects (font (size 1.27 1.27))))\n'
        '\t\t(property "Footprint" "ESP32_Carrier:R_0805_100k" (at 762 182.88 0)\n'
        '\t\t\t(effects (font (size 1.27 1.27)) (hide yes)))\n'
        '\t\t(property "Datasheet" "~" (at 762 182.88 0)\n'
        '\t\t\t(effects (font (size 1.27 1.27)) (hide yes)))\n'
        '\t\t(pin "1" (uuid "b1c2d3e4-f5a6-4789-8abc-def012345678"))\n'
        '\t\t(pin "2" (uuid "c2d3e4f5-a6b7-4890-9bcd-ef0123456789"))\n'
        '\t\t(instances\n'
        '\t\t\t(project "esp32_baseboard"\n'
        '\t\t\t\t(path "/104f720f-6c0d-4cdd-b2ff-299bfce56fbe"\n'
        '\t\t\t\t\t(reference "R_FREQ") (unit 1)\n'
        '\t\t\t\t)\n'
        '\t\t\t)\n'
        '\t\t)\n'
        '\t)\n'
        '\t(global_label "/BUCK_FREQ"\n'
        '\t\t(shape input)\n'
        '\t\t(at 756.92 181.61 180)\n'
        '\t\t(effects (font (size 1.27 1.27)) (justify right))\n'
        '\t\t(uuid "d4e5f6a7-b8c9-4d0e-91f2-334455667788")\n'
        '\t)\n'
        '\t(global_label "GND"\n'
        '\t\t(shape input)\n'
        '\t\t(at 756.92 184.15 180)\n'
        '\t\t(effects (font (size 1.27 1.27)) (justify right))\n'
        '\t\t(uuid "e5f6a7b8-c9d0-4e1f-82a3-445566778899")\n'
        '\t)\n'
        + tmc
    )
    if tmc not in t:
        raise SystemExit("TMC symbol after U2 not found")
    if '(property "Reference" "R_FREQ"' not in t:
        t = t.replace(tmc, extra, 1)

    idx = t.find('(symbol "ESP32_Carrier:GEN_R_0805_10k"')
    idx2 = t.find('(symbol "ESP32_Carrier:GEN_R_1206_22R"', idx)
    if idx2 < 0:
        raise SystemExit("cannot insert R_0805_100k lib")
    if '(symbol "ESP32_Carrier:GEN_R_0805_100k"' not in t:
        lib100 = (
            '(symbol "ESP32_Carrier:GEN_R_0805_100k"\n'
            '\t\t\t(pin_numbers (hide no))\n'
            '\t\t\t(pin_names (offset 0.508))\n'
            '\t\t\t(exclude_from_sim no) (in_bom yes) (on_board yes)\n'
            '\t\t\t(property "Reference" "R" (at 0 5.08 0) (effects (font (size 1.27 1.27))))\n'
            '\t\t\t(property "Value" "GEN_R_0805_100k" (at 0 -5.08 0) (effects (font (size 1.27 1.27))))\n'
            '\t\t\t(property "Footprint" "ESP32_Carrier:R_0805_100k" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
            '\t\t\t(symbol "GEN_R_0805_100k_0_1"\n'
            '\t\t\t\t(rectangle (start -2.54 2.54) (end 2.54 -2.54)\n'
            '\t\t\t\t\t(stroke (width 0.254) (type default)) (fill (type none)))\n'
            '\t\t\t)\n'
            '\t\t\t(symbol "GEN_R_0805_100k_1_1"\n'
            '\t\t\t\t(pin passive line\n'
            '\t\t\t\t\t(at -5.08 1.27 0)\n'
            '\t\t\t\t\t(length 2.54)\n'
            '\t\t\t\t\t(name "P1" (effects (font (size 1.27 1.27))))\n'
            '\t\t\t\t\t(number "1" (effects (font (size 1.27 1.27))))\n'
            '\t\t\t\t)\n'
            '\t\t\t\t(pin passive line\n'
            '\t\t\t\t\t(at -5.08 -1.27 0)\n'
            '\t\t\t\t\t(length 2.54)\n'
            '\t\t\t\t\t(name "P2" (effects (font (size 1.27 1.27))))\n'
            '\t\t\t\t\t(number "2" (effects (font (size 1.27 1.27))))\n'
            '\t\t\t\t)\n'
            '\t\t\t)\n'
            '\t\t)\n'
            '\t'
        )
        t = t[:idx2] + lib100 + t[idx2:]

    for ref, val in CAP_VALUES.items():
        t = re.sub(
            rf'(\(property "Reference" "{ref}"[\s\S]{{0,400}}\(property "Value" ")[^"]+',
            rf'\g<1>{val}',
            t,
            count=1,
        )
        t = re.sub(
            rf'(\(property "Reference" "{ref}"[\s\S]{{0,700}}\(property "Footprint" ")ESP32_Carrier:CP_SMD_D6\.3x5\.8',
            rf'\g<1>ESP32_Carrier:CP_SMD_D6.3x8',
            t,
            count=1,
        )
    sch.write_text(t, encoding="utf-8")
    print(f"wrote {sch}")


def apply() -> None:
    text = PCB.read_text(encoding="utf-8")
    start, old_u2 = find_fp(text, "U2")
    at = re.search(r"\(at\s+([\d.-]+)\s+([\d.-]+)(?:\s+([\d.-]+))?\)", old_u2)
    global U2_AT
    U2_AT = (float(at.group(1)), float(at.group(2)))
    print(f"  U2 @ {U2_AT}")
    text = strip_near_u2(text)
    u2 = instance_wrap(
        "MP1584EN_SOIC-8-EP", U2_AT, 0, "U2", "MP1584EN", U2_NETS,
        silk_extra=(
            f'(fp_text user "MP1584" (at 0 -3.4 0) (layer "F.SilkS") '
            f'(uuid "{uid()}") (effects (font (size 0.7 0.7) (thickness 0.1))))'
        ),
    )
    text = replace_fp(text, "U2", u2)
    for ref in CAP_REFS:
        start, old = find_fp(text, ref)
        at = re.search(r"\(at\s+([\d.-]+)\s+([\d.-]+)(?:\s+([\d.-]+))?\)", old)
        rot = float(at.group(3) or 0)
        nets: dict[str, str] = {}
        starts = [m.start() for m in re.finditer(r'\(pad "', old)]
        table = NetTable(text)
        for i, s in enumerate(starts):
            chunk = old[s : (starts[i + 1] if i + 1 < len(starts) else len(old))]
            num = re.match(r'\(pad "([^"]*)"', chunk)
            _nid, net = pad_net(chunk, table)
            if num and net:
                nets[num.group(1)] = net
        blk = instance_wrap(
            "CP_SMD_D6.3x8",
            (float(at.group(1)), float(at.group(2))),
            rot, ref, CAP_VALUES[ref], nets,
        )
        text = replace_fp(text, ref, blk)
        print(f"  {ref} → CP_SMD_D6.3x8 @ {at.group(1)} {at.group(2)}")
    if '(property "Reference" "R_FREQ"' not in text:
        rf = instance_wrap(
            "R_0805_100k", R_FREQ_AT, 0, "R_FREQ", "100k",
            {"1": "/BUCK_FREQ", "2": "GND"},
        )
        text = inject(text, "\n" + rf)
        print(f"  added R_FREQ @ {R_FREQ_AT}")
    text = add_u2_fanout(text)
    print("  fanout VIN/GND/FREQ stubs")
    text = maze_repair(text)
    PCB.write_text(text, encoding="utf-8")
    print(f"wrote {PCB}")


if __name__ == "__main__":
    apply()

