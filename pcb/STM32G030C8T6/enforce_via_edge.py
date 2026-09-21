#!/usr/bin/env python3
"""Remove vias <1 mm from component pads and copper <0.30 mm from Edge.Cuts."""
from __future__ import annotations

import re
import sys
from pathlib import Path

PCB = Path(__file__).with_name("STM32G030C8T6.kicad_pcb")
VIA_PAD_GAP_MM = 1.0
EDGE_MM = 0.3  # JLCPCB copper-to-edge house


def _board_box(text: str) -> tuple[float, float, float, float]:
    em = re.search(
        r"\(gr_rect\s*\(start\s+([\d.-]+)\s+([\d.-]+)\)\s*\(end\s+([\d.-]+)\s+([\d.-]+)\)"
        r"[\s\S]*?Edge\.Cuts",
        text,
    )
    if not em:
        raise SystemExit("FAIL: no Edge.Cuts rect")
    x0, y0, x1, y1 = map(float, em.groups())
    return x0, y0, x1 - x0, y1 - y0


def main() -> int:
    import pcbnew

    check = "--check" in sys.argv
    ox, oy, bw, bh = _board_box(PCB.read_text(encoding="utf-8"))
    board = pcbnew.LoadBoard(str(PCB))
    if board is None:
        print("LoadBoard failed", file=sys.stderr)
        return 2

    pads = []
    for fp in board.GetFootprints():
        if str(fp.GetReference()).startswith("H"):
            continue
        for pad in fp.Pads():
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                continue
            sz = pad.GetSize()
            pr = 0.5 * max(pcbnew.ToMM(sz.x), pcbnew.ToMM(sz.y))
            p = pad.GetPosition()
            pads.append((pcbnew.ToMM(p.x), pcbnew.ToMM(p.y), pr, fp.GetReference(), pad.GetNumber()))

    doomed = []
    for t in board.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            p = t.GetPosition()
            vx, vy = pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)
            try:
                vw = t.GetWidth(pcbnew.F_Cu)
            except TypeError:
                vw = t.GetWidth()
            vr = 0.5 * pcbnew.ToMM(vw)
            if (
                vx - vr < ox + EDGE_MM
                or vx + vr > ox + bw - EDGE_MM
                or vy - vr < oy + EDGE_MM
                or vy + vr > oy + bh - EDGE_MM
            ):
                doomed.append(t)
                continue
            for px, py, pr, _ref, _n in pads:
                if (vx - px) ** 2 + (vy - py) ** 2 < (vr + pr + VIA_PAD_GAP_MM) ** 2:
                    doomed.append(t)
                    break
            continue
        if t.Type() != pcbnew.PCB_TRACE_T:
            continue
        hw = 0.5 * pcbnew.ToMM(t.GetWidth())
        x1, y1 = pcbnew.ToMM(t.GetStart().x), pcbnew.ToMM(t.GetStart().y)
        x2, y2 = pcbnew.ToMM(t.GetEnd().x), pcbnew.ToMM(t.GetEnd().y)
        xmin, xmax = min(x1, x2) - hw, max(x1, x2) + hw
        ymin, ymax = min(y1, y2) - hw, max(y1, y2) + hw
        if (
            xmin < ox + EDGE_MM
            or xmax > ox + bw - EDGE_MM
            or ymin < oy + EDGE_MM
            or ymax > oy + bh - EDGE_MM
        ):
            doomed.append(t)

    n_via = sum(1 for t in doomed if t.Type() == pcbnew.PCB_VIA_T)
    n_tr = len(doomed) - n_via
    if check:
        print(
            f"A11/edge check: {n_via} via viol (pad/edge), "
            f"{n_tr} track viol (edge {EDGE_MM} mm) board={bw:.0f}x{bh:.0f}"
        )
        return 1 if doomed else 0
    for t in doomed:
        board.Remove(t)
    pcbnew.SaveBoard(str(PCB), board)
    print(
        f"removed {n_via} via(s) near pads/edge, "
        f"{n_tr} track(s) within {EDGE_MM} mm of edge"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
