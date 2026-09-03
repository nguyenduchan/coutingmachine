#!/usr/bin/env python3
"""Patch already-baked ULN2003_Module footprint blocks (U5/U6/U7) on the
compiled boards: swap the bare 1.7/1.0 pin-header pads for a keyed 1.6/0.9
socket (chamfer notch + KEY text), matching the updated gen_power_carrier.py
_emit_uln_module(). Pad local (x,y) stay identical (PITCH, unchanged) so
already-routed copper still lands on pad centers -- only pad size/drill and
added graphics change, so this is safe without a full re-route.
"""
from __future__ import annotations
import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PITCH = 2.54

TARGETS = [
    ROOT / "esp32_baseboard.kicad_pcb",
    ROOT / "out_freerouting" / "routed.kicad_pcb",
    ROOT / "out_freerouting" / "unrouted.kicad_pcb",
    ROOT / "out_freerouting" / "routed.best.kicad_pcb",
]


def uid() -> str:
    return str(uuid.uuid4())


def find_blocks(text: str) -> list[tuple[int, int]]:
    spans = []
    for m in re.finditer(r'\(footprint "ESP32_Carrier:ULN2003_Module"', text):
        s = m.start()
        depth = 0
        i = s
        while True:
            if text[i] == "(":
                depth += 1
            elif text[i] == ")":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        spans.append((s, i + 1))
    return spans


def build_block(ref: str, val: str, atx: str, aty: str, hrot: str, nets: dict) -> str:
    span = 5 * PITCH
    L = []
    a = L.append
    a(f'\t(footprint "ESP32_Carrier:ULN2003_Module"')
    a('\t\t(layer "F.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {atx} {aty} {hrot})")
    a(f'\t\t(property "Reference" "{ref}"')
    a(f"\t\t\t(at 0 -3.8 {hrot})")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.9 0.9) (thickness 0.12)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a(f'\t\t(property "Value" "{val}"')
    a(f"\t\t\t(at 0 {span + 3.8} {hrot})")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.1)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")
    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
        a("\t\t(fp_rect")
        a("\t\t\t(start -3.2 -2.0)")
        a(f"\t\t\t(end 3.2 {span + 2.0})")
        a(f"\t\t\t(stroke (width {w}) (type solid))")
        a("\t\t\t(fill none)")
        a(f'\t\t\t(layer "{layer}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
    a("\t\t(fp_line")
    a("\t\t\t(start -3.2 -0.6)")
    a("\t\t\t(end -4.2 0)")
    a('\t\t\t(stroke (width 0.15) (type solid))')
    a('\t\t\t(layer "F.SilkS")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(fp_line")
    a("\t\t\t(start -4.2 0)")
    a("\t\t\t(end -3.2 0.6)")
    a('\t\t\t(stroke (width 0.15) (type solid))')
    a('\t\t\t(layer "F.SilkS")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(fp_text user "KEY"')
    a(f"\t\t\t(at -5.2 0 {hrot})")
    a('\t\t\t(layer "F.SilkS")')
    a('\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1)))')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(fp_text user "day XH toi ULN2003 (module rieng, khong gan carrier)"')
    a(f"\t\t\t(at 0 {span + 5.4} {hrot})")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.6 0.6) (thickness 0.1)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    labs = ["IN1", "IN2", "IN3", "IN4", "GND", "+12V"]
    for pi, lab in enumerate(labs):
        y = pi * PITCH
        net = nets.get(pi + 1)
        a(f'\t\t(fp_text user "{lab}"')
        a(f"\t\t\t(at 4.2 {y} {hrot})")
        a('\t\t\t(layer "F.SilkS")')
        a("\t\t\t(effects (font (size 0.65 0.65) (thickness 0.1)) (justify left))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        shape = "rect" if pi == 0 else "circle"
        a(f'\t\t(pad "{pi + 1}" thru_hole {shape}')
        a(f"\t\t\t(at 0 {y})")
        a("\t\t\t(size 1.6 1.6)")
        a("\t\t\t(drill 0.9)")
        a('\t\t\t(layers "*.Cu" "*.Mask")')
        a('\t\t\t(remove_unused_layers no)')
        if net:
            a(f'\t\t\t(net "{net}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
    a("\t)")
    return "\n".join(a for a in L) + "\n"


for path in TARGETS:
    text = path.read_text(encoding="utf-8")
    spans = find_blocks(text)
    if not spans:
        print(f"SKIP {path.name}: no ULN2003_Module blocks")
        continue
    out = []
    last = 0
    n_patched = 0
    for s, e in spans:
        block = text[s:e]
        ref = re.search(r'\(property "Reference" "(U\d+)"', block).group(1)
        val = re.search(r'\(property "Value" "([^"]+)"', block).group(1)
        at_m = re.search(r"\(at ([\-0-9.]+) ([\-0-9.]+)(?: ([\-0-9.]+))?\)", block)
        atx, aty, hrot = at_m.group(1), at_m.group(2), at_m.group(3) or "0"
        nets = {}
        for pm in re.finditer(
            r'\(pad "(\d+)" thru_hole \w+\s*\(at [^)]*\)\s*\(size [^)]*\)\s*\(drill [^)]*\)\s*'
            r'\(layers[^)]*\)(?:\s*\(remove_unused_layers[^)]*\))?\s*(?:\(net "([^"]*)"\))?',
            block,
        ):
            pin = int(pm.group(1))
            if pm.group(2):
                nets[pin] = pm.group(2)
        assert len(nets) == 6, f"{ref}: expected 6 netted pads, got {nets}"
        new_block = build_block(ref, val, atx, aty, hrot, nets).rstrip("\n")
        out.append(text[last:s])
        out.append(new_block)
        last = e
        n_patched += 1
        print(f"  {path.name}: patched {ref} at ({atx},{aty},{hrot}) nets={nets}")
    out.append(text[last:])
    new_text = "".join(out)
    assert new_text.count("(") == new_text.count(")"), f"{path}: paren mismatch after patch"
    path.write_text(new_text, encoding="utf-8")
    print(f"OK {path.name}: {n_patched} block(s) patched")
