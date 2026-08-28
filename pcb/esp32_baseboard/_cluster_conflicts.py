"""Summarize unique crossing geometry (not pair counts)."""
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


def seg_dist(p1, p2, p3, p4):
    best = 1e9
    for (a, b), (c, d) in (((p1, p2), (p3, p4)), ((p3, p4), (p1, p2))):
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln2 = dx * dx + dy * dy or 1e-18
        for i in range(9):
            t = i / 8
            px, py = a[0] + t * dx, a[1] + t * dy
            u = max(0, min(1, ((px - c[0]) * (d[0] - c[0]) + (py - c[1]) * (d[1] - c[1])) / ln2))
            qx, qy = c[0] + u * (d[0] - c[0]), c[1] + u * (d[1] - c[1])
            # wrong: ln2 is for first seg; fix properly
            dx2, dy2 = d[0] - c[0], d[1] - c[1]
            ln2b = dx2 * dx2 + dy2 * dy2 or 1e-18
            u = max(0, min(1, ((px - c[0]) * dx2 + (py - c[1]) * dy2) / ln2b))
            qx, qy = c[0] + u * dx2, c[1] + u * dy2
            best = min(best, math.hypot(px - qx, py - qy))
    return best


CLEAR = 0.2
cells = defaultdict(int)
for i, a in enumerate(segs):
    for b in segs[i + 1 :]:
        if a[3] != b[3] or a[4] == b[4]:
            continue
        d = seg_dist(a[0], a[1], b[0], b[1])
        need = (a[2] + b[2]) / 2 + CLEAR
        if d < need - 1e-6:
            mx = round(((a[0][0] + a[1][0]) / 2) / 5) * 5
            my = round(((a[0][1] + a[1][1]) / 2) / 5) * 5
            cells[(a[3], mx, my, a[4], b[4])] += 1

# Cluster by location
print(f"conflict location clusters: {len(cells)}")
for (layer, mx, my, n1, n2), c in sorted(cells.items(), key=lambda x: -x[1])[:40]:
    print(
        f"  {layer} @~({mx},{my}) {net_names.get(n1,'?')}/{net_names.get(n2,'?')} x{c}"
    )
