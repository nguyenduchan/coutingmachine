#!/usr/bin/env python3
"""Copy footprint (x, y, rot) from the live PCB into placement_saved.py.

Also dumps copper routes into routes_saved.sexpr (see dump_saved_routes.py).

Run after hand-edits in pcbnew (save the board first):

  python dump_saved_pos.py
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PCB = ROOT / "STM32G030C8T6.kicad_pcb"
OUT = ROOT / "placement_saved.py"


def parse_pcb(text: str) -> tuple[float, float, float, float, dict[str, tuple[float, float, float]]]:
    em = re.search(
        r"\(gr_rect\s*\(start\s+([\d.-]+)\s+([\d.-]+)\)\s*\(end\s+([\d.-]+)\s+([\d.-]+)\)"
        r"[\s\S]*?Edge\.Cuts",
        text,
    )
    if not em:
        raise SystemExit("FAIL: no Edge.Cuts rect")
    x0, y0, x1, y1 = map(float, em.groups())
    anchors: dict[str, tuple[float, float, float]] = {}
    i = 0
    while True:
        p = text.find("(footprint ", i)
        if p < 0:
            break
        depth = 0
        end = None
        for j in range(p, len(text)):
            if text[j] == "(":
                depth += 1
            elif text[j] == ")":
                depth -= 1
                if depth == 0:
                    end = j
                    break
        if end is None:
            break
        blk = text[p : end + 1]
        i = end + 1
        ref_m = re.search(r'\(property "Reference" "([^"]+)"', blk)
        at = re.search(r"\(at\s+([\d.-]+)\s+([\d.-]+)(?:\s+([\d.-]+))?\)", blk)
        if not ref_m or not at:
            continue
        anchors[ref_m.group(1)] = (
            float(at.group(1)),
            float(at.group(2)),
            float(at.group(3) or 0),
        )
    return x0, y0, x1, y1, anchors


def fmt(v: float) -> str:
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return s if s else "0"


def main() -> int:
    text = PCB.read_text(encoding="utf-8")
    x0, y0, x1, y1, pos = parse_pcb(text)
    bw, bh = x1 - x0, y1 - y0
    lines = [
        "#!/usr/bin/env python3",
        '"""Hand-tuned footprint poses from STM32G030C8T6.kicad_pcb.',
        "",
        "Source of truth for generator sticky placement. Refresh after pcbnew edits:",
        "  python dump_saved_pos.py",
        '"""',
        "from __future__ import annotations",
        "",
        f"SAVED_OX = {fmt(x0)}",
        f"SAVED_OY = {fmt(y0)}",
        f"SAVED_BOARD_W = {fmt(bw)}",
        f"SAVED_BOARD_H = {fmt(bh)}",
        "",
        "# ref -> KiCad footprint origin (at x y rot_deg)",
        "SAVED_POS: dict[str, tuple[float, float, float]] = {",
    ]
    for ref in sorted(pos):
        x, y, r = pos[ref]
        lines.append(f'    "{ref}": ({fmt(x)}, {fmt(y)}, {fmt(r)}),')
    lines.append("}")
    lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT.name}: {len(pos)} parts, board {bw:.0f}x{bh:.0f} origin=({x0:g},{y0:g})")

    from dump_saved_routes import main as dump_routes

    dump_routes()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
