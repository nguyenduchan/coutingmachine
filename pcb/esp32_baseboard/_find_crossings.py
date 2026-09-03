#!/usr/bin/env python3
"""Find same-layer interior track crossings (any net)."""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def orient(a, b, c):
    return (b[1] - a[1]) * (c[0] - b[0]) - (b[0] - a[0]) * (c[1] - b[1])


def on_seg(a, b, c, eps=1e-4):
    return (
        min(a[0], b[0]) - eps <= c[0] <= max(a[0], b[0]) + eps
        and min(a[1], b[1]) - eps <= c[1] <= max(a[1], b[1]) + eps
    )


def proper_cross(p1, p2, p3, p4):
    o1, o2 = orient(p1, p2, p3), orient(p1, p2, p4)
    o3, o4 = orient(p3, p4, p1), orient(p3, p4, p2)
    if abs(o1) < 1e-9 and on_seg(p1, p2, p3):
        return False
    if abs(o2) < 1e-9 and on_seg(p1, p2, p4):
        return False
    if abs(o3) < 1e-9 and on_seg(p3, p4, p1):
        return False
    if abs(o4) < 1e-9 and on_seg(p3, p4, p2):
        return False
    return (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0)


def intersect_pt(p1, p2, p3, p4):
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    d = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(d) < 1e-12:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / d
    u = ((x1 - x3) * (y1 - y2) - (y1 - y3) * (x1 - x2)) / d
    if 0.02 < t < 0.98 and 0.02 < u < 0.98:
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
    return None


def scan(path: Path):
    text = path.read_text(encoding="utf-8")
    nets = {int(a): b for a, b in re.findall(r'\(net\s+(\d+)\s+"([^"]*)"\)', text)}
    segs = []
    # KiCad 9+ FreeRouting: (net "NAME") ; modules: (net N)
    for m in re.finditer(
        r'\(segment\s+\(start\s+([\d.-]+)\s+([\d.-]+)\)\s+\(end\s+([\d.-]+)\s+([\d.-]+)\)'
        r'\s+\(width\s+([\d.-]+)\)\s+\(layer\s+"([^"]+)"\)\s+\(net\s+(?:(\d+)|"([^"]+)")\)',
        text,
    ):
        nid = m.group(7)
        nname = m.group(8)
        if nid is not None:
            net_key: int | str = int(nid)
            label = nets.get(net_key, str(net_key))
        else:
            net_key = nname or "?"
            label = net_key
        segs.append(
            (
                (float(m.group(1)), float(m.group(2))),
                (float(m.group(3)), float(m.group(4))),
                float(m.group(5)),
                m.group(6),
                net_key,
                label,
            )
        )
    by_layer: dict[str, list] = defaultdict(list)
    for s in segs:
        by_layer[s[3]].append(s)
    hits = []
    for layer, ls in by_layer.items():
        for i in range(len(ls)):
            for j in range(i + 1, len(ls)):
                a, b = ls[i], ls[j]
                if a[4] == b[4]:
                    continue
                if proper_cross(a[0], a[1], b[0], b[1]):
                    pt = intersect_pt(a[0], a[1], b[0], b[1])
                    hits.append((layer, a[5], b[5], pt, a, b))
    print(f"{path.name}: segs={len(segs)} same-layer crossings={len(hits)}")
    for layer, n1, n2, pt, a, b in hits[:40]:
        print(f"  {layer}: {n1} x {n2} @ {pt}")
        print(f"    {a[0]}->{a[1]}  |  {b[0]}->{b[1]}")
    return hits


def main():
    paths = [
        ROOT / "esp32_baseboard.kicad_pcb",
        ROOT / "modules" / "m1_power_prot.kicad_pcb",
        ROOT / "modules" / "m2_opto4.kicad_pcb",
    ]
    total = 0
    for p in paths:
        if p.exists():
            total += len(scan(p))
    print(f"\nTOTAL crossings: {total}")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
