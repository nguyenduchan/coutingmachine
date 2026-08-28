"""Count true interior crossings (ignore shared endpoints / T-hits)."""
from __future__ import annotations

import math
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
    """True if segments cross in their interiors (not just touch at endpoint)."""
    o1, o2 = orient(p1, p2, p3), orient(p1, p2, p4)
    o3, o4 = orient(p3, p4, p1), orient(p3, p4, p2)
    if o1 == 0 and on_seg(p1, p2, p3):
        return False  # colinear touch — handle separately
    if o2 == 0 and on_seg(p1, p2, p4):
        return False
    if o3 == 0 and on_seg(p3, p4, p1):
        return False
    if o4 == 0 and on_seg(p3, p4, p2):
        return False
    return (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0)


def seg_clearance(p1, p2, p3, p4):
    best = 1e9
    for (a, b), (c, d) in (((p1, p2), (p3, p4)), ((p3, p4), (p1, p2))):
        dx, dy = b[0] - a[0], b[1] - a[1]
        for i in range(9):
            t = i / 8
            px, py = a[0] + t * dx, a[1] + t * dy
            dx2, dy2 = d[0] - c[0], d[1] - c[1]
            ln2 = dx2 * dx2 + dy2 * dy2 or 1e-18
            u = max(0, min(1, ((px - c[0]) * dx2 + (py - c[1]) * dy2) / ln2))
            # skip if near endpoint of either seg
            if t < 0.05 or t > 0.95 or u < 0.05 or u > 0.95:
                continue
            qx, qy = c[0] + u * dx2, c[1] + u * dy2
            best = min(best, math.hypot(px - qx, py - qy))
    return best


CLEAR = 0.2
cross = []
near = []
for i, a in enumerate(segs):
    for b in segs[i + 1 :]:
        if a[3] != b[3] or a[4] == b[4]:
            continue
        if proper_intersect(a[0], a[1], b[0], b[1]):
            mid = ((a[0][0] + a[1][0]) / 2, (a[0][1] + a[1][1]) / 2)
            cross.append((a, b, mid))
            continue
        d = seg_clearance(a[0], a[1], b[0], b[1])
        need = (a[2] + b[2]) / 2 + CLEAR
        if d < need:
            near.append((d, need, a, b))

print(f"proper interior crossings (SHORT risk): {len(cross)}")
pairs = defaultdict(int)
for a, b, mid in cross:
    pairs[tuple(sorted((a[4], b[4])))] += 1
for (n1, n2), c in sorted(pairs.items(), key=lambda x: -x[1])[:20]:
    print(f"  {net_names.get(n1)} vs {net_names.get(n2)}: {c}")
print("sample shorts:")
for a, b, mid in cross[:15]:
    print(
        f"  {net_names.get(a[4])} x {net_names.get(b[4])} @({mid[0]:.1f},{mid[1]:.1f}) {a[3]}"
    )

print(f"\ninterior clearance (not endpoint) violations: {len(near)}")
pairs2 = defaultdict(int)
for d, need, a, b in near:
    pairs2[tuple(sorted((a[4], b[4])))] += 1
for (n1, n2), c in sorted(pairs2.items(), key=lambda x: -x[1])[:15]:
    print(f"  {net_names.get(n1)} vs {net_names.get(n2)}: {c}")
