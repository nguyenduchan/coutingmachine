"""Report worst same-layer clearance gaps with geometry (false-endpoint filter)."""
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
        for i in range(21):
            t = i / 20
            px, py = a[0] + t * dx, a[1] + t * dy
            dx2, dy2 = d[0] - c[0], d[1] - c[1]
            ln22 = dx2 * dx2 + dy2 * dy2 or 1e-18
            u = max(0, min(1, ((px - c[0]) * dx2 + (py - c[1]) * dy2) / ln22))
            # skip near either endpoint (T-junction / via fanout)
            if t < 0.08 or t > 0.92 or u < 0.08 or u > 0.92:
                continue
            qx, qy = c[0] + u * dx2, c[1] + u * dy2
            best = min(best, math.hypot(px - qx, py - qy))
    return best


CLEAR = 0.2  # copper-to-copper clearance target (mm)
hits = []
for i, a in enumerate(segs):
    for b in segs[i + 1 :]:
        if a[3] != b[3] or a[4] == b[4]:
            continue
        d = seg_dist(a[0], a[1], b[0], b[1])
        need = (a[2] + b[2]) / 2 + CLEAR
        gap = d - (a[2] + b[2]) / 2  # edge-to-edge
        if d < need:
            hits.append((gap, d, need, a, b))

hits.sort()
print(f"clearance hits (edge gap < {CLEAR}mm after width): {len(hits)}")
by = defaultdict(int)
by_layer = defaultdict(int)
for gap, d, need, a, b in hits:
    na, nb = net_names[a[4]], net_names[b[4]]
    by[tuple(sorted((na, nb)))] += 1
    by_layer[a[3]] += 1
print("by layer:", dict(by_layer))
print("top pairs:")
for k, c in sorted(by.items(), key=lambda x: -x[1])[:20]:
    print(f"  {c:4d}  {k[0]} vs {k[1]}")
print("\nworst 25 (edge_gap_mm):")
for gap, d, need, a, b in hits[:25]:
    na, nb = net_names[a[4]], net_names[b[4]]
    print(
        f"  gap={gap:.3f}  {na} w={a[2]} {a[0]}->{a[1]}  |  {nb} w={b[2]} {b[0]}->{b[1]}  {a[3]}"
    )

# Parallel same-orientation clusters: list unique Y (F H) and X (B V) with multi-nets too close
print("\n=== F.Cu parallel H lanes too close (center pitch) ===")
fh = [s for s in segs if s[3] == "F.Cu"]
# group by rounded Y
ys = defaultdict(list)
for s in fh:
    y = round((s[0][1] + s[1][1]) / 2, 2)
    ys[y].append(s)
ysorted = sorted(ys.keys())
for i, y1 in enumerate(ysorted):
    for y2 in ysorted[i + 1 :]:
        dy = abs(y2 - y1)
        if dy > 3.0:
            break
        # any pair different nets overlapping in X?
        for a in ys[y1]:
            for b in ys[y2]:
                if a[4] == b[4]:
                    continue
                xa0, xa1 = min(a[0][0], a[1][0]), max(a[0][0], a[1][0])
                xb0, xb1 = min(b[0][0], b[1][0]), max(b[0][0], b[1][0])
                if xa1 < xb0 - 0.5 or xb1 < xa0 - 0.5:
                    continue
                edge = dy - (a[2] + b[2]) / 2
                if edge < CLEAR:
                    print(
                        f"  dy={dy:.2f} edge={edge:.2f} y={y1}/{y2} "
                        f"{net_names[a[4]]} w{a[2]} vs {net_names[b[4]]} w{b[2]}"
                    )

print("\n=== B.Cu parallel V lanes too close ===")
bv = [s for s in segs if s[3] == "B.Cu"]
xs = defaultdict(list)
for s in bv:
    x = round((s[0][0] + s[1][0]) / 2, 2)
    xs[x].append(s)
xsorted = sorted(xs.keys())
shown = 0
for i, x1 in enumerate(xsorted):
    for x2 in xsorted[i + 1 :]:
        dx = abs(x2 - x1)
        if dx > 3.0:
            break
        for a in xs[x1]:
            for b in xs[x2]:
                if a[4] == b[4]:
                    continue
                ya0, ya1 = min(a[0][1], a[1][1]), max(a[0][1], a[1][1])
                yb0, yb1 = min(b[0][1], b[1][1]), max(b[0][1], b[1][1])
                if ya1 < yb0 - 0.5 or yb1 < ya0 - 0.5:
                    continue
                edge = dx - (a[2] + b[2]) / 2
                if edge < CLEAR:
                    print(
                        f"  dx={dx:.2f} edge={edge:.2f} x={x1}/{x2} "
                        f"{net_names[a[4]]} w{a[2]} vs {net_names[b[4]]} w{b[2]}"
                    )
                    shown += 1
                    if shown > 40:
                        break
            if shown > 40:
                break
        if shown > 40:
            break
    if shown > 40:
        break
print(f"(showed {min(shown,40)} B lane pairs)")
