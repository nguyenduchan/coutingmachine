#!/usr/bin/env python3
"""Run KiCad's own DRC and gate on it.

The Python checks in this directory model the board; KiCad's DRC *is* the
board. Leaving it as a manual tick let a run pass every local gate while KiCad
found 380 violations and 29 unconnected items, so it belongs in the automated
gate. Needs kicad-cli on PATH or in the usual Windows install location.
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

# Categories that make the board wrong rather than untidy. Everything else is
# reported but does not fail the gate.
FATAL = {
    "unconnected_items",
    "shorting_items",
    "tracks_crossing",
    "clearance",
    "copper_edge_clearance",
    "hole_clearance",
    "hole_to_hole",
    "track_dangling",
    "via_dangling",
    "annular_width",
    "drill_out_of_range",
    "track_width",
    "invalid_outline",
}
# Known and accepted: the generator writes each footprint inline with its nets,
# so it never byte-matches the .kicad_mod copy in the library.
ACCEPTED = {"lib_footprint_mismatch"}


def find_cli() -> str | None:
    if (cli := shutil.which("kicad-cli")):
        return cli
    local = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "KiCad"
    for base in (local, Path(r"C:\Program Files\KiCad")):
        if base.is_dir():
            hits = sorted(base.glob("*/bin/kicad-cli.exe"), reverse=True)
            if hits:
                return str(hits[0])
    return None


def main() -> int:
    cli = find_cli()
    if cli is None:
        print("SKIP: kicad-cli not found — run DRC manually in KiCad")
        return 0
    proc = subprocess.run(
        [cli, "pcb", "drc", "--severity-error", "--severity-warning",
         "--units", "mm", "--format", "report", "-o", str(REPORT), str(PCB)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print(f"FAIL: kicad-cli drc exited {proc.returncode}\n{proc.stderr.strip()}")
        return 1

    text = REPORT.read_text(encoding="utf-8", errors="replace")
    counts = Counter(re.findall(r"^\[([a-z_]+)\]", text, re.M))
    fatal = {k: v for k, v in counts.items() if k in FATAL}
    other = {k: v for k, v in counts.items() if k not in FATAL and k not in ACCEPTED}
    accepted = {k: v for k, v in counts.items() if k in ACCEPTED}

    print(f"KiCad DRC ({Path(cli).parent.parent.name}) -> {REPORT.name}")
    for label, group in (("FATAL", fatal), ("cosmetic", other), ("accepted", accepted)):
        if group:
            print(f"  {label}:")
            for k, v in sorted(group.items(), key=lambda kv: -kv[1]):
                print(f"    {v:4d}  {k}")
    if not counts:
        print("  no violations")
    if fatal:
        print(f"FAIL: {sum(fatal.values())} electrical DRC violation(s)")
        return 1
    if other:
        print(f"PASS with {sum(other.values())} cosmetic warning(s)")
    else:
        print("PASS: KiCad DRC clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
