#!/usr/bin/env python3
"""Geometry guard for the generated baseboard.

gen_power_carrier.py places every footprint by hand-tuned coordinates, so an
edit to one placement can silently drop another part on top of it. Run this
after every regenerate:

    python gen_power_carrier.py && python check_pcb.py

Checks:
  1. no two footprints have pads closer than CLEARANCE (through-hole pads
     collide across layers, so F.Cu vs B.Cu still counts)
  2. every pad sits inside the Edge.Cuts outline with MARGIN to spare
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

PCB = Path(__file__).resolve().parent / "esp32_baseboard.kicad_pcb"
CLEARANCE = 0.2  # mm, pad edge to pad edge
MARGIN = 0.5  # mm, pad edge to board edge

FP_RE = re.compile(
    r'\(footprint "([^"]+)"\s*\n\s*\(layer "([FB])\.Cu"\)\s*\n\s*'
    r'\(uuid "[^"]+"\)\s*\n\s*\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)'
)
PAD_RE = re.compile(
    r'\(pad "([^"]+)" \w+ \w+\s*\n\s*\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)'
    r'\s*\n\s*\(size ([\d.]+) ([\d.]+)\)'
)
REF_RE = re.compile(r'\(property "Reference" "([^"]+)"')
EDGE_RE = re.compile(
    r'\(gr_rect\s*\n\s*\(start ([-\d.]+) ([-\d.]+)\)\s*\n\s*'
    r'\(end ([-\d.]+) ([-\d.]+)\).*?\(layer "Edge\.Cuts"\)',
    re.S,
)


def collect_pads(src: str) -> list[tuple[str, float, float, float, float]]:
    """(ref, x, y, w, h) in board coordinates for every pad."""
    starts = [m.start() for m in re.finditer(r'\n\t\(footprint "', src)]
    starts.append(len(src))
    pads = []
    for i in range(len(starts) - 1):
        blk = src[starts[i]:starts[i + 1]]
        fm = FP_RE.search(blk)
        if not fm:
            continue
        fx, fy = float(fm.group(3)), float(fm.group(4))
        th = math.radians(float(fm.group(5) or 0))
        rm = REF_RE.search(blk)
        ref = rm.group(1) if rm else fm.group(1)
        for pm in PAD_RE.finditer(blk):
            px, py = float(pm.group(2)), float(pm.group(3))
            w, h = float(pm.group(5)), float(pm.group(6))
            gx = fx + px * math.cos(th) - py * math.sin(th)
            gy = fy + px * math.sin(th) + py * math.cos(th)
            pads.append((ref, gx, gy, w, h))
    return pads


def main() -> int:
    src = PCB.read_text(encoding="utf-8")
    pads = collect_pads(src)
    refs = {p[0] for p in pads}
    print(f"{len(pads)} pads across {len(refs)} footprints")
    fails = 0

    clashes: dict[tuple[str, str], int] = {}
    for i in range(len(pads)):
        r1, x1, y1, w1, h1 = pads[i]
        for j in range(i + 1, len(pads)):
            r2, x2, y2, w2, h2 = pads[j]
            if r1 == r2:
                continue
            if (abs(x1 - x2) - (w1 + w2) / 2 < CLEARANCE
                    and abs(y1 - y2) - (h1 + h2) / 2 < CLEARANCE):
                key = (r1, r2) if r1 < r2 else (r2, r1)
                clashes[key] = clashes.get(key, 0) + 1
    if clashes:
        fails += 1
        print(f"\nFAIL - pad clashes (<{CLEARANCE}mm):")
        for (a, b), n in sorted(clashes.items(), key=lambda kv: -kv[1]):
            print(f"  {a:22s} <-> {b:22s}  {n} pad pairs")
    else:
        print(f"OK   - no pad clashes (>={CLEARANCE}mm)")

    em = EDGE_RE.search(src)
    if not em:
        print("FAIL - no Edge.Cuts rectangle found")
        return 1
    ex0, ey0, ex1, ey1 = (float(em.group(k)) for k in range(1, 5))
    outside = [
        (ref, round(x, 2), round(y, 2))
        for ref, x, y, w, h in pads
        if (x - w / 2 < ex0 + MARGIN or x + w / 2 > ex1 - MARGIN
            or y - h / 2 < ey0 + MARGIN or y + h / 2 > ey1 - MARGIN)
    ]
    if outside:
        fails += 1
        print(f"\nFAIL - {len(outside)} pads outside the {ex1-ex0:.0f}x{ey1-ey0:.0f}mm outline:")
        for row in outside:
            print("  ", row)
    else:
        print(f"OK   - all pads inside outline (>={MARGIN}mm margin)")

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
