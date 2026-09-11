#!/usr/bin/env python3
"""AABB courtyard gap audit (same rule as placer/verify)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

PCB = Path(__file__).resolve().parent / "esp32_baseboard.kicad_pcb"


def _block(text: str, start: int) -> str:
    depth, i = 0, start
    while True:
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
        i += 1


def bodies(text: str):
    out = []
    for m in re.finditer(r'\n\t\(footprint "', text):
        blk = _block(text, m.start() + 1)
        if "board_only" in blk:
            continue
        rm = re.search(r'\(property "Reference" "([^"]+)"', blk)
        at = re.search(r"\(at\s+([\d.-]+)\s+([\d.-]+)(?:\s+([\d.-]+))?\)", blk)
        if not rm or not at:
            continue
        cx, cy = float(at.group(1)), float(at.group(2))
        rot = float(at.group(3) or 0)
        crt = re.search(
            r"\(fp_rect\s*\(start\s+([\d.-]+)\s+([\d.-]+)\)\s*\(end\s+([\d.-]+)\s+([\d.-]+)\)[\s\S]*?F\.CrtYd",
            blk,
        )
        if crt:
            sx0, sy0, sx1, sy1 = map(float, crt.groups())
            hw, hh = abs(sx1 - sx0) / 2, abs(sy1 - sy0) / 2
        else:
            hw, hh = 4.0, 4.0
        if abs(rot - 90) < 1 or abs(rot - 270) < 1:
            hw, hh = hh, hw
        out.append((rm.group(1), cx, cy, hw, hh))
    return out


def clashes(bodies, gap: float):
    hits = []
    for i, (ra, ax, ay, aw, ah) in enumerate(bodies):
        for rb, bx, by, bw, bh in bodies[i + 1 :]:
            need_x = aw + bw + gap
            need_y = ah + bh + gap
            if abs(ax - bx) < need_x and abs(ay - by) < need_y:
                sx = need_x - abs(ax - bx)
                sy = need_y - abs(ay - by)
                hits.append((min(sx, sy), ra, rb))
    hits.sort(reverse=True)
    return hits


def main() -> int:
    text = PCB.read_text(encoding="utf-8")
    b = bodies(text)
    print(f"parts={len(b)}")
    for gap in (0.0, 1.0, 1.5, 2.0, 2.5, 3.0):
        h = clashes(b, gap)
        print(f"gap>={gap:.1f}: {len(h)} clashes")
        for short, a, c in h[:15]:
            print(f"  shortfall {short:.2f}  {a}/{c}")
    # fail if any shortfall vs 2.0
    return 0 if not clashes(b, 2.0) else 1


if __name__ == "__main__":
    sys.exit(main())
