#!/usr/bin/env python3
"""Mandatory pre-fab review gate for esp32_baseboard.

Runs all automated checks listed in PCB_REVIEW.md.
Exit 0 = ready for KiCad DRC + human sign-off; non-zero = do not order PCB.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PCB = ROOT / "esp32_baseboard.kicad_pcb"

# Actual board size: 2026-09-04 resized snug to components (185.8x96.2, 5mm
# edge clear), then 2026-09-05 rounded up to 190x100 (extra margin split evenly
# on all 4 sides). gen_power_carrier.py's BOARD_W/BOARD_H stay 180x145 --
# that's the from-scratch generator default, not used since current layout is
# hand-placed.
BOARD_W_MM = 190.0
BOARD_H_MM = 100.0
# FreeRouting uses pad→via→B.Cu (A0/A8); budget is a soft cap, not maze-era 12.
MAX_ROUTING_VIAS = 120


def _banner(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def _run_script(name: str, script: str, required: bool = True) -> bool:
    _banner(name)
    r = subprocess.run([sys.executable, str(ROOT / script)], cwd=ROOT)
    ok = r.returncode == 0
    tag = "PASS" if ok else ("WARN" if not required else "FAIL")
    print(f"-> {tag} ({script})")
    return ok if required else True


def _check_board_outline() -> bool:
    _banner("Board outline + routing policy")
    text = PCB.read_text(encoding="utf-8")
    # Prefer Edge.Cuts gr_rect whose layer is in the same block (not a later object).
    w = h = None
    for chunk in text.split("(gr_rect")[1:]:
        head, _, rest = chunk.partition("\n\t)")
        if 'layer "Edge.Cuts"' not in head and "(layer \"Edge.Cuts\")" not in head:
            # also accept multiline layer before closing
            if "Edge.Cuts" not in head.split("(gr_", 1)[0]:
                continue
        st = re.search(r"\(start\s+([\d.-]+)\s+([\d.-]+)\)", head)
        en = re.search(r"\(end\s+([\d.-]+)\s+([\d.-]+)\)", head)
        if not st or not en:
            continue
        x1, y1 = float(st.group(1)), float(st.group(2))
        x2, y2 = float(en.group(1)), float(en.group(2))
        cw, ch = abs(x2 - x1), abs(y2 - y1)
        if cw < 50 or ch < 50:
            continue  # skip silk/callout boxes that share Edge.Cuts by mistake
        w, h = cw, ch
        break
    if w is None:
        edges = re.findall(
            r'\(gr_line\s+\(start\s+([\d.-]+)\s+([\d.-]+)\)\s+\(end\s+([\d.-]+)\s+([\d.-]+)\)'
            r'[\s\S]*?\(layer\s+"Edge\.Cuts"\)',
            text,
        )
        if not edges:
            print("FAIL: no Edge.Cuts outline")
            return False
        xs = [float(a) for a, b, c, d in edges] + [float(c) for a, b, c, d in edges]
        ys = [float(b) for a, b, c, d in edges] + [float(d) for a, b, c, d in edges]
        w, h = max(xs) - min(xs), max(ys) - min(ys)
    print(f"outline: {w:.1f} x {h:.1f} mm (expect {BOARD_W_MM} x {BOARD_H_MM})")
    ok_w = abs(w - BOARD_W_MM) < 0.6
    ok_h = abs(h - BOARD_H_MM) < 0.6
    if not ok_w or not ok_h:
        print("FAIL: board size mismatch")
        return False

    vias = len(re.findall(r"\(via\s", text))
    print(f"routing vias: {vias} (max allowed {MAX_ROUTING_VIAS})")
    if vias > MAX_ROUTING_VIAS:
        print("FAIL: too many routing vias — must stay a last resort")
        return False

    print("PASS outline + via budget")
    return True


def main() -> int:
    if not PCB.is_file():
        print(f"FAIL: missing {PCB}")
        return 1

    results: list[tuple[str, bool]] = []
    results.append(("Board outline / vias", _check_board_outline()))
    results.append(("Copper islands", _run_script("Copper connectivity", "_check_net_copper.py")))
    results.append(("Schematic/PCB nets", _run_script("Net assignment", "verify_connectivity.py")))
    results.append(("ESP32 GPIO pinmap", _run_script("GPIO safety", "verify_esp32_nets.py")))
    results.append(
        ("Signal routing (A5-A7)", _run_script("Signal geometry", "_check_signal_routing.py"))
    )
    # KiCad's own DRC is the authority. The Python checks above only model the
    # board, and a run once passed every one of them while KiCad found 380
    # violations, so the real DRC is part of the gate, not a manual tick.
    results.append(("KiCad DRC", _run_script("KiCad DRC", "verify_drc.py")))

    _banner("Track clearance (advisory)")
    r = subprocess.run([sys.executable, str(ROOT / "_check_overlaps.py")], cwd=ROOT)
    clearance_ok = r.returncode == 0
    print(f"-> {'PASS' if clearance_ok else 'WARN'} (_check_overlaps.py -- confirm in KiCad DRC)")

    _banner("REVIEW GATE SUMMARY")
    fails = [name for name, ok in results if not ok]
    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not clearance_ok:
        print("  WARN  Track clearance heuristic (run KiCad DRC)")
    if fails:
        print(f"\nOVERALL: FAIL ({len(fails)} check(s))")
        print("See PCB_REVIEW.md — fix generator and re-run:")
        print("  python gen_power_carrier.py && python verify_pcb.py")
        return 1
    print("\nOVERALL: PASS (automated gate)")
    print("Next: open KiCad, Run DRC, complete manual checklist in PCB_REVIEW.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
