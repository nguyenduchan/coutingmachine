"""Count proper interior crossings per copper layer."""
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


by_layer = defaultdict(int)
by_pair = defaultdict(lambda: defaultdict(int))
samples = defaultdict(list)
for i, a in enumerate(segs):
    for b in segs[i + 1 :]:
        if a[3] != b[3] or a[4] == b[4]:
            continue
        if proper_intersect(a[0], a[1], b[0], b[1]):
            by_layer[a[3]] += 1
            na, nb = net_names.get(a[4], str(a[4])), net_names.get(b[4], str(b[4]))
            key = tuple(sorted((na, nb)))
            by_pair[a[3]][key] += 1
            if len(samples[a[3]]) < 12:
                mid = ((a[0][0] + a[1][0]) / 2, (a[0][1] + a[1][1]) / 2)
                samples[a[3]].append((na, nb, mid))

print("crossings by layer:", dict(by_layer))
for layer in ("F.Cu", "B.Cu"):
    print(f"\n=== {layer} top pairs ===")
    for (na, nb), c in sorted(by_pair[layer].items(), key=lambda x: -x[1])[:15]:
        print(f"  {c:4d}  {na} vs {nb}")
    print("samples:")
    for na, nb, mid in samples[layer]:
        print(f"  {na} x {nb} @{mid[0]:.1f},{mid[1]:.1f}")
