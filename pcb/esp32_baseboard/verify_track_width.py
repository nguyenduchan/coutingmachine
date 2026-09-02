#!/usr/bin/env python3
"""Check every track against fab capability and against the current it carries.

Two independent questions:

1. Is any track narrower than the board house can reliably etch? Standard
   (no-extra-cost) 2-layer capability is 5 mil = 0.127 mm at JLCPCB and 6 mil =
   0.153 mm at PCBWay/Aisler, so MIN_TRACK_MM below sits above all of them with
   room for hand rework.

2. Does each net's width carry its current? Capacity is IPC-2221 for an
   external conductor, I = 0.048 * dT^0.44 * A^0.725 with A in mil^2, at 1 oz
   copper and a 10 C rise -- the conservative pairing.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from maze_router import parse_segments  # noqa: E402
from pcb_parse import NetTable  # noqa: E402

PCB = ROOT / "esp32_baseboard.kicad_pcb"

MIN_TRACK_MM = 0.20  # above every standard fab tier; 8 mil
COPPER_OZ = 1
DELTA_T_C = 10.0

# Worst-case current (A) and optional minimum width override (mm).
# +12V budget matches 0.70 mm FR/maze width (~1.85 A @ 10 °C — burst stall OK).
NET_CURRENT_A = {
    "+12V": 1.8,
    "+12V_RAW": 1.8,
    "GND": 1.8,
    "+5V": 1.0,
    "+3V3": 0.5,
    "+12V_SNS": 0.05,
    "MotA1": 1.0,
    "MotA2": 1.0,
    "MotB1": 1.0,
    "MotB2": 1.0,
    "BLW_RET": 0.6,
}
NET_MIN_WIDTH_MM = {
    "MotA1": 0.34,
    "MotA2": 0.34,
    "MotB1": 0.34,
    "MotB2": 0.34,
    "+12V": 0.70,
    "+12V_RAW": 0.70,
    "GND": 0.70,
}
for _ax in (1, 2, 3):
    for _ph in "ABCD":
        NET_CURRENT_A[f"BYJ{_ax}_{_ph}"] = 0.15  # 28BYJ-48 12 V, ~74 mA/axis


def capacity_a(width_mm: float, dt: float = DELTA_T_C, oz: int = COPPER_OZ) -> float:
    thickness_mil = 1.378 * oz
    area_mil2 = (width_mm / 0.0254) * thickness_mil
    return 0.048 * dt**0.44 * area_mil2**0.725


def main() -> int:
    text = PCB.read_text(encoding="utf-8")
    table = NetTable(text)
    narrowest: dict[str, float] = defaultdict(lambda: 99.0)
    for s in parse_segments(text):
        name = table.name_of(s.net) or f"net{s.net}"
        narrowest[name] = min(narrowest[name], s.width)
    if not narrowest:
        print("FAIL: no tracks parsed")
        return 1

    too_thin, under_rated, too_narrow_min = [], [], []
    for name, w in sorted(narrowest.items()):
        if w < MIN_TRACK_MM - 1e-9:
            too_thin.append((name, w))
        min_w = NET_MIN_WIDTH_MM.get(name)
        if min_w is not None and w < min_w - 1e-9:
            too_narrow_min.append((name, w, min_w))
        need = NET_CURRENT_A.get(name)
        if need is not None and capacity_a(w) < need:
            under_rated.append((name, w, capacity_a(w), need))

    print(f"nets routed: {len(narrowest)}   fab minimum: {MIN_TRACK_MM} mm")
    widths = sorted({round(w, 3) for w in narrowest.values()})
    print("widths used: " + ", ".join(f"{w:g} mm ({capacity_a(w):.2f} A)" for w in widths))

    if too_thin:
        print(f"\nFAIL: {len(too_thin)} net(s) below the fab minimum")
        for name, w in too_thin:
            print(f"  {name:16s} {w:.3f} mm")
    if under_rated:
        print(f"\nFAIL: {len(under_rated)} net(s) too narrow for their current"
              f" (1 oz, {DELTA_T_C:.0f} C rise)")
        for name, w, cap, need in under_rated:
            print(f"  {name:16s} {w:.3f} mm = {cap:.2f} A, needs {need:.2f} A")
    if too_narrow_min:
        print(f"\nFAIL: {len(too_narrow_min)} net(s) below required minimum width")
        for name, w, min_w in too_narrow_min:
            print(f"  {name:16s} {w:.3f} mm (need >= {min_w:.2f} mm)")
    if not too_thin and not under_rated and not too_narrow_min:
        print("\nPASS: every track clears the fab minimum and its current")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
