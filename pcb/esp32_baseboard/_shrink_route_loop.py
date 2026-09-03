# -*- coding: utf-8 -*-
"""Shrink carrier BOARD_W/H until FreeRouting can no longer finish; keep last OK.

Loop:
  1. set BOARD_W/H
  2. gen_power_carrier (PCB_SKIP_MAZE=1) — fail => placement too tight, stop
  3. verify_connectivity — fail => stop
  4. FreeRouting (quick then full on last OK)
  5. if unconnected > 0 => revert to previous size, full-route, exit

Usage:
  python _shrink_route_loop.py
  python _shrink_route_loop.py --step 10 --w-min 160 --h-min 120
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CARRIER = HERE / "gen_power_carrier.py"
PCB = HERE / "esp32_baseboard.kicad_pcb"
LOG = HERE / "_shrink_route.log"
KI_PY = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/KiCad/10.0/bin/python.exe"


def _log(msg: str) -> None:
    print(msg, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


def set_board_size(w: float, h: float) -> None:
    t = CARRIER.read_text(encoding="utf-8")
    t2, n1 = re.subn(
        r"^BOARD_W = [0-9.]+", f"BOARD_W = {w:.1f}", t, count=1, flags=re.M
    )
    t2, n2 = re.subn(
        r"^BOARD_H = [0-9.]+", f"BOARD_H = {h:.1f}", t2, count=1, flags=re.M
    )
    if n1 != 1 or n2 != 1:
        raise SystemExit(f"patch BOARD_W/H failed (n1={n1} n2={n2})")
    # keep BOARD_W_EXTRA consistent with historic 185 baseline
    t2, n3 = re.subn(
        r"^BOARD_W_EXTRA = BOARD_W - [0-9.]+",
        "BOARD_W_EXTRA = BOARD_W - 185.0",
        t2,
        count=1,
        flags=re.M,
    )
    CARRIER.write_text(t2, encoding="utf-8")
    _log(f"set BOARD {w:.0f}x{h:.0f}")


def read_board_size() -> tuple[float, float]:
    t = CARRIER.read_text(encoding="utf-8")
    w = float(re.search(r"^BOARD_W = ([0-9.]+)", t, re.M).group(1))
    h = float(re.search(r"^BOARD_H = ([0-9.]+)", t, re.M).group(1))
    return w, h


def run_gen() -> bool:
    env = os.environ.copy()
    env["PCB_SKIP_MAZE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run(
        [sys.executable, str(CARRIER)],
        cwd=str(HERE),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    (HERE / "_gen.log").write_text(r.stdout + "\n" + r.stderr, encoding="utf-8")
    if r.returncode != 0:
        tail = (r.stdout + r.stderr)[-800:]
        _log(f"GEN FAIL rc={r.returncode}\n{tail}")
        return False
    _log("GEN OK")
    return True


def run_verify() -> bool:
    r = subprocess.run(
        [sys.executable, str(HERE / "verify_connectivity.py")],
        cwd=str(HERE),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    _log(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "verify empty")
    return r.returncode == 0


def run_route(quick: bool) -> int:
    """Return unconnected count (0 = success). -1 = tool failure."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    if quick:
        env["FR_QUICK"] = "1"
    py = str(KI_PY) if KI_PY.is_file() else sys.executable
    r = subprocess.run(
        [py, str(HERE / "route_freerouting.py")],
        cwd=str(HERE),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = r.stdout + "\n" + r.stderr
    (HERE / "_route.log").write_text(out, encoding="utf-8")
    _log(out[-1200:])
    if "freerouting.jar not found" in out or "java found but too old" in out:
        return -1
    m = re.search(r"best attempt still leaves (\d+) unconnected", out)
    if m:
        return int(m.group(1))
    # any attempt with 0 unconnected
    zeros = re.findall(r": 0 unconnected", out)
    if zeros:
        return 0
    lefts = [int(x) for x in re.findall(r": (\d+) unconnected", out)]
    if lefts:
        return min(lefts)
    if r.returncode != 0:
        return -1
    return -1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", type=float, default=10.0)
    ap.add_argument("--w-min", type=float, default=150.0)
    ap.add_argument("--h-min", type=float, default=110.0)
    ap.add_argument("--start-w", type=float, default=None)
    ap.add_argument("--start-h", type=float, default=None)
    args = ap.parse_args()

    LOG.write_text("", encoding="utf-8")
    w0, h0 = read_board_size()
    w = float(args.start_w or w0)
    h = float(args.start_h or h0)
    set_board_size(w, h)

    last_ok: tuple[float, float] | None = None
    sizes: list[tuple[float, float]] = []
    # Shrink both dims each step; stop when gen (placement E11) or route fails
    cw, ch = w, h
    while cw >= args.w_min and ch >= args.h_min:
        sizes.append((cw, ch))
        cw -= args.step
        ch -= args.step
    # Also probe W-only / H-only one step below start (finer packing limits)
    if args.step >= 2:
        sizes.append((max(args.w_min, w - args.step), h))
        sizes.append((w, max(args.h_min, h - args.step)))

    # de-dupe preserving order
    seen = set()
    uniq = []
    for s in sizes:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    sizes = uniq

    _log(f"plan sizes: {sizes}")

    for wi, hi in sizes:
        set_board_size(wi, hi)
        _log(f"\n=== TRY {wi:.0f}x{hi:.0f} ===")
        if not run_gen():
            _log("stop: gen/placement cannot fit")
            break
        if not run_verify():
            _log("stop: connectivity fail")
            break
        left = run_route(quick=True)
        if left < 0:
            _log("stop: router tool failure")
            break
        if left > 0:
            _log(f"stop: {left} unconnected — cannot shrink further")
            break
        last_ok = (wi, hi)
        # snapshot successful routed PCB
        shutil.copy2(PCB, HERE / f"_ok_{int(wi)}x{int(hi)}.kicad_pcb")
        _log(f"OK routed {wi:.0f}x{hi:.0f}")

    if last_ok is None:
        _log("no successful shrink candidate; restoring start and full-route")
        set_board_size(w, h)
        run_gen()
        run_route(quick=False)
        return 1

    # Restore last OK and full-route for quality
    wi, hi = last_ok
    set_board_size(wi, hi)
    _log(f"\n=== FINAL {wi:.0f}x{hi:.0f} full route ===")
    if not run_gen() or not run_verify():
        return 1
    left = run_route(quick=False)
    _log(f"FINAL unconnected={left} size={wi:.0f}x{hi:.0f}")
    return 0 if left == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
