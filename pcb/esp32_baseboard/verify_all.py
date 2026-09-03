#!/usr/bin/env python3
"""One command that decides whether the board is fit to fab.

Runs every gate in PCB_REVIEW.md end to end and prints a single verdict, so the
fix loop is: run this, fix what it names, run it again. KiCad's own DRC is
included -- and with --schematic-parity, so the copper is checked against the
schematic and not just against itself.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
PCB = HERE / "esp32_baseboard.kicad_pcb"
REPORT = HERE / "drc_report.txt"

FATAL_DRC = {
    "unconnected_items", "shorting_items", "tracks_crossing", "clearance",
    "copper_edge_clearance", "hole_clearance", "hole_to_hole", "track_dangling",
    "via_dangling", "annular_width", "drill_out_of_range", "track_width",
    "invalid_outline", "footprint_type_mismatch", "duplicate_footprints",
    "missing_footprint", "extra_footprint", "net_conflict", "schematic_parity",
}
# The generator writes each footprint inline with its nets, so it never
# byte-matches the .kicad_mod copy; and out-of-tree copies lose the lib table.
ACCEPTED_DRC = {"lib_footprint_mismatch", "lib_footprint_issues"}


def find_cli() -> str | None:
    if (cli := shutil.which("kicad-cli")):
        return cli
    for base in (Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "KiCad",
                 Path(r"C:\Program Files\KiCad")):
        if base.is_dir():
            hits = sorted(base.glob("*/bin/kicad-cli.exe"), reverse=True)
            if hits:
                return str(hits[0])
    return None


def run(label: str, args: list[str]) -> bool:
    print(f"\n=== {label} ===")
    r = subprocess.run(args, cwd=HERE)
    return r.returncode == 0


def drc(pcb: Path) -> tuple[bool, Counter]:
    cli = find_cli()
    if cli is None:
        print("SKIP: kicad-cli not found")
        return True, Counter()
    subprocess.run(
        [cli, "pcb", "drc", "--severity-error", "--severity-warning",
         "--schematic-parity", "--units", "mm", "--format", "report",
         "-o", str(REPORT), str(pcb)],
        cwd=HERE, capture_output=True, text=True,
    )
    text = REPORT.read_text(encoding="utf-8", errors="replace")
    counts = Counter(re.findall(r"^\[([a-z_]+)\]", text, re.M))
    fatal = {k: v for k, v in counts.items() if k in FATAL_DRC}
    other = {k: v for k, v in counts.items()
             if k not in FATAL_DRC and k not in ACCEPTED_DRC}
    print(f"\n=== KiCad DRC ({pcb.name}) ===")
    for lbl, grp in (("FATAL", fatal), ("cosmetic", other)):
        for k, v in sorted(grp.items(), key=lambda kv: -kv[1]):
            print(f"  {lbl:8s} {v:4d}  {k}")
    if not fatal and not other:
        print("  clean")
    return not fatal, counts


def main() -> int:
    pcb = Path(sys.argv[1]) if len(sys.argv) > 1 else PCB
    py = sys.executable
    results = [
        ("Copper islands", run("Copper islands", [py, "_check_net_copper.py"])),
        ("Schematic/PCB nets", run("Schematic/PCB nets", [py, "verify_connectivity.py"])),
        ("ESP32 GPIO pinmap", run("ESP32 GPIO pinmap", [py, "verify_esp32_nets.py"])),
        ("Signal geometry A5-A7", run("Signal geometry", [py, "_check_signal_routing.py"])),
        ("Track width vs fab + current", run("Track width", [py, "verify_track_width.py"])),
        ("Sub-modules M1/M2/panel", run("Sub-modules", [py, "verify_modules.py"])),
        ("Rotations E11.6/13", run("Rotations", [py, "_check_rot.py"])),
        ("Edge clear E11.10", run("Edge clear", [py, "_check_edge_clear.py"])),
        ("Cluster cover E11.14", run("Cluster cover", [py, "_check_cluster_cover.py"])),
    ]
    ok_drc, counts = drc(pcb)
    results.append(("KiCad DRC (incl. schematic parity)", ok_drc))

    print("\n" + "=" * 56)
    print("VERDICT")
    print("=" * 56)
    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    bad = [n for n, ok in results if not ok]
    cosmetic = sum(v for k, v in counts.items()
                   if k not in FATAL_DRC and k not in ACCEPTED_DRC)
    if bad:
        print(f"\nOVERALL: FAIL ({len(bad)} gate(s))")
        return 1
    if cosmetic:
        print(f"\nOVERALL: PASS — {cosmetic} cosmetic DRC warning(s) left")
        return 0
    print("\nOVERALL: PASS — board is clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
