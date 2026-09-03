#!/usr/bin/env python3
"""Mandatory signal routing geometry (PCB_REVIEW.md A5-A7).

- Same layer: signal traces must not cross (interior intersection) other nets.
- Same layer: no colinear copper overlap between different nets.
- Tracks must not pass through or too close to foreign drill holes / pads.
"""
from __future__ import annotations

import math
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from pcb_parse import NetTable, pad_net, seg_net

PCB = Path(__file__).with_name("esp32_baseboard.kicad_pcb")

# Keep in sync with gen_power_carrier.py / KiCad rules
TRACE_CLEARANCE_MM = 0.20
HOLE_EXTRA_MM = 0.25  # beyond drill radius before track copper edge
ENDPOINT_PAD_TOL_MM = 1.0  # fanout from own pad allowed

POWER_NET_NAMES = frozenset(
    {
        "GND",
        "+5V",
        "+3V3",
        "+12V",
        "+12V_RAW",
        "+12V_SNS",
        "/OPTO_VCC_I",
    }
)


@dataclass
class Seg:
    p1: tuple[float, float]
    p2: tuple[float, float]
    width: float
    layer: str
    net: int


@dataclass
class Hole:
    x: float
    y: float
    radius: float  # keepout from center (drill/2 + extras)
    net: int
    ref: str
    pad: str


def is_power_net(name: str) -> bool:
    return name in POWER_NET_NAMES or name.startswith("+")


def parse_pcb(text: str) -> tuple[dict[int, str], list[Seg], list[Hole]]:
    table = NetTable(text)
    segs: list[Seg] = []
    for m in re.finditer(
        r'\(segment\s+\(start\s+([\d.-]+)\s+([\d.-]+)\)\s+\(end\s+([\d.-]+)\s+([\d.-]+)\)'
        r'\s+\(width\s+([\d.-]+)\)\s+\(layer\s+"([^"]+)"\)\s+'
        r'(\(net\s+(?:\d+|"[^"]*")\s*\))',
        text,
    ):
        nid, _ = seg_net(m.group(7), table)
        segs.append(
            Seg(
                (float(m.group(1)), float(m.group(2))),
                (float(m.group(3)), float(m.group(4))),
                float(m.group(5)),
                m.group(6),
                nid,
            )
        )

    holes: list[Hole] = []
    for block in re.split(r"(?=\t\(footprint )", text):
        if "(footprint " not in block[:40] and not block.lstrip().startswith("(footprint"):
            if "\t(footprint " not in block:
                continue
        at = re.search(r"\(at\s+([\d.-]+)\s+([\d.-]+)(?:\s+([\d.-]+))?\)", block)
        if not at:
            continue
        fx, fy = float(at.group(1)), float(at.group(2))
        rot = math.radians(float(at.group(3) or 0))
        c, s = math.cos(rot), math.sin(rot)
        ref_m = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
        ref = ref_m.group(1) if ref_m else "?"
        # One chunk per pad: a pad's (net ...) line comes after its (drill ...),
        # so a single regex anchored on the drill never captures the net and
        # every pad reads as net 0 -- foreign even to its own net.
        pad_starts = [m.start() for m in re.finditer(r'\(pad\s+"', block)]
        for pi, ps in enumerate(pad_starts):
            chunk = block[ps: (pad_starts[pi + 1] if pi + 1 < len(pad_starts) else len(block))]
            hm = re.match(r'\(pad\s+"([^"]*)"\s+(?:thru_hole|np_thru_hole)\s+\w+', chunk)
            if not hm:
                continue
            am = re.search(r"\(at\s+([\d.-]+)\s+([\d.-]+)(?:\s+[\d.-]+)?\)", chunk)
            zm = re.search(r"\(size\s+([\d.-]+)\s+([\d.-]+)\)", chunk)
            dm = re.search(r"\(drill\s+([\d.-]+)\)", chunk)
            if not (am and zm and dm):
                continue
            pname = hm.group(1)
            lx, ly = float(am.group(1)), float(am.group(2))
            sx, sy = float(zm.group(1)), float(zm.group(2))
            drill = float(dm.group(1))
            net, _pn = pad_net(chunk, table)
            # y grows downward, so the sine terms flip (see maze_router._rot_xy)
            wx = fx + lx * c + ly * s
            wy = fy - lx * s + ly * c
            r = max(sx, sy, drill) * 0.5 + HOLE_EXTRA_MM
            holes.append(Hole(wx, wy, r, net, ref, pname))
    # A routing via is a drilled hole too: every other net's copper has to keep
    # the same A7 distance from it as from a pad.
    for vm in re.finditer(
        r"\(via\s*\(at\s+([\d.-]+)\s+([\d.-]+)\)\s*\(size\s+([\d.-]+)\)"
        r"\s*\(drill\s+([\d.-]+)\)([\s\S]*?)\(uuid",
        text,
    ):
        vx, vy = float(vm.group(1)), float(vm.group(2))
        vr = max(float(vm.group(3)), float(vm.group(4))) * 0.5 + HOLE_EXTRA_MM
        vnet, _ = pad_net(vm.group(5), table)
        if not vnet:
            vnet, _ = seg_net(vm.group(5), table)
        holes.append(Hole(vx, vy, vr, vnet, "via", ""))
    return dict(table.by_id), segs, holes


def orient(a, b, c) -> float:
    return (b[1] - a[1]) * (c[0] - b[0]) - (b[0] - a[0]) * (c[1] - b[1])


def on_seg(a, b, c, eps: float = 1e-6) -> bool:
    return (
        min(a[0], b[0]) - eps <= c[0] <= max(a[0], b[0]) + eps
        and min(a[1], b[1]) - eps <= c[1] <= max(a[1], b[1]) + eps
    )


def proper_interior_cross(p1, p2, p3, p4) -> bool:
    """True if segments cross strictly inside both (not at endpoints)."""
    o1, o2 = orient(p1, p2, p3), orient(p1, p2, p4)
    o3, o4 = orient(p3, p4, p1), orient(p3, p4, p2)
    if o1 == 0 and on_seg(p1, p2, p3):
        return False
    if o2 == 0 and on_seg(p1, p2, p4):
        return False
    if o3 == 0 and on_seg(p3, p4, p1):
        return False
    if o4 == 0 and on_seg(p3, p4, p2):
        return False
    return (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0)


def overlap_1d(a0, a1, b0, b1, eps: float = 0.05) -> bool:
    lo = max(min(a0, a1), min(b0, b1))
    hi = min(max(a0, a1), max(b0, b1))
    return hi - lo > eps


def colinear_overlap(a: Seg, b: Seg) -> bool:
    need_sep = (a.width + b.width) * 0.5 + TRACE_CLEARANCE_MM
    # horizontal
    if abs(a.p1[1] - a.p2[1]) < 1e-4 and abs(b.p1[1] - b.p2[1]) < 1e-4:
        if abs(a.p1[1] - b.p1[1]) > need_sep:
            return False
        return overlap_1d(a.p1[0], a.p2[0], b.p1[0], b.p2[0])
    # vertical
    if abs(a.p1[0] - a.p2[0]) < 1e-4 and abs(b.p1[0] - b.p2[0]) < 1e-4:
        if abs(a.p1[0] - b.p1[0]) > need_sep:
            return False
        return overlap_1d(a.p1[1], a.p2[1], b.p1[1], b.p2[1])
    return False


def dist_point_seg(px, py, a, b) -> tuple[float, float]:
    dx, dy = b[0] - a[0], b[1] - a[1]
    ln2 = dx * dx + dy * dy or 1e-18
    t = max(0.0, min(1.0, ((px - a[0]) * dx + (py - a[1]) * dy) / ln2))
    qx, qy = a[0] + t * dx, a[1] + t * dy
    return math.hypot(px - qx, py - qy), t


def is_signal(net: int, net_names: dict[int, str]) -> bool:
    """A5/A6 apply to every net, not just the thin ones.

    Power nets used to be exempt, on the idea that they may be routed loosely.
    But two *different* power nets crossing on one layer is a short like any
    other, and the exemption was hiding 25 of them (GND x +12V, GND x +3V3,
    +5V x GND) that KiCad's DRC reported straight away.
    """
    return True


def main() -> int:
    text = PCB.read_text(encoding="utf-8")
    net_names, segs, holes = parse_pcb(text)

    crosses: list[tuple[Seg, Seg]] = []
    colinear: list[tuple[Seg, Seg]] = []
    hole_hits: list[tuple[float, Seg, Hole]] = []

    for i, a in enumerate(segs):
        for b in segs[i + 1 :]:
            if a.layer != b.layer or a.net == b.net:
                continue
            if not (is_signal(a.net, net_names) and is_signal(b.net, net_names)):
                continue
            if proper_interior_cross(a.p1, a.p2, b.p1, b.p2):
                crosses.append((a, b))
            elif colinear_overlap(a, b):
                colinear.append((a, b))

    for seg in segs:
        for hole in holes:
            if hole.net == seg.net and hole.net != 0:
                continue
            for pt in (seg.p1, seg.p2):
                if math.hypot(pt[0] - hole.x, pt[1] - hole.y) < hole.radius + ENDPOINT_PAD_TOL_MM:
                    break
            else:
                d, t = dist_point_seg(hole.x, hole.y, seg.p1, seg.p2)
                need = hole.radius + seg.width * 0.5 + TRACE_CLEARANCE_MM
                if d < need and 0.02 < t < 0.98:
                    hole_hits.append((need - d, seg, hole))

    hole_hits.sort(key=lambda x: x[0], reverse=True)

    print("=== Signal routing geometry (mandatory) ===")
    print(f"segments: {len(segs)}  drill keepouts: {len(holes)}")
    print(f"clearance rule: {TRACE_CLEARANCE_MM} mm copper-to-copper")
    print()

    print(f"A5 interior crossings (signal, same layer, diff net): {len(crosses)}")
    if crosses:
        pairs: dict[tuple[str, str], int] = defaultdict(int)
        for a, b in crosses:
            n1, n2 = net_names.get(a.net, "?"), net_names.get(b.net, "?")
            pairs[tuple(sorted((n1, n2)))] += 1
        for (n1, n2), c in sorted(pairs.items(), key=lambda x: -x[1])[:12]:
            print(f"  {c:3d}  {n1} x {n2}")
        for a, b in crosses[:8]:
            mid = ((a.p1[0] + a.p2[0]) / 2, (a.p1[1] + a.p2[1]) / 2)
            print(
                f"  sample {net_names.get(a.net)} x {net_names.get(b.net)} "
                f"@({mid[0]:.1f},{mid[1]:.1f}) {a.layer}"
            )
    else:
        print("  PASS")

    print()
    print(f"A6 colinear overlap (signal, same layer, diff net): {len(colinear)}")
    if colinear:
        for a, b in colinear[:8]:
            print(
                f"  sample {net_names.get(a.net)} | {net_names.get(b.net)} {a.layer}"
            )
    else:
        print("  PASS")

    print()
    print(f"A7 through/near foreign hole (all nets): {len(hole_hits)}")
    if hole_hits:
        by_ref: dict[str, int] = defaultdict(int)
        for _, _, h in hole_hits:
            by_ref[h.ref] += 1
        for ref, c in sorted(by_ref.items(), key=lambda x: -x[1])[:12]:
            print(f"  {c:4d}  {ref}")
        for pen, seg, hole in hole_hits[:8]:
            print(
                f"  pen={pen:.2f}  {net_names.get(seg.net, str(seg.net))} "
                f"near {hole.ref}/{hole.pad} @({hole.x:.1f},{hole.y:.1f}) {seg.layer}"
            )
    else:
        print("  PASS")

    ok = not crosses and not colinear and not hole_hits
    print()
    print("OVERALL:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
