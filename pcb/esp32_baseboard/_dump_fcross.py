"""Dump F.Cu crossing segment pairs for debugging."""
from __future__ import annotations

import re
from pathlib import Path

text = Path(__file__).with_name("esp32_baseboard.kicad_pcb").read_text(encoding="utf-8")
net_names = {int(a): b for a, b in re.findall(r'\(net\s+(\d+)\s+"([^"]*)"\)', text)}
segs = []
for m in re.finditer(
    r'\(segment\s+\(start\s+([\d.-]+)\s+([\d.-]+)\)\s+\(end\s+([\d.-]+)\s+([\d.-]+)\)'
    r'\s+\(width\s+([\d.-]+)\)\s+\(layer\s+"([^"]+)"\)\s+\(net\s+(\d+)\)',
    text,
):
    x1, y1, x2, y2, w, layer, net = m.groups()
    if layer != "F.Cu":
        continue
    segs.append(((float(x1), float(y1)), (float(x2), float(y2)), float(w), int(net)))


def orient(a, b, c):
    return (b[1] - a[1]) * (c[0] - b[0]) - (b[0] - a[0]) * (c[1] - b[1])


def on_seg(a, b, c, eps=1e-6):
    return (
        min(a[0], b[0]) - eps <= c[0] <= max(a[0], b[0]) + eps
        and min(a[1], b[1]) - eps <= c[1] <= max(a[1], b[1]) + eps
    )


def proper_intersect(p1, p2, p3, p4):
    o1, o2 = orient(p1, p2, p3), orient(p1, p2, p4)
    o3, o4 = orient(p3, p4, p1), orient(p3, p4, p2)
    if o1 == 0 and on_seg(p1, p2, p3):
        return False
    if o2 == 0 and on_seg(p1, p2, p4):
        return False
    if o3 == 0 and on_seg(p3, p4, p1):
        return False
    if o4 == 0 and on_seg(p3, p4, p2):
        return False
    return (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0)


want = {("/MotA2", "/TFT_SCK"), ("+5V_BLW", "/OPTO_IN1"), ("+3V3", "/BLOWER"), ("/OPTO_IN1", "GND")}
shown = 0
for i, a in enumerate(segs):
    for b in segs[i + 1 :]:
        if a[3] == b[3]:
            continue
        na, nb = net_names[a[3]], net_names[b[3]]
        key = tuple(sorted((na, nb)))
        if key not in {tuple(sorted(x)) for x in want} and shown > 20:
            continue
        if not proper_intersect(a[0], a[1], b[0], b[1]):
            continue
        if key in {tuple(sorted(x)) for x in want} or shown < 8:
            print(f"{na} {a[0]}->{a[1]}  x  {nb} {b[0]}->{b[1]}")
            shown += 1
