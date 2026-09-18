#!/usr/bin/env python3
"""Snap footprints to 0.5 mm and straighten N/S jack rows. H1–H4 stay put."""
from __future__ import annotations

import re
from pathlib import Path

PCB = Path(__file__).resolve().parent / "esp32_baseboard.kicad_pcb"
GRID = 0.5
SKIP = {"H1", "H2", "H3", "H4"}
NORTH = {
    "J_P24N", "J14", "J15", "J_IN2", "J_IN3", "J_P5N", "J_CNT5",
    "J_KEY", "J_DISP",
}
NORTH_Y = 54.0
USB_Y = 55.0
SOUTH_MOT = {"J_MOT1", "J_MOT2"}
SOUTH_MOT_Y = 166.0
SOUTH_PWR = {"U_PWR1", "U_PWR2", "U_VIB", "J_P24S"}
SOUTH_PWR_Y = 167.0
# Visible 5×20 holder, east of D3, west of motors, silk on.
F1_XY = (93.0, 151.0)


def _block(text: str, start: int) -> str:
    d, i = 0, start
    while i < len(text):
        if text[i] == "(":
            d += 1
        elif text[i] == ")":
            d -= 1
            if d == 0:
                return text[start : i + 1]
        i += 1
    raise ValueError("unbalanced")


def snap(v: float) -> float:
    return round(v / GRID) * GRID


def main() -> None:
    text = PCB.read_text(encoding="utf-8")
    n = 0
    chunks: list[tuple[int, int, str]] = []
    for m in re.finditer(r'\n\t\(footprint "', text):
        start = m.start() + 1
        blk = _block(text, start)
        rm = re.search(r'\(property "Reference" "([^"]+)"', blk)
        if not rm:
            continue
        ref = rm.group(1)
        if ref in SKIP:
            continue
        at = re.search(r"\(at\s+([\d.-]+)\s+([\d.-]+)((?:\s+[\d.-]+)?)\)", blk)
        if not at:
            continue
        x, y = float(at.group(1)), float(at.group(2))
        rest = at.group(3) or ""
        if ref == "F1":
            nx, ny = F1_XY
        elif ref == "J_USB":
            nx, ny = snap(x), USB_Y
        elif ref in NORTH:
            nx, ny = snap(x), NORTH_Y
        elif ref in SOUTH_MOT:
            nx, ny = snap(x), SOUTH_MOT_Y
        elif ref in SOUTH_PWR:
            nx, ny = snap(x), SOUTH_PWR_Y
        else:
            nx, ny = snap(x), snap(y)
        if abs(nx - x) < 1e-9 and abs(ny - y) < 1e-9:
            continue
        new_at = f"(at {nx:g} {ny:g}{rest})"
        nblk = blk[: at.start()] + new_at + blk[at.end() :]
        chunks.append((start, start + len(blk), nblk))
        n += 1
        print(f"  {ref:12s} {x:8.3f},{y:8.3f} → {nx:g},{ny:g}")
    for start, end, nblk in reversed(chunks):
        text = text[:start] + nblk + text[end:]
    PCB.write_text(text, encoding="utf-8")
    print(f"aligned {n} footprints, grid {GRID} mm")


if __name__ == "__main__":
    main()
