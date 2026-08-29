"""Flood-fill copper connectivity per net; report pads not joined by tracks/vias."""
from __future__ import annotations

import math
import re
from collections import defaultdict, deque
from pathlib import Path

from maze_router import parse_pads, parse_segments, parse_kept_vias

text = Path(__file__).with_name("esp32_baseboard.kicad_pcb").read_text(encoding="utf-8")
pads = parse_pads(text)
segs = [(g.x1, g.y1, g.x2, g.y2, g.width, g.layer, g.net) for g in parse_segments(text)]
print(f"parsed segments: {len(segs)}")
vias = [(vx, vy, vsz, vnet) for vx, vy, vnet, vsz in parse_kept_vias(text)]
print(f"parsed vias: {len(vias)}")

# Copper only counts as joined where it physically touches. A 0.85 mm snap was
# wider than the routing grid itself, so it declared connected any two track
# ends that merely landed in neighbouring cells -- reporting 0 open nets on a
# board KiCad flagged with 29 unconnected items and 44 dangling track ends.
TOL = 0.05


def near(ax, ay, bx, by, t=TOL):
    return abs(ax - bx) <= t and abs(ay - by) <= t


def point_on_seg(px, py, x1, y1, x2, y2, half_w):
    """Does a point sit on a track's copper (T-junction, not just an end)?"""
    dx, dy = x2 - x1, y2 - y1
    ln2 = dx * dx + dy * dy
    if ln2 < 1e-12:
        return near(px, py, x1, y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / ln2))
    qx, qy = x1 + t * dx, y1 + t * dy
    return math.hypot(px - qx, py - qy) <= half_w + TOL


by_net_pads = defaultdict(list)
for i, p in enumerate(pads):
    by_net_pads[p.net].append(i)

open_nets = []
for net, idxs in sorted(by_net_pads.items()):
    if len(idxs) < 2:
        continue
    # Nodes are (x, y, layer). Layer matters: two track ends at the same XY on
    # opposite faces are NOT joined unless a thru-hole pad or a via bridges
    # them. Ignoring the layer is what let a board with 29 unconnected items
    # and 44 dangling ends read as fully routed here.
    net_segs = [sg for sg in segs if sg[6] == net]
    net_vias = [(x, y) for x, y, _sz, n in vias if n == net]
    pad_xy = [(pads[i].x, pads[i].y, pads[i].radius) for i in idxs]

    nodes: list[tuple[float, float, str]] = []
    pad_nodes: list[list[int]] = []
    for px, py, _r in pad_xy:  # a thru-hole pad exists on both faces
        pad_nodes.append([len(nodes), len(nodes) + 1])
        nodes.append((px, py, "F.Cu"))
        nodes.append((px, py, "B.Cu"))
    n_pad_nodes = len(nodes)
    seg_ends: list[tuple[int, int]] = []
    for x1, y1, x2, y2, _w, ly, _n in net_segs:
        seg_ends.append((len(nodes), len(nodes) + 1))
        nodes.append((x1, y1, ly))
        nodes.append((x2, y2, ly))
    via_nodes: list[list[int]] = []
    for vx, vy in net_vias:
        via_nodes.append([len(nodes), len(nodes) + 1])
        nodes.append((vx, vy, "F.Cu"))
        nodes.append((vx, vy, "B.Cu"))

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

    for a, b in seg_ends:      # copper along each track
        union(a, b)
    for pair in pad_nodes:     # the barrel of a thru-hole pad
        union(*pair)
    for pair in via_nodes:     # the barrel of a via
        union(*pair)

    # Coincident copper on the SAME face.
    for i in range(len(nodes)):
        xi, yi, li = nodes[i]
        for j in range(i + 1, len(nodes)):
            xj, yj, lj = nodes[j]
            if li == lj and near(xi, yi, xj, yj):
                union(i, j)

    # A track end landing part-way along another same-net track on the same
    # face is a real T-junction.
    for i, (px, py, li) in enumerate(nodes):
        for (a, b), (x1, y1, x2, y2, w, ly, _n) in zip(seg_ends, net_segs):
            if ly == li and point_on_seg(px, py, x1, y1, x2, y2, w * 0.5):
                union(i, a)

    # A pad's or via's copper joins any track end inside its annulus.
    for pair, (px, py, rad) in zip(pad_nodes, pad_xy):
        for j, (qx, qy, lj) in enumerate(nodes):
            if math.hypot(px - qx, py - qy) <= rad + TOL:
                union(pair[0] if lj == "F.Cu" else pair[1], j)
    for pair, (vx, vy) in zip(via_nodes, net_vias):
        for j, (qx, qy, lj) in enumerate(nodes):
            if math.hypot(vx - qx, vy - qy) <= 0.4 + TOL:
                union(pair[0] if lj == "F.Cu" else pair[1], j)

    roots = {find(pair[0]) for pair in pad_nodes}
    if len(roots) > 1:
        name = pads[idxs[0]].name
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
