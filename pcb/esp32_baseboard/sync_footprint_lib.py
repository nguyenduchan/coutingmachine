#!/usr/bin/env python3
"""Rewrite the .pretty library from the footprints actually placed on the board.

gen_power_carrier.py emits each footprint twice: once into
libraries/ESP32_Carrier.pretty/*.kicad_mod and once inline in the .kicad_pcb.
The two code paths drifted -- different text sizes, a graphic present in one
and not the other -- so KiCad reported every part as
"does not match copy in library" (26 warnings).

Rather than keep two emitters in step by hand, the library is regenerated from
what is on the board: same pads, same graphics, by construction. The board is
the artifact that gets fabricated, so it is the right master.

Instance-specific parts are stripped: position, rotation, net assignments,
uuids, and the reference text (reset to REF**).
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PCB = ROOT / "esp32_baseboard.kicad_pcb"
PRETTY = ROOT / "libraries" / "ESP32_Carrier.pretty"


def _block(text: str, start: int) -> str:
    depth, i = 0, start
    while True:
        c = text[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
        i += 1


def to_module(blk: str, name: str) -> str:
    """Turn a placed footprint into a standalone .kicad_mod body."""
    out = blk
    # footprint-level placement and identity
    out = re.sub(r'^\t\(footprint "[^"]+"', f'(footprint "{name}"', out, count=1)
    out = re.sub(r"\n\t\t\(at [-\d.]+ [-\d.]+(?: [-\d.]+)?\)", "", out, count=1)
    out = re.sub(r'\n\t\t\(uuid "[^"]*"\)', "", out, count=1)
    # nets and uuids belong to the instance, not the library part
    out = re.sub(r'\n\s*\(net (?:\d+ )?"[^"]*"\)', "", out)
    out = re.sub(r'\n\s*\(uuid "[^"]*"\)', "", out)
    # a library footprint carries a placeholder designator
    out = re.sub(r'(\(property "Reference" )"[^"]*"', r'\1"REF**"', out, count=1)
    # library parts live on the front layer; placement decides the real side
    out = re.sub(r'\n\t\t\(layer "B\.Cu"\)', '\n\t(layer "F.Cu")', out, count=1)
    out = re.sub(r'\n\t\t\(layer "F\.Cu"\)', '\n\t(layer "F.Cu")', out, count=1)
    out = out.replace('\n\t\t(layer "B.SilkS")', '\n\t\t(layer "F.SilkS")')
    out = out.replace('\n\t\t\t(layer "B.SilkS")', '\n\t\t\t(layer "F.SilkS")')
    out = out.replace('\n\t\t(layer "B.Fab")', '\n\t\t(layer "F.Fab")')
    out = out.replace('\n\t\t\t(layer "B.Fab")', '\n\t\t\t(layer "F.Fab")')
    out = out.replace('\n\t\t(layer "B.CrtYd")', '\n\t\t(layer "F.CrtYd")')
    # Mirroring and text rotation come from how the instance is placed (back
    # layer, rot 180); the library part is the unplaced, front-side form.
    out = out.replace(" (justify mirror)", "").replace("(justify mirror)", "")
    # Text rotation is part of how the instance sits (rot 180), not part of
    # the library part, so drop the angle from every (at x y ang).
    out = re.sub(r"(\n\s*\(at [-\d.]+ [-\d.]+) [-\d.]+\)", r"\1 0)", out)
    # de-indent one level: the block was nested inside the board
    lines = out.split("\n")
    lines = [ln[1:] if ln.startswith("\t") else ln for ln in lines]
    body = "\n".join(ln for ln in lines if ln.strip())
    header = (
        f'(footprint "{name}"\n'
        "\t(version 20241229)\n"
        '\t(generator "sync_footprint_lib.py")\n'
        '\t(generator_version "1.0")\n'
    )
    body = re.sub(r'^\(footprint "[^"]+"\n', header, body, count=1)
    return body + "\n"


def main() -> int:
    text = PCB.read_text(encoding="utf-8")
    seen: set[str] = set()
    written = 0
    for m in re.finditer(r'\n\t\(footprint "ESP32_Carrier:([^"]+)"', text):
        name = m.group(1)
        if name in seen:
            continue
        seen.add(name)
        blk = _block(text, m.start() + 1)
        path = PRETTY / f"{name}.kicad_mod"
        new = to_module(blk, name)
        if not path.is_file() or path.read_text(encoding="utf-8") != new:
            path.write_text(new, encoding="utf-8")
            written += 1
    print(f"footprint library synced from board: {len(seen)} parts, {written} rewritten")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
