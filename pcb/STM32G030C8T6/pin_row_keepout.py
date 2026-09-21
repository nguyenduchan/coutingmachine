"""Keepout strips so traces cannot snake through THT pin rows (sockets / headers).

PCB_REVIEW A7: copper stays clear of foreign holes. User rule on top of that:
do not route *between* adjacent pins of a socket row (cọc đế cắm).
"""
from __future__ import annotations

import math
import re
from collections import defaultdict

from pcb_parse import NetTable, pad_net

# 2.54 mm headers / XH / StepStick rows
PITCH_LO, PITCH_HI = 1.95, 2.70
ALIGN_MM = 0.45
# Alley between two pads in a row, extended past the pad copper so a track
# cannot squeeze through. Pads themselves stay free for fan-out.
ALLEY_PAD_INSET = 0.55  # mm from each pad centre along the row
ALLEY_HALF = 1.15  # mm perpendicular to the row
# Interior of a dual-row socket (between the two pin rows).
DUAL_ROW_LO, DUAL_ROW_HI = 7.0, 18.0
BODY_INSET = 1.15


def _rot(lx: float, ly: float, rot_deg: float) -> tuple[float, float]:
    """Footprint-local → board offset. KiCad CCW on screen, y down."""
    r = math.radians(rot_deg % 360.0)
    c, s = math.cos(r), math.sin(r)
    return lx * c + ly * s, -lx * s + ly * c


def tht_pads_by_ref(pcb_text: str) -> dict[str, list[tuple[float, float]]]:
    table = NetTable(pcb_text)
    out: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for block in re.split(r"(?=\t\(footprint )", pcb_text):
        if "(footprint " not in block[:40] and "\t(footprint " not in block:
            continue
        at = re.search(r"\(at\s+([\d.-]+)\s+([\d.-]+)(?:\s+([\d.-]+))?\)", block)
        if not at:
            continue
        fx, fy = float(at.group(1)), float(at.group(2))
        frot = float(at.group(3) or 0.0)
        rm = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
        ref = rm.group(1) if rm else "?"
        if ref.startswith("H"):
            continue
        starts = [m.start() for m in re.finditer(r"\(pad\s+\"", block)]
        for i, ps in enumerate(starts):
            chunk = block[ps : (starts[i + 1] if i + 1 < len(starts) else len(block))]
            if not re.match(r'\(pad\s+"[^"]*"\s+(?:thru_hole|np_thru_hole)\s+\w+', chunk):
                continue
            am = re.search(r"\(at\s+([\d.-]+)\s+([\d.-]+)(?:\s+[\d.-]+)?\)", chunk)
            if not am:
                continue
            net, _ = pad_net(chunk, table)
            if net <= 0:
                continue
            lx, ly = float(am.group(1)), float(am.group(2))
            dx, dy = _rot(lx, ly, frot)
            out[ref].append((fx + dx, fy + dy))
    return dict(out)


def _cluster_axis(pts: list[tuple[float, float]], axis: int) -> list[list[tuple[float, float]]]:
    """Group points that share X (axis=0) or Y (axis=1)."""
    keyed: dict[int, list[tuple[float, float]]] = defaultdict(list)
    for p in pts:
        keyed[round(p[axis] / ALIGN_MM)].append(p)
    return [v for v in keyed.values() if len(v) >= 2]


def _row_pairs(pts: list[tuple[float, float]], along: int) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    ordered = sorted(pts, key=lambda p: p[along])
    pairs = []
    for a, b in zip(ordered, ordered[1:]):
        d = abs(b[along] - a[along])
        if PITCH_LO <= d <= PITCH_HI:
            pairs.append((a, b))
    return pairs


def pin_row_rects(pcb_text: str) -> list[tuple[float, float, float, float, str]]:
    """Axis-aligned keepout rectangles in KiCad mm (x0,y0,x1,y1,tag)."""
    rects: list[tuple[float, float, float, float, str]] = []
    for ref, pts in tht_pads_by_ref(pcb_text).items():
        if len(pts) < 2:
            continue
        rows: list[list[tuple[float, float]]] = []
        for axis, along in ((1, 0), (0, 1)):  # horiz rows (same Y), vert rows (same X)
            for group in _cluster_axis(pts, axis):
                pairs = _row_pairs(group, along)
                if not pairs:
                    continue
                rows.append(group)
                for a, b in pairs:
                    if along == 0:
                        x0, x1 = min(a[0], b[0]) + ALLEY_PAD_INSET, max(a[0], b[0]) - ALLEY_PAD_INSET
                        ymid = 0.5 * (a[1] + b[1])
                        y0, y1 = ymid - ALLEY_HALF, ymid + ALLEY_HALF
                    else:
                        y0, y1 = min(a[1], b[1]) + ALLEY_PAD_INSET, max(a[1], b[1]) - ALLEY_PAD_INSET
                        xmid = 0.5 * (a[0] + b[0])
                        x0, x1 = xmid - ALLEY_HALF, xmid + ALLEY_HALF
                    if x1 - x0 > 0.15 and y1 - y0 > 0.15:
                        rects.append((x0, y0, x1, y1, f"{ref}_alley"))
        # Dual-row body: two parallel rows a header-spacing apart.
        uniq = []
        for g in rows:
            cx = sum(p[0] for p in g) / len(g)
            cy = sum(p[1] for p in g) / len(g)
            horiz = max(p[0] for p in g) - min(p[0] for p in g) >= max(p[1] for p in g) - min(p[1] for p in g)
            uniq.append((cx, cy, horiz, g))
        for i, (cx1, cy1, h1, g1) in enumerate(uniq):
            for cx2, cy2, h2, g2 in uniq[i + 1 :]:
                if h1 != h2:
                    continue
                gap = abs((cy1 - cy2) if h1 else (cx1 - cx2))
                if not (DUAL_ROW_LO <= gap <= DUAL_ROW_HI):
                    continue
                xs = [p[0] for p in g1 + g2]
                ys = [p[1] for p in g1 + g2]
                if h1:
                    x0, x1 = min(xs) - 0.2, max(xs) + 0.2
                    y0, y1 = min(cy1, cy2) + BODY_INSET, max(cy1, cy2) - BODY_INSET
                else:
                    y0, y1 = min(ys) - 0.2, max(ys) + 0.2
                    x0, x1 = min(cx1, cx2) + BODY_INSET, max(cx1, cx2) - BODY_INSET
                if x1 - x0 > 1.0 and y1 - y0 > 1.0:
                    rects.append((x0, y0, x1, y1, f"{ref}_body"))
    return rects


def dsn_keepout_block(pcb_text: str) -> str:
    """Specctra keepouts in um, Y flipped (KiCad DSN convention)."""
    lines = []
    for i, (x0, y0, x1, y1, tag) in enumerate(pin_row_rects(pcb_text)):
        xa, xb = min(x0, x1) * 1000.0, max(x0, x1) * 1000.0
        # DSN Y = -KiCad Y
        ya, yb = -max(y0, y1) * 1000.0, -min(y0, y1) * 1000.0
        name = re.sub(r"[^A-Za-z0-9_]+", "_", tag)[:24]
        lines.append(
            f'    (keepout "{name}_{i}"\n'
            f"      (rect signal {xa:.0f} {ya:.0f} {xb:.0f} {yb:.0f}))\n"
        )
    return "".join(lines)
