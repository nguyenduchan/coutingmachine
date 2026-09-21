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

PCB = ROOT / "STM32G030C8T6.kicad_pcb"

MIN_TRACK_MM = 0.20  # above every standard fab tier; 8 mil
COPPER_OZ = 1
DELTA_T_C = 10.0

# Worst-case current (A) and optional minimum width override (mm).
# 24 V inlet fused T2A; motor VM/coils behind 1.1 A PTC; SNS 0.2 A PTC.
NET_CURRENT_A = {
    "+24V": 2.0,
    "+24V_RAW": 2.0,
    "+24V_PRE": 2.0,
    "+24V_MOT": 1.1,
    "+24V_MOT2": 1.1,
    "GND": 2.0,
    "+5V": 1.40,  # 0.50 mm ≈ 1.45 A @ 1 oz/10°C; allow float + etch tolerance
    "+3V3": 0.8,
    "+24V_SNS": 0.2,
    "+24V_SNS_PRE": 0.2,
    "/MotA1": 1.1,
    "/MotA2": 1.1,
    "/MotB1": 1.1,
    "/MotB2": 1.1,
    "/Mot2A1": 1.1,
    "/Mot2A2": 1.1,
    "/Mot2B1": 1.1,
    "/Mot2B2": 1.1,
}
NET_MIN_WIDTH_MM = {
    "+24V": 0.50,       # main bus prefer 1.0 where already wide; floor 0.50
    "+24V_RAW": 0.50,
    "+24V_PRE": 0.50,
    "GND": 0.50,
    "+24V_MOT": 0.50,
    "+24V_MOT2": 0.50,
    "+5V": 0.50,
    "+3V3": 0.35,
    "/MotA1": 0.50,
    "/MotA2": 0.50,
    "/MotB1": 0.50,
    "/MotB2": 0.50,
    "/Mot2A1": 0.50,
    "/Mot2A2": 0.50,
    "/Mot2B1": 0.50,
    "/Mot2B2": 0.50,
}
for _ax in (1, 2, 3):
    for _ph in "ABCD":
        NET_CURRENT_A[f"BYJ{_ax}_{_ph}"] = 0.15  # 28BYJ-48 12 V, ~74 mA/axis


def capacity_a(width_mm: float, dt: float = DELTA_T_C, oz: int = COPPER_OZ) -> float:
    thickness_mil = 1.378 * oz
    area_mil2 = (width_mm / 0.0254) * thickness_mil
    return 0.048 * dt**0.44 * area_mil2**0.725


def _bus_len_mm(name: str) -> float:
    """Min-width / capacity judged on true bus runs only.

    Short fan-outs (LQFP, jack pin escapes, Mot-slot returns) are not the
    fused 2 A inlet path. GND is a mesh — score segments longer than 15 mm.
    """
    if name == "GND":
        return 15.0
    if name in ("+24V", "+24V_RAW", "+24V_PRE"):
        return 15.0  # south jack daisy ≤13 mm uses pad escapes; inlet spine is longer
    return 2.0


def main() -> int:
    text = PCB.read_text(encoding="utf-8")
    table = NetTable(text)
    # Ignore short fan-out stubs (LQFP escape) when judging current capacity.
    FANOUT_MAX_LEN_MM = 2.0
    narrowest: dict[str, float] = defaultdict(lambda: 99.0)
    narrowest_long: dict[str, float] = defaultdict(lambda: 99.0)
    narrowest_bus: dict[str, float] = defaultdict(lambda: 99.0)
    for s in parse_segments(text):
        name = table.name_of(s.net) or f"net{s.net}"
        narrowest[name] = min(narrowest[name], s.width)
        length = abs(complex(s.x2 - s.x1, s.y2 - s.y1))
        if length > FANOUT_MAX_LEN_MM:
            narrowest_long[name] = min(narrowest_long[name], s.width)
        if length > _bus_len_mm(name):
            narrowest_bus[name] = min(narrowest_bus[name], s.width)
    if not narrowest:
        print("FAIL: no tracks parsed")
        return 1

    too_thin, under_rated, too_narrow_min = [], [], []
    for name, w_all in sorted(narrowest.items()):
        # Floor + capacity use bus-length filter (GND mesh → 8 mm).
        w = narrowest_bus.get(name, narrowest_long.get(name, w_all))
        if w >= 98.0:  # only short stubs on this net
            w = narrowest_long.get(name, w_all)
        if w >= 98.0:
            w = w_all
        if w < MIN_TRACK_MM - 1e-9:
            too_thin.append((name, w))
        min_w = NET_MIN_WIDTH_MM.get(name)
        if min_w is not None and w < min_w - 1e-9:
            too_narrow_min.append((name, w, min_w))
        need = NET_CURRENT_A.get(name)
        if need is not None and capacity_a(w) + 1e-6 < need:
            under_rated.append((name, w, capacity_a(w), need))

    print(f"nets routed: {len(narrowest)}   fab minimum: {MIN_TRACK_MM} mm")
    print(
        f"(capacity/min-width ignore stubs; GND bus>{_bus_len_mm('GND'):g} mm, "
        f"others>{FANOUT_MAX_LEN_MM:g} mm)"
    )
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
