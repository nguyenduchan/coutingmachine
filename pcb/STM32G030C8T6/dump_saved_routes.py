#!/usr/bin/env python3
"""Copy copper routes (segment/via/arc/zone) from the live PCB into routes_saved.sexpr.

Run after hand-routing in pcbnew (save the board first):

  python dump_saved_pos.py      # also dumps routes
  python dump_saved_routes.py   # routes only

gen_compact_carrier.py re-injects these on regen so tracks survive footprint rebuilds.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PCB = ROOT / "STM32G030C8T6.kicad_pcb"
OUT = ROOT / "routes_saved.sexpr"

ROUTE_KINDS = ("segment", "via", "arc", "zone")


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


def extract_routes(text: str) -> list[str]:
    blocks: list[str] = []
    for m in re.finditer(r"\n\t\((segment|via|arc|zone)\b", text):
        # match is "\n\t(" — open paren is at start+2
        blocks.append(_block(text, m.start() + 2))
    return blocks


def main() -> int:
    if not PCB.exists():
        raise SystemExit(f"FAIL: missing {PCB}")
    text = PCB.read_text(encoding="utf-8")
    blocks = extract_routes(text)
    counts = {k: 0 for k in ROUTE_KINDS}
    for b in blocks:
        head = b.lstrip()
        for k in ROUTE_KINDS:
            if head.startswith(f"({k}"):
                counts[k] += 1
                break
    header = (
        f"; sticky copper routes from {PCB.name}\n"
        f"; regenerate: python dump_saved_routes.py\n"
        f"; counts: " + " ".join(f"{k}={counts[k]}" for k in ROUTE_KINDS) + "\n"
    )
    body = "\n".join(blocks)
    OUT.write_text(header + (body + "\n" if body else ""), encoding="utf-8")
    print(
        f"Wrote {OUT.name}: "
        + ", ".join(f"{k}={counts[k]}" for k in ROUTE_KINDS)
        + f" (total {len(blocks)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
