#!/usr/bin/env python3
"""Route modules/m2_opto4.kicad_pcb with the in-house A* maze router.

Unlike route_freerouting.py (Java, external jar), this is the "traditional"
in-house router (maze_router.py) already used by gen_power_carrier.py for the
main carrier — pure Python, no external tools. The module board is small
(14 nets, 15 footprints) so a full autoroute + open-island repair pass is
enough; the carrier's emit_service_buses() is skipped since it hardcodes
carrier-only net ids/refs (TFT/HMI channels) that don't exist here.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from maze_router import (
    autoroute_pads,
    format_routes,
    inject_routes,
    parse_hole_sites,
    parse_kept_vias,
    parse_pads,
    repair_open_pcb,
    strip_routes,
)

HERE = Path(__file__).resolve().parent
PCB = HERE / "modules" / "m2_opto4.kicad_pcb"

# Edge.Cuts bbox baked in gen_m2(): (10,10) .. (36,44) -> 26x34 mm.
OX, OY, BW, BH = 10.0, 10.0, 26.0, 34.0


def uid() -> str:
    return str(uuid.uuid4())


def main() -> int:
    text = PCB.read_text(encoding="utf-8")
    text = strip_routes(text)  # no-op today (board is place-only) but idempotent
    pads = parse_pads(text)
    kept = parse_kept_vias(text)
    hole_sites = parse_hole_sites(text)
    print(
        f"Maze autoroute: {len(pads)} pads, {len(hole_sites)} drill sites, "
        f"board {BW:.0f}x{BH:.0f} mm @ origin ({OX},{OY})"
    )
    result = autoroute_pads(pads, OX, OY, BW, BH, kept, grid=0.55, hole_sites=hole_sites)
    print(
        f"Maze result: {len(result.segments)} segments, {len(result.vias)} vias, "
        f"{len(result.failed)} failed edges"
    )
    for net, name, axy, bxy in result.failed[:20]:
        print(f"  FAIL net {net} {name} {axy} -> {bxy}")
    text = inject_routes(text, format_routes(result, uid))

    print("Repair open copper islands…")
    total_repair_failed = 0
    for rnd in range(12):
        text, repair = repair_open_pcb(text, OX, OY, BW, BH, uid_fn=uid)
        print(f"  round {rnd + 1}: +{len(repair.segments)} segments, {len(repair.failed)} failed")
        total_repair_failed = len(repair.failed)
        if not repair.segments:
            break

    if not text.endswith("\n"):
        text += "\n"
    PCB.write_text(text, encoding="utf-8")
    print(f"routed -> {PCB}")
    return 0 if (not result.failed and total_repair_failed == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
