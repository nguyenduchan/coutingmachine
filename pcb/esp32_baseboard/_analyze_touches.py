#!/usr/bin/env python3
"""Classify cross-net segment contacts."""
from __future__ import annotations

import math
import re
from collections import defaultdict
from pathlib import Path

text = Path("esp32_baseboard.kicad_pcb").read_text(encoding="utf-8")
segs = []
for m in re.finditer(
    r'\(segment\s+\(start\s+([\d.-]+)\s+([\d.-]+)\)\s+\(end\s+([\d.-]+)\s+([\d.-]+)\)'
    r'\s+\(width\s+([\d.-]+)\)\s+\(layer\s+"([^"]+)"\)\s+\(net\s+(\d+)\)',
    text,
):
    segs.append(
        {
            "p1": (float(m.group(1)), float(m.group(2))),
            "p2": (float(m.group(3)), float(m.group(4))),
            "w": float(m.group(5)),
            "layer": m.group(6),
            "net": int(m.group(7)),
        }
    )


def seg_dist(p1, p2, p3, p4):
    best = 1e9
    for i in range(11):
        t = i / 10
        ax, ay = p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1])
        for j in range(11):
            u = j / 10
            bx, by = p3[0] + u * (p4[0] - p3[0]), p3[1] + u * (p4[1] - p3[1])
            best = min(best, math.hypot(ax - bx, ay - by))
    return best


def copper_overlap(d, w1, w2) -> bool:
    return d < (w1 + w2) * 0.5 - 0.02


touch = copper_touch = 0
by_layer = defaultdict(int)
for i, a in enumerate(segs):
    for b in segs[i + 1 :]:
        if a["layer"] != b["layer"] or a["net"] == b["net"]:
            continue
        d = seg_dist(a["p1"], a["p2"], b["p1"], b["p2"])
        if d < 0.01:
            touch += 1
            by_layer[a["layer"]] += 1
        if copper_overlap(d, a["w"], b["w"]):
            copper_touch += 1

print(f"centerline touch d<0.01: {touch}")
print(f"copper overlap (d < half-widths): {copper_touch}")
print("touch by layer:", dict(by_layer))
