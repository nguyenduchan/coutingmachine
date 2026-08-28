"""Flood-fill copper connectivity per net; report pads not joined by tracks/vias."""
from __future__ import annotations

import math
import re
from collections import defaultdict, deque
from pathlib import Path

from maze_router import parse_pads

text = Path(__file__).with_name("esp32_baseboard.kicad_pcb").read_text(encoding="utf-8")
pads = parse_pads(text)
segs = []
for m in re.finditer(
    r'\(segment\s+'
    r'\(start\s+([\d.-]+)\s+([\d.-]+)\)\s+'
    r'\(end\s+([\d.-]+)\s+([\d.-]+)\)\s+'
    r'\(width\s+([\d.-]+)\)\s+'
    r'\(layer\s+"([^"]+)"\)\s+'
    r'\(net\s+(\d+)\)',
    text,
    re.S,
):
    x1, y1, x2, y2, w, layer, net = m.groups()
    segs.append((float(x1), float(y1), float(x2), float(y2), float(w), layer, int(net)))
print(f"parsed segments: {len(segs)}")
vias = []
for m in re.finditer(
    r"\(via\s+[\s\S]*?\(at\s+([\d.-]+)\s+([\d.-]+)\)[\s\S]*?"
    r"\(size\s+([\d.-]+)\)[\s\S]*?\(net\s+(\d+)\)",
    text,
):
    vias.append((float(m.group(1)), float(m.group(2)), float(m.group(3)), int(m.group(4))))
print(f"parsed vias: {len(vias)}")

TOL = 0.85  # pad/track endpoint snap (grid 0.55)


def near(ax, ay, bx, by, t=TOL):
    return abs(ax - bx) <= t and abs(ay - by) <= t


by_net_pads = defaultdict(list)
for i, p in enumerate(pads):
    by_net_pads[p.net].append(i)

open_nets = []
for net, idxs in sorted(by_net_pads.items()):
    if len(idxs) < 2:
        continue
    # graph nodes = pads + via points + segment endpoints of this net
    nodes = []  # (x,y)
    for i in idxs:
        nodes.append((pads[i].x, pads[i].y))
    n_pad = len(nodes)
    for x, y, _sz, n in vias:
        if n == net:
            nodes.append((x, y))
    for x1, y1, x2, y2, _w, _ly, n in segs:
        if n != net:
            continue
        nodes.append((x1, y1))
        nodes.append((x2, y2))

    # union-find by proximity + segment links
    parent = list(range(len(nodes)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            if near(*nodes[i], *nodes[j]):
                union(i, j)
    # also union along each segment's two ends
    for x1, y1, x2, y2, _w, _ly, n in segs:
        if n != net:
            continue
        ia = ib = None
        for i, (x, y) in enumerate(nodes):
            if near(x, y, x1, y1):
                ia = i
            if near(x, y, x2, y2):
                ib = i
        if ia is not None and ib is not None:
            union(ia, ib)

    roots = {find(i) for i in range(n_pad)}
    if len(roots) > 1:
        name = pads[idxs[0]].name
        # classify module pads disconnected
        open_nets.append((net, name, len(idxs), len(roots)))

print(f"nets with >=2 pads: {sum(1 for v in by_net_pads.values() if len(v)>=2)}")
print(f"OPEN (pads not one copper island): {len(open_nets)}")
for net, name, np, nr in open_nets[:40]:
    print(f"  net {net:3d} {name:16s} pads={np} islands={nr}")

# Optional face stats (refs may lack is_module)
mod_xy = [(p.x, p.y) for p in pads if getattr(p, "ref", "").startswith(("U", "T"))]
jack_xy = [(p.x, p.y) for p in pads if getattr(p, "ref", "").startswith("J")]
bad_f = 0
for x1, y1, x2, y2, w, layer, net in segs:
    if layer != "F.Cu" or not mod_xy:
        continue

    def closest(px, py, pts):
        return min(math.hypot(px - a, py - b) for a, b in pts) if pts else 1e9

    mx, my = 0.5 * (x1 + x2), 0.5 * (y1 + y2)
    if jack_xy and closest(mx, my, jack_xy) > 8.0 and closest(mx, my, mod_xy) < 25.0:
        bad_f += 1
print(f"F.Cu segments near modules (info): {bad_f}")
if open_nets:
    raise SystemExit(1)
raise SystemExit(0)
