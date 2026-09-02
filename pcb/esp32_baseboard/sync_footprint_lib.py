#!/usr/bin/env python3
"""Rewrite the .pretty library from the footprints actually placed on the board.

gen_power_carrier.py emits each footprint twice: once into
libraries/ESP32_Carrier.pretty/*.kicad_mod and once inline in the .kicad_pcb.
The two code paths drifted, so KiCad reported every part as "does not match
copy in library". Rather than keep two emitters in step by hand, the library is
regenerated from what is on the board -- the board is the artifact that gets
fabricated, so it is the right master.

The un-placing is done by **KiCad's own writer**, not by rewriting the
s-expression here. A hand-rolled normalisation got 7 of 20 parts right and left
17 warnings standing: every footprint placed at rot 180 mismatched, because
KiCad does not simply zero the text angles when it lifts a part off the board --
for a back-side part it flips the geometry to the front, which negates y while
*keeping* the stored text angle at 180. Matching that by regex is guesswork;
asking KiCad to write the file is exact.

This needs pcbnew, so the script re-runs itself under KiCad's bundled Python
when imported from a plain interpreter.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PCB = ROOT / "esp32_baseboard.kicad_pcb"
PRETTY = ROOT / "libraries" / "ESP32_Carrier.pretty"
LIB_PREFIX = "ESP32_Carrier:"
LIB_REFERENCE = "REF**"


def _kicad_python() -> Path | None:
    base = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "KiCad"
    if not base.is_dir():
        return None
    hits = sorted(base.glob("*/bin/python.exe"), reverse=True)
    return hits[0] if hits else None


def main() -> int:
    try:
        import pcbnew  # noqa: PLC0415
    except ImportError:
        py = _kicad_python()
        if py is None:
            print("FAIL: pcbnew not importable and no KiCad Python found")
            return 1
        return subprocess.run([str(py), str(Path(__file__).resolve())]).returncode

    board = pcbnew.LoadBoard(str(PCB))
    io = pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.KICAD_SEXP)
    PRETTY.mkdir(parents=True, exist_ok=True)

    seen: set[str] = set()
    written = 0
    for fp in board.GetFootprints():
        fpid = fp.GetFPID()
        if fpid.GetLibNickname().wx_str() != LIB_PREFIX.rstrip(":"):
            continue
        name = fpid.GetLibItemName().wx_str()
        if name in seen:
            continue
        seen.add(name)
        # The designator belongs to the instance; a library part carries the
        # placeholder. Mutating the in-memory board is safe -- it is never saved.
        fp.SetReference(LIB_REFERENCE)
        before = ""
        path = PRETTY / f"{name}.kicad_mod"
        if path.is_file():
            before = path.read_text(encoding="utf-8")
        io.FootprintSave(str(PRETTY), fp)
        if path.read_text(encoding="utf-8") != before:
            written += 1

    print(f"footprint library synced from board: {len(seen)} parts, {written} rewritten")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
