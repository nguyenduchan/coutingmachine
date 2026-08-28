"""Dump B.Cu crossing samples with segment geometry."""
from __future__ import annotations

import re
from collections import defaultdict
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
    segs.append(((float(x1), float(y1)), (float(x2), float(y2)), float(w), layer, int(net)))


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


# Classify segments: H vs V vs diagonal
hv = defaultdict(lambda: {"H": 0, "V": 0, "D": 0})
for a, b, w, layer, net in segs:
    dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
    kind = "H" if dy < 1e-4 else ("V" if dx < 1e-4 else "D")
    hv[layer][kind] += 1
print("segment orientation:", dict(hv))

# Count crossings where at least one segment is "wrong" orientation for Manhattan
# Ideal: F=H only, B=V only
bad = 0
for i, a in enumerate(segs):
    for b in segs[i + 1 :]:
        if a[3] != b[3] or a[4] == b[4]:
            continue
        if proper_intersect(a[0], a[1], b[0], b[1]):
            bad += 1
print("total crossings", bad)

# How many B.Cu segs are horizontal (illegal under V-only-B)?
bh = sum(1 for a, b, w, layer, net in segs if layer == "B.Cu" and abs(a[1] - b[1]) < 1e-4 and abs(a[0] - b[0]) > 1e-4)
fv = sum(1 for a, b, w, layer, net in segs if layer == "F.Cu" and abs(a[0] - b[0]) < 1e-4 and abs(a[1] - b[1]) > 1e-4)
print(f"B.Cu horizontals: {bh}")
print(f"F.Cu verticals: {fv}")
