#!/usr/bin/env python3
"""Route the current carrier: FreeRouting first, A* maze for leftovers.

Does not call gen_compact_carrier / route_4layer (those wipe silk / F1).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
PCB = HERE / "STM32G030C8T6.kicad_pcb"
KICAD_PY = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "KiCad" / "10.0" / "bin" / "python.exe"
OX, OY, BW, BH = 50.0, 50.0, 180.0, 120.0


def _kicad() -> str:
    if KICAD_PY.is_file():
        return str(KICAD_PY)
    return sys.executable


def run_freerouting() -> bool:
    env = os.environ.copy()
    # Inherit FR_ATTEMPTS from the environment; otherwise route_freerouting.py
    # uses its A2 table (do not weaken to 10:50 — that leaves dozens of opens).
    env["FR_TIMEOUT_S"] = os.environ.get("FR_TIMEOUT_S") or "900"
    env["SKIP_FANOUT"] = "1"
    env["FR_KEEP_TRACKS"] = os.environ.get("FR_KEEP_TRACKS") or "0"
    r = subprocess.run(
        [_kicad(), str(HERE / "route_freerouting.py")],
        cwd=str(HERE),
        env=env,
    )
    return r.returncode in (0, 1)


def maze_repair() -> None:
    os.environ.setdefault("MAZE_EXPAND", "40000")
    from maze_router import repair_open_pcb

    uid = lambda: str(uuid.uuid4())
    text = PCB.read_text(encoding="utf-8")
    for rnd in range(1, 3):
        text, repair = repair_open_pcb(text, OX, OY, BW, BH, uid_fn=uid)
        print(f"  repair {rnd}: +{len(repair.segments)} segs, {len(repair.failed)} failed")
        if not repair.segments:
            break
    PCB.write_text(text, encoding="utf-8")


def maze_full() -> None:
    os.environ["MAZE_PASSES"] = os.environ.get("MAZE_PASSES", "2")
    os.environ.setdefault("MAZE_EXPAND", "40000")
    from maze_router import (
        autoroute_pads,
        format_routes,
        inject_routes,
        parse_hole_sites,
        parse_kept_vias,
        parse_pads,
        strip_routes,
        repair_open_pcb,
    )
    from pin_row_keepout import pin_row_rects

    text = strip_routes(PCB.read_text(encoding="utf-8"))
    pads = parse_pads(text)
    kept = parse_kept_vias(text)
    holes = parse_hole_sites(text)
    rects = [b[:4] for b in pin_row_rects(text)]
    print(f"Maze autoroute: {len(pads)} pads, {len(rects)} pin-row keepouts")
    result = autoroute_pads(
        pads, OX, OY, BW, BH, kept, grid=0.55, hole_sites=holes, rect_keepouts=rects
    )
    print(
        f"  +{len(result.segments)} segs +{len(result.vias)} vias, "
        f"{len(result.failed)} failed"
    )
    uid = lambda: str(uuid.uuid4())
    text = inject_routes(text, format_routes(result, uid))
    for rnd in range(1, 3):
        text, repair = repair_open_pcb(text, OX, OY, BW, BH, uid_fn=uid)
        print(f"  repair {rnd}: +{len(repair.segments)} segs, {len(repair.failed)} failed")
        if not repair.segments:
            break
    PCB.write_text(text, encoding="utf-8")


def fill_zones() -> None:
    env = os.environ.copy()
    env["SKIP_FANOUT"] = "1"
    subprocess.check_call(
        [_kicad(), str(HERE / "route_freerouting.py"), "--fill-zones"],
        cwd=str(HERE),
        env=env,
    )


def enforce_via_edge() -> None:
    subprocess.check_call(
        [_kicad(), str(HERE / "enforce_via_edge.py")],
        cwd=str(HERE),
    )


def main() -> int:
    bak = HERE / "out_freerouting" / "pre_route.kicad_pcb"
    bak.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PCB, bak)
    print(f"backup -> {bak.name}")
    skip_fr = os.environ.get("FR_SKIP", "0") == "1"
    ses = HERE / "out_freerouting" / "STM32G030C8T6.ses"
    if ses.exists():
        ses.unlink()
    fr_ok = False if skip_fr else run_freerouting()
    print(f"FreeRouting {'skipped' if skip_fr else ('got SES' if fr_ok else 'no SES')}")
    if fr_ok:
        maze_repair()
    else:
        # maze_full strips every track; PCB_REVIEW forbids it after a SES, and
        # without a SES it would still wipe the live board. Leave copper as-is.
        print("FreeRouting produced no SES — skip maze_full (would wipe copper)")
        return 2
    os.environ["SKIP_FANOUT"] = "1"
    enforce_via_edge()
    maze_repair()
    fill_zones()
    print(f"routed -> {PCB.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
