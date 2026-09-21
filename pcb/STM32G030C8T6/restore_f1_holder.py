#!/usr/bin/env python3
"""Restore F1 to the visible 5x20 open holder (schematic symbol name).

The 2410 SMT is ~6 mm with hidden silk, so F1 disappears in pcbnew.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PCB = HERE / "STM32G030C8T6.kicad_pcb"
SCH = HERE / "STM32G030C8T6.kicad_sch"
PRETTY = HERE / "libraries" / "STM32G030C8T6.pretty"
FP = "Fuse_Holder_5x20_Open"
# Pose comes from placement_saved / live PCB — do not hardcode board-size coords.
F1_AT = None  # filled from current F1 (at ...) when restoring


def _block(text: str, start: int) -> str:
    d, i = 0, start
    while i < len(text):
        if text[i] == "(":
            d += 1
        elif text[i] == ")":
            d -= 1
            if d == 0:
                return text[start : i + 1]
        i += 1
    raise ValueError("unbalanced")


def restore_pcb() -> None:
    text = PCB.read_text(encoding="utf-8")
    hit = None
    for m in re.finditer(r'\n\t\(footprint "', text):
        blk = _block(text, m.start() + 1)
        if '(property "Reference" "F1"' in blk:
            hit = (m.start() + 1, blk)
            break
    if hit is None:
        raise SystemExit("F1 not found on PCB")
    start, old = hit
    at_m = re.search(r"\(at\s+[-\d.]+\s+[-\d.]+(?:\s+[-\d.]+)?\)", old)
    f1_at = at_m.group(0) if at_m else "(at 75 123)"
    nets: dict[str, str] = {}
    starts = [m.start() for m in re.finditer(r'\(pad "', old)]
    for i, s in enumerate(starts):
        chunk = old[s : (starts[i + 1] if i + 1 < len(starts) else len(old))]
        num = re.match(r'\(pad "([^"]*)"', chunk)
        net = re.search(r'\(net\s+\d+\s+"([^"]*)"\)', chunk) or re.search(
            r'\(net "([^"]*)"\)', chunk
        )
        if num and net:
            nets[num.group(1)] = net.group(1)
    uid = re.search(r'\(uuid "[^"]+"\)', old)
    uid_s = uid.group(0) if uid else f'(uuid "{os.urandom(8).hex()}")'
    mod = (PRETTY / f"{FP}.kicad_mod").read_text(encoding="utf-8").strip()
    inner = mod[mod.find("\n") + 1 : -1].rstrip()
    keep: list[str] = []
    i = 0
    while i < len(inner):
        p = inner.find("(", i)
        if p < 0:
            break
        blk = _block(inner, p)
        if not (blk.startswith("(property ") or blk.startswith("(version ")
                or blk.startswith("(generator ") or blk.startswith("(layer ")):
            keep.append(blk)
        i = p + len(blk)
    inner = "\n\t\t".join(keep)
    for num, net in nets.items():
        inner = re.sub(
            rf'(\(pad "{re.escape(num)}"[\s\S]*?\(layers [^)]+\))',
            rf'\1\n\t\t\t(net 0 "{net}")',
            inner,
            count=1,
        )
    new_blk = (
        f'(footprint "STM32G030C8T6:{FP}"\n'
        f'\t\t(layer "F.Cu")\n'
        f"\t\t{uid_s}\n"
        f"\t\t{f1_at}\n"
        f'\t\t(property "Reference" "F1"\n'
        f'\t\t\t(at 0 -5.2 0)\n'
        f'\t\t\t(layer "F.SilkS")\n'
        f'\t\t\t(effects (font (size 1.0 1.0) (thickness 0.15))))\n'
        f'\t\t(property "Value" "T2A"\n'
        f'\t\t\t(at 0 5.2 0)\n'
        f'\t\t\t(layer "F.SilkS")\n'
        f'\t\t\t(effects (font (size 0.8 0.8) (thickness 0.12))))\n'
        f"{inner}\n\t)"
    )
    PCB.write_text(text[:start] + new_blk + text[start + len(old) :], encoding="utf-8")
    print(f"PCB F1 → {FP} at {f1_at} nets={nets}")

def restore_sch() -> None:
    text = SCH.read_text(encoding="utf-8")
    n = text.count("STM32G030C8T6:Fuse_2410")
    text = text.replace("STM32G030C8T6:Fuse_2410", f"STM32G030C8T6:{FP}")
    SCH.write_text(text, encoding="utf-8")
    print(f"SCH Fuse_2410 → {FP} ({n} hits)")


if __name__ == "__main__":
    restore_pcb()
    restore_sch()
