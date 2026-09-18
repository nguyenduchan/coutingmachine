#!/usr/bin/env python3
"""Remove vias <1 mm from component pads and copper <2 mm from Edge.Cuts."""
from __future__ import annotations

import sys
from pathlib import Path

PCB = Path(__file__).with_name("esp32_baseboard.kicad_pcb")
OX, OY, BW, BH = 50.0, 50.0, 180.0, 120.0
VIA_PAD_GAP_MM = 1.0
EDGE_MM = 2.0


def main() -> int:
    import pcbnew

    check = "--check" in sys.argv
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
                vx - vr < OX + EDGE_MM
                or vx + vr > OX + BW - EDGE_MM
                or vy - vr < OY + EDGE_MM
                or vy + vr > OY + BH - EDGE_MM
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
            xmin < OX + EDGE_MM
            or xmax > OX + BW - EDGE_MM
            or ymin < OY + EDGE_MM
            or ymax > OY + BH - EDGE_MM
        ):
            doomed.append(t)

    n_via = sum(1 for t in doomed if t.Type() == pcbnew.PCB_VIA_T)
    n_tr = len(doomed) - n_via
    if check:
        print(f"A11/A12 check: {n_via} via viol (pad/edge), {n_tr} track viol (edge {EDGE_MM} mm)")
        return 1 if doomed else 0
    for t in doomed:
        board.Remove(t)
    pcbnew.SaveBoard(str(PCB), board)
    print(f"removed {n_via} via(s) near pads/edge, {n_tr} track(s) within {EDGE_MM} mm of edge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
