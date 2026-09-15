#!/usr/bin/env python3
"""Full PCB placement engine for the compact carrier.

DIN-rail layout guide (N/S edge jacks, W/E = clip sides):
  SOUTH (bottom): 24V power + motor jacks + drivers / buck
  MID:            optocoupler isolation wall
  NORTH (top):    sensors + keypad + display + MCU 3V3

Pipeline: min-cut → quadratic → force → GA → SA → legalize.
Locked: inlet chain, edge jacks, U1, USB, TMC near MOT jacks.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Callable, Sequence


WEAK_NETS = frozenset({
    "GND", "+24V", "+24V_RAW", "+24V_PRE", "+24V_SNS", "+24V_SNS_PRE",
    "+24V_MOT", "+24V_MOT2", "+5V", "+3V3",
})

RAIL_24_NETS = frozenset({
    "+24V", "+24V_RAW", "+24V_PRE", "+24V_SNS", "+24V_SNS_PRE", "+24V_MOT", "+24V_MOT2",
})
POST_FUSE_NETS = frozenset({
    "+24V", "+24V_SNS", "+24V_SNS_PRE", "+24V_MOT", "+24V_MOT2",
})
PRE_FUSE_REFS = frozenset({"J1", "D3", "F1"})

# Soft prefs for non-locked parts (edge jacks are hard-pinned)
EDGE_PREF = {
    "SW_BOOT": ("N", 4.0),
    "SW_NRST": ("N", 4.0),
    "J_DBG": ("N", 6.5),
    "U3": ("S", 7.5),
    "U4": ("S", 7.5),
    "U_PWR": ("S", 6.0),
    "U_VIB": ("S", 5.5),
    "PTC_MOT": ("S", 5.0),
    "PTC_MOT2": ("S", 5.0),
    "PTC_SNS": ("S", 4.0),
}

# Y fractions: N=top(low Y) 3V3 | mid OPTO | S=bottom(high Y) 24V
REGION_BOX = {
    "MCU": (0.45, 0.04, 0.92, 0.38),
    "HMI": (0.04, 0.04, 0.55, 0.36),
    "OPTO": (0.04, 0.32, 0.55, 0.55),
    "POWER": (0.04, 0.50, 0.45, 0.92),
    "TMC": (0.30, 0.48, 0.78, 0.92),
    "PWR": (0.70, 0.48, 0.96, 0.88),
}

REGION_ORDER = ("POWER", "TMC", "OPTO", "PWR", "MCU", "HMI")

LOCKED_REFS = frozenset({
    "U1", "J1", "J_USB", "D3", "F1",
    "J_MOT1", "J_MOT2", "U3", "U4",
    "J14", "J15", "J_IN2", "J_IN3", "J_KEY", "J_DISP",
    "J_DBG",
})

# External field connectors — may sit on N/S board edges.
# Everything else must keep ≥ INNER courtyard clearance from Edge.Cuts.
EDGE_JACK_REFS = frozenset({
    "J1", "J_MOT1", "J_MOT2",
    "J14", "J15", "J_IN2", "J_IN3",
    "J_KEY", "J_DISP", "J_USB", "J_DBG",
})


@dataclass
class PlaceCfg:
    board_w: float
    board_h: float
    ox: float
    oy: float
    margin: float  # non-jack ≥ this from Edge.Cuts
    jack_margin: float  # field jacks may be closer
    gap: float
    ant_tip: float
    ant_clear: float
    ant_half_w: float
    courtyard_size: Callable[[str], tuple[float, float]]


def _aabb(p) -> tuple[float, float, float, float]:
    return (p.x - p.w / 2, p.y - p.h / 2, p.x + p.w / 2, p.y + p.h / 2)


def _rects_overlap(a, b) -> bool:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return not (ax1 <= bx0 or bx1 <= ax0 or ay1 <= by0 or by1 <= ay0)


def pack_parts(parts: list, cfg: PlaceCfg, seed: int = 42) -> dict:
    rng = random.Random(seed)
    # Inner keep-in for non-jacks (≥ margin from Edge.Cuts)
    ix0, iy0 = cfg.ox + cfg.margin, cfg.oy + cfg.margin
    ix1, iy1 = cfg.ox + cfg.board_w - cfg.margin, cfg.oy + cfg.board_h - cfg.margin
    # Field jacks may hug N/S edges
    jx0, jy0 = cfg.ox + cfg.jack_margin, cfg.oy + cfg.jack_margin
    jx1, jy1 = cfg.ox + cfg.board_w - cfg.jack_margin, cfg.oy + cfg.board_h - cfg.jack_margin
    by_ref = {p.ref: p for p in parts}

    hole = max(cfg.margin + 0.5, 4.5)
    by_ref["H1"].x, by_ref["H1"].y = cfg.ox + hole, cfg.oy + hole
    by_ref["H2"].x, by_ref["H2"].y = cfg.ox + cfg.board_w - hole, cfg.oy + hole
    by_ref["H3"].x, by_ref["H3"].y = cfg.ox + hole, cfg.oy + cfg.board_h - hole
    by_ref["H4"].x, by_ref["H4"].y = cfg.ox + cfg.board_w - hole, cfg.oy + cfg.board_h - hole

    movable = [p for p in parts if not p.board_only]
    u1 = by_ref["U1"]
    others = []

    def set_rot(p, rot: float) -> None:
        """Apply rotation; update courtyard w/h. Locked edge parts keep guide angles."""
        if p is u1:
            rot = 0.0
        elif p.ref == "J1":
            rot = 0.0  # south edge, pads || edge
        elif p.ref == "J_USB":
            rot = 180.0  # mouth north outward
        elif p.ref == "D3":
            rot = 0.0
        elif p.ref == "F1":
            rot = 0.0  # pad1 west PRE, pad2 east +24V
        elif p.ref in (
            "J_MOT1", "J_MOT2", "J14", "J15", "J_IN2", "J_IN3",
            "J_KEY", "J_DISP", "J_DBG",
        ):
            # Native pad row is local +Y → rot 90/270 = pin row || N/S edge (ngang)
            rot = 90.0
        elif p.ref in ("U3", "U4"):
            rot = 0.0
        elif p.ref in ("SW_BOOT", "SW_NRST"):
            rot = 0.0
        rot = float(int(rot) % 360)
        if rot not in (0.0, 90.0, 180.0, 270.0):
            rot = 0.0
        p.rot = rot
        uw, uh = cfg.courtyard_size(p.fp)
        if rot in (90.0, 270.0):
            p.w, p.h = uh, uw
        else:
            p.w, p.h = uw, uh

    def clamp(p) -> None:
        if p.ref in EDGE_JACK_REFS:
            x0, y0, x1, y1 = jx0, jy0, jx1, jy1
        else:
            x0, y0, x1, y1 = ix0, iy0, ix1, iy1
        p.x = min(max(p.x, x0 + p.w / 2), x1 - p.w / 2)
        p.y = min(max(p.y, y0 + p.h / 2), y1 - p.h / 2)

    def overlaps(a, b) -> bool:
        return (
            abs(a.x - b.x) < (a.w + b.w) / 2 + cfg.gap
            and abs(a.y - b.y) < (a.h + b.h) / 2 + cfg.gap
        )

    def overlap_depth(a, b) -> float:
        ox = (a.w + b.w) / 2 + cfg.gap - abs(a.x - b.x)
        oy = (a.h + b.h) / 2 + cfg.gap - abs(a.y - b.y)
        if ox <= 0 or oy <= 0:
            return 0.0
        return min(ox, oy)

    def separate_pair(a, b) -> bool:
        """Push apart so AABB + gap no longer overlap. Returns True if moved."""
        d = overlap_depth(a, b)
        if d <= 0:
            return False
        dx, dy = b.x - a.x, b.y - a.y
        if abs(dx) < 1e-9 and abs(dy) < 1e-9:
            dx, dy = 1.0, 0.0
        min_dx = (a.w + b.w) / 2 + cfg.gap
        min_dy = (a.h + b.h) / 2 + cfg.gap
        ox = min_dx - abs(dx)
        oy = min_dy - abs(dy)
        eps = 0.05
        # Never move locked edge/inlet parts — always shove the other body
        a_fixed = a.ref in LOCKED_REFS
        b_fixed = b.ref in LOCKED_REFS

        def _push_x(target, sgn, push):
            target.x += push * sgn

        def _push_y(target, sgn, push):
            target.y += push * sgn

        if ox < oy:
            push = ox + eps
            sgn = 1.0 if dx >= 0 else -1.0
            if a_fixed and not b_fixed:
                _push_x(b, sgn, push)
            elif b_fixed and not a_fixed:
                _push_x(a, -sgn, push)
            elif is_locked(a) and not is_locked(b):
                _push_x(b, sgn, push)
            elif is_locked(b) and not is_locked(a):
                _push_x(a, -sgn, push)
            else:
                _push_x(a, -sgn, 0.5 * push)
                _push_x(b, sgn, 0.5 * push)
        else:
            push = oy + eps
            sgn = 1.0 if dy >= 0 else -1.0
            if a_fixed and not b_fixed:
                _push_y(b, sgn, push)
            elif b_fixed and not a_fixed:
                _push_y(a, -sgn, push)
            elif is_locked(a) and not is_locked(b):
                _push_y(b, sgn, push)
            elif is_locked(b) and not is_locked(a):
                _push_y(a, -sgn, push)
            else:
                _push_y(a, -sgn, 0.5 * push)
                _push_y(b, sgn, 0.5 * push)
        return True

    def antenna_ko():
        """RF keepout (disabled when ant_half_w==0 for STM32)."""
        tip_x = u1.x
        tip_y = u1.y - cfg.ant_tip
        return (
            tip_x - cfg.ant_half_w,
            iy0 - 0.5,
            tip_x + cfg.ant_half_w,
            tip_y,
        )

    def in_keepout(p) -> float:
        """Overlap depth vs keepout expanded by gap (parts must clear, not kiss)."""
        if p is u1 or cfg.ant_half_w <= 0.0:
            return 0.0
        kx0, ky0, kx1, ky1 = antenna_ko()
        g = cfg.gap
        kx0, ky0, kx1, ky1 = kx0 - g, ky0 - g, kx1 + g, ky1 + g
        px0, py0, px1, py1 = _aabb(p)
        if not _rects_overlap((px0, py0, px1, py1), (kx0, ky0, kx1, ky1)):
            return 0.0
        ox = min(px1, kx1) - max(px0, kx0)
        oy = min(py1, ky1) - max(py0, ky0)
        return max(0.0, min(ox, oy))

    def eject_keepout(p) -> None:
        """Hard push south (and E/W if needed) clear of antenna keepout + gap."""
        if p is u1 or p is j1:
            return
        d = in_keepout(p)
        if d <= 0:
            return
        kx0, _ky0, kx1, ky1 = antenna_ko()
        clear = cfg.gap + 1.0
        p.y = ky1 + p.h / 2 + clear
        clamp(p)
        if in_keepout(p) > 0:
            if p.x >= u1.x:
                p.x = kx1 + p.w / 2 + clear
            else:
                p.x = kx0 - p.w / 2 - clear
            clamp(p)
            p.y = max(p.y, ky1 + p.h / 2 + clear)
            clamp(p)

    def pin_j1() -> None:
        """24V terminal: south-west corner on field-jack margin."""
        set_rot(j1, 0.0)
        j1.y = jy1 - j1.h / 2
        j1.x = jx0 + j1.w / 2 + 1.0
        clamp(j1)

    def pin_j_usb() -> None:
        """USB Micro-B: flush north; final X set in pin_edge_jacks."""
        set_rot(usb, 180.0)
        usb.y = jy0 + usb.h / 2
        usb.x = cfg.ox + 0.88 * cfg.board_w
        clamp(usb)

    def pin_inlet_chain() -> None:
        """J1 on south edge; D3/F1 inland (≥4 mm from Edge.Cuts)."""
        pin_j1()
        chain_gap = cfg.gap + 0.5
        set_rot(d3, 0.0)
        d3.x = j1.x + j1.w / 2 + chain_gap + d3.w / 2
        d3.y = min(j1.y - j1.h / 2 - chain_gap - d3.h / 2, iy1 - d3.h / 2)
        clamp(d3)
        set_rot(f1, 0.0)
        f1.y = iy1 - f1.h / 2
        f1.x = max(d3.x + d3.w / 2, j1.x + j1.w / 2) + chain_gap + f1.w / 2
        clamp(f1)

    def fuse_out_x() -> float:
        """World X of F1 pad2 (+24V) with rot=0 (local +11.25 → +X)."""
        return f1.x + 11.25

    def fuse_out_y() -> float:
        """North face of fuse — post-fuse loads stay clear of inlet."""
        return f1.y - f1.h / 2

    def is_post_fuse_load(p) -> bool:
        if p.ref in PRE_FUSE_REFS:
            return False
        return any(n in POST_FUSE_NETS for n in (p.pad_nets or {}).values())

    def enforce_post_fuse() -> None:
        """Keep +24V loads out of pre-fuse pocket (west of F1 on south band)."""
        xmin = fuse_out_x() + cfg.gap
        for p in others:
            if not is_post_fuse_load(p):
                continue
            if p.x + p.w / 2 < xmin and p.y > fuse_out_y() - 2.0:
                p.x = xmin + p.w / 2
            clamp(p)
            eject_keepout(p)

    def pin_edge_jacks() -> None:
        """All field connectors on N or S only; pin rows || edge (rot 90)."""
        edge_gap = cfg.gap + 0.75
        # South: power + motors only (Mot pad-row along edge)
        u3w = cfg.courtyard_size("TMC2209_StepStick")[0]
        f1p = by_ref["F1"]
        # Clear full F1 body (not just pad2) so U3 under Mot cannot kiss fuse
        x = f1p.x + f1p.w / 2 + edge_gap
        for ref in ("J_MOT1", "J_MOT2"):
            p = by_ref[ref]
            set_rot(p, 90.0)
            p.y = jy1 - p.h / 2
            mot_pitch = max(p.w, u3w) + cfg.gap + 1.0
            p.x = x + max(p.w, u3w) / 2
            clamp(p)
            x = p.x - max(p.w, u3w) / 2 + mot_pitch
        for uref, jref in (("U3", "J_MOT1"), ("U4", "J_MOT2")):
            u = by_ref[uref]
            j = by_ref[jref]
            set_rot(u, 0.0)
            u.x = j.x
            u.y = j.y - j.h / 2 - edge_gap - u.h / 2
            clamp(u)
        # North: tight cluster SNS→KEY→DISP→DBG→USB (ngang)
        # cfg.gap+0.15 avoids float "exact-gap" false overlaps in placer
        n_gap = cfg.gap + 0.15
        x = jx0 + 0.5
        north_order = ("J14", "J_IN2", "J_KEY", "J_DISP", "J_DBG", "J_USB")
        for ref in north_order:
            p = by_ref[ref]
            set_rot(p, 180.0 if ref == "J_USB" else 90.0)
            p.y = jy0 + p.h / 2
            p.x = x + p.w / 2
            clamp(p)
            x = p.x + p.w / 2 + n_gap
        # Alternates inland, tight under parents
        for child, parent in (("J15", "J14"), ("J_IN3", "J_IN2")):
            c, p = by_ref[child], by_ref[parent]
            set_rot(c, 90.0)
            c.x = p.x
            c.y = p.y + p.h / 2 + n_gap + c.h / 2
            clamp(c)
        # SW_BOOT / SW_NRST: seeded once elsewhere (movable); do not re-pin here

    def pin_locked_edges() -> None:
        pin_inlet_chain()
        pin_j_usb()
        pin_edge_jacks()
        enforce_post_fuse()

    # --- pin U1 below north jack strip (MCU / 3V3), east half ---
    set_rot(u1, 0.0)
    u1.x = cfg.ox + 0.62 * cfg.board_w
    u1.y = cfg.oy + 0.36 * cfg.board_h
    clamp(u1)

    j1 = by_ref["J1"]
    d3 = by_ref["D3"]
    f1 = by_ref["F1"]
    usb = by_ref["J_USB"]
    locked_refs = set(LOCKED_REFS)
    others = [p for p in movable if p.ref not in locked_refs]

    def is_locked(p) -> bool:
        return p.ref in locked_refs

    pin_locked_edges()

    # Seed tact switches inland near USB (movable)
    for i, sref in enumerate(("SW_BOOT", "SW_NRST")):
        sw = by_ref[sref]
        set_rot(sw, 0.0)
        sw.x = usb.x - (i + 0.5) * (sw.w + cfg.gap + 0.75)
        sw.y = usb.y + usb.h / 2 + cfg.gap + 8.0 + sw.h / 2
        clamp(sw)

    # --- net graph ---
    def net_weight(net: str) -> float:
        if not net:
            return 0.0
        if net in WEAK_NETS:
            return 0.05
        return 1.0

    # adjacency[ref][ref2] = weight
    adj: dict[str, dict[str, float]] = {p.ref: {} for p in movable}

    net_to_parts: dict[str, list] = {}
    for p in movable:
        for net in set(p.pad_nets.values()):
            w = net_weight(net)
            if w <= 0:
                continue
            net_to_parts.setdefault(net, []).append(p)

    for net, members in net_to_parts.items():
        w = net_weight(net)
        if len(members) < 2:
            continue
        if len(members) <= 6:
            pairs = [
                (members[i], members[j])
                for i in range(len(members))
                for j in range(i + 1, len(members))
            ]
        else:
            hub = members[0]
            pairs = [(hub, q) for q in members[1:]]
        for a, b in pairs:
            adj[a.ref][b.ref] = adj[a.ref].get(b.ref, 0.0) + w
            adj[b.ref][a.ref] = adj[b.ref].get(a.ref, 0.0) + w

    edge_list = []
    seen_e: set[tuple[str, str]] = set()
    for a in movable:
        for bref, w in adj[a.ref].items():
            ra, rb = (a.ref, bref) if a.ref < bref else (bref, a.ref)
            if (ra, rb) in seen_e:
                continue
            seen_e.add((ra, rb))
            edge_list.append((a, by_ref[bref], w))

    def region_box(name: str) -> tuple[float, float, float, float]:
        x0, y0, x1, y1 = REGION_BOX[name]
        return (
            cfg.ox + x0 * cfg.board_w,
            cfg.oy + y0 * cfg.board_h,
            cfg.ox + x1 * cfg.board_w,
            cfg.oy + y1 * cfg.board_h,
        )

    def uses_24v(p) -> bool:
        return any(n in RAIL_24_NETS for n in (p.pad_nets or {}).values())

    # =====================================================================
    # 1) Min-cut / FM partition refine (seed = schematic cluster)
    # =====================================================================
    part_of = {p.ref: p.cluster if p.cluster in REGION_BOX else "HMI" for p in others}
    # Keep 24V rail parts in POWER/TMC/OPTO (never migrate to HMI via FM)
    for p in others:
        if uses_24v(p) and p.cluster in ("POWER", "TMC", "OPTO"):
            part_of[p.ref] = p.cluster

    def cut_cost() -> float:
        c = 0.0
        for a, b, w in edge_list:
            if a is u1 or b is u1:
                # edges to U1: prefer MCU partition
                other = b if a is u1 else a
                if other is u1:
                    continue
                if part_of.get(other.ref, "MCU") != "MCU":
                    c += w * 0.5
                continue
            if part_of.get(a.ref) != part_of.get(b.ref):
                c += w
        return c

    def fm_refine(passes: int = 4) -> None:
        regions = list(REGION_ORDER)
        for _ in range(passes):
            improved = False
            order = others[:]
            rng.shuffle(order)
            for p in order:
                if uses_24v(p):
                    continue  # freeze rail cluster
                cur = part_of[p.ref]
                best_r, best_d = cur, 0.0
                base = cut_cost()
                for r in regions:
                    if r == cur:
                        continue
                    part_of[p.ref] = r
                    d = base - cut_cost()
                    if d > best_d:
                        best_d, best_r = d, r
                part_of[p.ref] = best_r if best_d > 0 else cur
                if best_d > 0:
                    improved = True
            if not improved:
                break

    fm_refine()

    # seed place: POWER/TMC/OPTO start under J1; others in their boxes
    for rname in REGION_ORDER:
        box = region_box(rname)
        group = sorted(
            [p for p in others if part_of[p.ref] == rname],
            key=lambda q: q.w * q.h,
            reverse=True,
        )
        x0, y0, x1, y1 = box
        if rname in ("POWER", "TMC", "PWR"):
            # pack in south 24V band, east of fuse
            x = max(x0 + 1.0, fuse_out_x() + cfg.gap)
            y = max(y0 + 1.0, fuse_out_y() + cfg.gap)
        elif rname == "OPTO":
            x, y = x0 + 1.0, y0 + 1.0
        else:
            x, y = x0 + 1.0, y0 + 1.0
        row_h = 0.0
        for p in group:
            if x + p.w / 2 > x1 - 1.0:
                x = (
                    max(x0 + 1.0, fuse_out_x() + cfg.gap)
                    if rname in ("POWER", "TMC", "PWR")
                    else x0 + 1.0
                )
                y += row_h + cfg.gap
                row_h = 0.0
            p.x = min(max(x + p.w / 2, x0 + p.w / 2), x1 - p.w / 2)
            p.y = min(max(y + p.h / 2, y0 + p.h / 2), y1 - p.h / 2)
            if is_post_fuse_load(p):
                xmin = fuse_out_x() + cfg.gap
                if p.x + p.w / 2 < xmin and p.y > fuse_out_y() - 2.0:
                    p.x = xmin + p.w / 2
            clamp(p)
            eject_keepout(p)
            x += p.w + cfg.gap
            row_h = max(row_h, p.h)

    # =====================================================================
    # 2) Analytical / quadratic wirelength (Jacobi on spring equilibrium)
    # =====================================================================
    # Fixed: U1. Soft anchors: edge-pref parts pulled toward edge targets.
    def soft_anchor(p) -> tuple[float, float, float] | None:
        """Return (tx, ty, weight) or None."""
        pref = EDGE_PREF.get(p.ref)
        if not pref:
            # partition center soft anchor
            box = region_box(part_of.get(p.ref, "MCU"))
            return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2, 0.15)
        side, s = pref
        kx0, ky0, kx1, ky1 = antenna_ko()
        if side == "N":
            return (p.x, iy0 + p.h / 2, 0.4 * s / 10)
        if side == "S":
            return (p.x, iy1 - p.h / 2, 0.45 * s / 10)
        if side == "W":
            return (ix0 + p.w / 2, p.y, 0.3 * s / 10)
        if side == "E":
            return (ix1 - p.w / 2, p.y, 0.4 * s / 10)
        return None

    for _ in range(40):
        new_xy: dict[str, tuple[float, float]] = {}
        for p in others:
            num_x = num_y = den = 0.0
            for qref, w in adj[p.ref].items():
                q = by_ref[qref]
                num_x += w * q.x
                num_y += w * q.y
                den += w
            anc = soft_anchor(p)
            if anc:
                tx, ty, aw = anc
                num_x += aw * tx
                num_y += aw * ty
                den += aw
            if den < 1e-9:
                new_xy[p.ref] = (p.x, p.y)
            else:
                # damp toward solution
                nx, ny = num_x / den, num_y / den
                new_xy[p.ref] = (0.65 * nx + 0.35 * p.x, 0.65 * ny + 0.35 * p.y)
        for p in others:
            p.x, p.y = new_xy[p.ref]
            clamp(p)
            eject_keepout(p)
        pin_locked_edges()

    # =====================================================================
    # 3) Force-directed
    # =====================================================================
    def cluster_pull(p) -> tuple[float, float]:
        box = region_box(part_of.get(p.ref, "MCU"))
        x0, y0, x1, y1 = box
        fx = fy = 0.0
        if p.x < x0 + p.w / 2:
            fx += (x0 + p.w / 2 - p.x) * 0.12
        elif p.x > x1 - p.w / 2:
            fx += (x1 - p.w / 2 - p.x) * 0.12
        if p.y < y0 + p.h / 2:
            fy += (y0 + p.h / 2 - p.y) * 0.12
        elif p.y > y1 - p.h / 2:
            fy += (y1 - p.h / 2 - p.y) * 0.12
        return fx, fy

    for _ in range(30):
        force = {id(p): [0.0, 0.0] for p in movable}
        for a, b, w in edge_list:
            dx, dy = b.x - a.x, b.y - a.y
            dist = math.hypot(dx, dy) + 1e-6
            ideal = 0.55 * (math.hypot(a.w, a.h) + math.hypot(b.w, b.h)) + 3.0
            f = 0.08 * w * (dist - ideal)
            ux, uy = dx / dist, dy / dist
            if not is_locked(a):
                force[id(a)][0] += f * ux
                force[id(a)][1] += f * uy
            if not is_locked(b):
                force[id(b)][0] -= f * ux
                force[id(b)][1] -= f * uy
        for i, a in enumerate(movable):
            for b in movable[i + 1 :]:
                d = overlap_depth(a, b)
                if d <= 0:
                    continue
                dx, dy = b.x - a.x, b.y - a.y
                if abs(dx) < 1e-9 and abs(dy) < 1e-9:
                    dx, dy = rng.uniform(-1, 1), rng.uniform(-1, 1)
                dist = math.hypot(dx, dy) + 1e-6
                push = 0.55 * d + 0.3
                ux, uy = dx / dist, dy / dist
                area_a = max(a.w * a.h, 1)
                area_b = max(b.w * b.h, 1)
                wa = area_b / (area_a + area_b)
                if not is_locked(a):
                    force[id(a)][0] -= push * ux * (1 - wa)
                    force[id(a)][1] -= push * uy * (1 - wa)
                if not is_locked(b):
                    force[id(b)][0] += push * ux * wa
                    force[id(b)][1] += push * uy * wa
        for p in others:
            fx, fy = force[id(p)]
            cx, cy = cluster_pull(p)
            kd = in_keepout(p)
            if kd > 0:
                fx += 1.2 * kd + 0.8
            # Pull post-fuse 24V loads east of inlet (beside fuse preferred)
            if is_post_fuse_load(p):
                tx = fuse_out_x() + 14.0
                ty = iy1 - 18.0
                fx += 0.12 * (tx - p.x)
                fy += 0.10 * (ty - p.y)
            p.x += fx + cx
            p.y += fy + cy
            clamp(p)
            eject_keepout(p)
        pin_locked_edges()

    # =====================================================================
    # Cost (shared by GA + SA)
    # =====================================================================
    def wirelength() -> float:
        return sum(w * (abs(a.x - b.x) + abs(a.y - b.y)) for a, b, w in edge_list)

    def overlap_cost() -> float:
        s = 0.0
        for i, a in enumerate(movable):
            for b in movable[i + 1 :]:
                d = overlap_depth(a, b)
                if d > 0:
                    s += d * d
        return s

    def keepout_cost() -> float:
        return sum(in_keepout(p) ** 2 for p in others) * 500.0

    def j1_edge_cost() -> float:
        target_y = jy1 - j1.h / 2
        target_x = jx0 + j1.w / 2 + 1.0
        return (
            40.0 * abs(j1.y - target_y)
            + 30.0 * abs(j1.x - target_x)
            + (0.0 if abs(j1.rot) < 0.1 else 100.0)
        )

    def partition_cost() -> float:
        s = 0.0
        for p in others:
            x0, y0, x1, y1 = region_box(part_of.get(p.ref, "MCU"))
            if p.x < x0:
                s += (x0 - p.x) ** 2
            elif p.x > x1:
                s += (p.x - x1) ** 2
            if p.y < y0:
                s += (y0 - p.y) ** 2
            elif p.y > y1:
                s += (p.y - y1) ** 2
        return s

    def edge_cost() -> float:
        s = 0.0
        for ref, (side, w) in EDGE_PREF.items():
            p = by_ref.get(ref)
            if not p or p.board_only:
                continue
            if side == "N":
                s += w * abs(p.y - (iy0 + p.h / 2))
            elif side == "S":
                s += w * abs(p.y - (iy1 - p.h / 2))
            elif side == "W":
                s += w * abs(p.x - (ix0 + p.w / 2))
            elif side == "E":
                s += w * abs(p.x - (ix1 - p.w / 2))
        return s

    def rail_24_cost() -> float:
        """Penalize post-fuse loads inside pre-fuse south-west pocket."""
        s = 0.0
        xmin = fuse_out_x() + cfg.gap
        tx = xmin + 12.0
        ty = iy1 - 20.0
        for p in others:
            if not is_post_fuse_load(p):
                continue
            if p.x + p.w / 2 < xmin and p.y > fuse_out_y() - 2.0:
                s += 100.0 * (xmin - (p.x + p.w / 2)) ** 2
            s += abs(p.x - tx) + 0.4 * abs(p.y - ty)
        return s

    def total_cost() -> float:
        return (
            200.0 * overlap_cost()
            + 1.0 * wirelength()
            + 0.35 * partition_cost()
            + 0.8 * edge_cost()
            + 5.0 * rail_24_cost()
            + keepout_cost()
            + j1_edge_cost()
        )

    def snapshot() -> list[tuple[float, float, float]]:
        return [(p.x, p.y, p.rot) for p in others]

    def restore(state: Sequence[tuple[float, float, float]]) -> None:
        for p, (x, y, r) in zip(others, state):
            set_rot(p, r)
            p.x, p.y = x, y
            clamp(p)
            eject_keepout(p)
        pin_locked_edges()

    # =====================================================================
    # 4) Genetic / evolutionary
    # =====================================================================
    pop_n, gens = 6, 5
    population: list[tuple[list[tuple[float, float, float]], float]] = []
    base = snapshot()
    population.append((base, total_cost()))
    for _ in range(pop_n - 1):
        restore(base)
        for p in others:
            p.x += rng.uniform(-6, 6)
            p.y += rng.uniform(-6, 6)
            if rng.random() < 0.25:
                set_rot(p, rng.choice([0.0, 90.0, 180.0, 270.0]))
            clamp(p)
            eject_keepout(p)
        population.append((snapshot(), total_cost()))

    population.sort(key=lambda t: t[1])
    for _gen in range(gens):
        # elites
        next_pop = population[:3]
        while len(next_pop) < pop_n:
            pa = population[rng.randrange(min(8, len(population)))][0]
            pb = population[rng.randrange(min(8, len(population)))][0]
            child: list[tuple[float, float, float]] = []
            for i in range(len(others)):
                if rng.random() < 0.5:
                    x, y, r = pa[i]
                else:
                    x, y, r = pb[i]
                # blend
                if rng.random() < 0.3:
                    x = 0.5 * (pa[i][0] + pb[i][0])
                    y = 0.5 * (pa[i][1] + pb[i][1])
                # mutate
                if rng.random() < 0.35:
                    x += rng.uniform(-4, 4)
                    y += rng.uniform(-4, 4)
                if rng.random() < 0.12:
                    r = rng.choice([0.0, 90.0, 180.0, 270.0])
                child.append((x, y, r))
            restore(child)
            next_pop.append((snapshot(), total_cost()))
        next_pop.sort(key=lambda t: t[1])
        population = next_pop

    restore(population[0][0])
    best_state = snapshot()
    best_cost = total_cost()

    # =====================================================================
    # 5) Simulated annealing (XY + rotation)
    # =====================================================================
    cost = best_cost
    T0, T1 = 30.0, 0.04
    steps = 200
    for step in range(steps):
        T = T0 * (T1 / T0) ** (step / max(steps - 1, 1))
        p = rng.choice(others)
        ox, oy, orot = p.x, p.y, p.rot
        if rng.random() < 0.18:
            set_rot(p, rng.choice([0.0, 90.0, 180.0, 270.0]))
        else:
            amp = 1.2 + 9.0 * (T / T0)
            p.x += rng.uniform(-amp, amp)
            p.y += rng.uniform(-amp, amp)
        clamp(p)
        eject_keepout(p)
        new_cost = total_cost()
        dE = new_cost - cost
        if dE <= 0 or rng.random() < math.exp(-dE / max(T, 1e-9)):
            cost = new_cost
            if cost < best_cost:
                best_cost = cost
                best_state = snapshot()
        else:
            set_rot(p, orot)
            p.x, p.y = ox, oy

    restore(best_state)
    for p in others:
        clamp(p)
        eject_keepout(p)
    pin_locked_edges()

    # =====================================================================
    # 6) Legalization — separate courtyards until gap clear
    # =====================================================================
    for _ in range(120):
        moved = False
        for p in others:
            if in_keepout(p) > 0:
                eject_keepout(p)
                moved = True
        for i, a in enumerate(movable):
            for b in movable[i + 1 :]:
                if separate_pair(a, b):
                    moved = True
        for p in others:
            clamp(p)
            eject_keepout(p)
        pin_locked_edges()
        clamp(u1)
        if not moved:
            break

    def try_place(p) -> bool:
        step = 3.0
        y = iy0 + p.h / 2
        while y <= iy1 - p.h / 2 + 1e-9:
            x = ix0 + p.w / 2
            while x <= ix1 - p.w / 2 + 1e-9:
                ox, oy = p.x, p.y
                p.x, p.y = x, y
                clamp(p)
                eject_keepout(p)
                if in_keepout(p) > 0:
                    p.x, p.y = ox, oy
                    x += step
                    continue
                if all(q is p or not overlaps(p, q) for q in movable):
                    return True
                p.x, p.y = ox, oy
                x += step
            y += step
        return False

    warns = 0
    for _pass in range(2):
        offenders = [
            p
            for p in others
            if in_keepout(p) > 0 or any(overlaps(p, q) for q in movable if q is not p)
        ]
        if not offenders:
            break
        for p in sorted(offenders, key=lambda q: q.w * q.h, reverse=True):
            if not try_place(p):
                if _pass == 1:
                    print(f"  WARN: {p.ref} still overlaps/keepout")
                    warns += 1
        for __ in range(80):
            moved = False
            for i, a in enumerate(movable):
                for b in movable[i + 1 :]:
                    if separate_pair(a, b):
                        moved = True
            for p in others:
                clamp(p)
                eject_keepout(p)
            pin_locked_edges()
            if not moved:
                break

    for p in others:
        eject_keepout(p)
    pin_locked_edges()

    # Soft pull post-fuse 24V loads toward south band east of fuse
    tx = fuse_out_x() + 14.0
    ty = iy1 - 20.0
    for _ in range(80):
        moved = False
        for p in others:
            if not is_post_fuse_load(p):
                continue
            ox, oy = p.x, p.y
            p.x += 0.4 * (tx - p.x) / max(abs(tx - p.x), 1.0)
            p.y += 0.4 * (ty - p.y) / max(abs(ty - p.y), 1.0)
            clamp(p)
            eject_keepout(p)
            enforce_post_fuse()
            if in_keepout(p) > 0 or any(overlaps(p, q) for q in movable if q is not p):
                p.x, p.y = ox, oy
            elif abs(p.x - ox) + abs(p.y - oy) > 0.02:
                moved = True
        if not moved:
            break

    # Final courtyard separation (soft-pull can leave parts at gap edge)
    for _ in range(200):
        moved = False
        for i, a in enumerate(movable):
            for b in movable[i + 1 :]:
                if separate_pair(a, b):
                    moved = True
        for p in others:
            clamp(p)
            eject_keepout(p)
        pin_locked_edges()
        clamp(u1)
        if not moved:
            break

    overlaps_n = sum(
        1 for i, a in enumerate(movable) for b in movable[i + 1 :] if overlaps(a, b)
    )
    if overlaps_n > 0:
        warns += overlaps_n
    ant_hits = sum(1 for p in others if in_keepout(p) > 0.05)
    metrics = {
        "overlaps": overlaps_n,
        "ant_hits": ant_hits,
        "warns": warns,
        "cost": best_cost,
        "wl": wirelength(),
        "cut": cut_cost(),
        "keepout": antenna_ko(),
        "partition": dict(part_of),
        "gap": cfg.gap,
    }
    print(
        f"Placement {cfg.board_w:.0f}x{cfg.board_h:.0f}: parts={len(movable)} "
        f"overlaps={overlaps_n} ant_hits={ant_hits} warns={warns} "
        f"cost={best_cost:.1f} cut={metrics['cut']:.1f} gap={cfg.gap} "
        f"[mincut+quad+force+GA+SA]"
    )
    return metrics
