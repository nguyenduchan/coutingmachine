#!/usr/bin/env python3
"""Full PCB placement engine for the compact carrier.

Pipeline (matches EDA guide):
  1) Graph partition / min-cut (FM refine on net graph)
  2) Analytical quadratic wirelength (Jacobi on weighted Laplacian)
  3) Force-directed springs (net attract + courtyard repel + antenna)
  4) Genetic / evolutionary refine (XY + 90° rotation)
  5) Simulated annealing (XY + rotation, Metropolis cooling)
  6) Legalization (push + grid)

U1 (WROOM) stays fixed: rot=180, antenna north/top keepout.
J1 (24V) stays fixed: left/west edge, rot=90 (parallel to that edge).
J_USB stays fixed: south edge, rot=0 (mouth outward, axis ⊥ edge).
Inlet chain locked: J1 → D3 → F1 (west edge, fuse out south); all post-fuse 24V loads south/east of F1.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Callable, Sequence


WEAK_NETS = frozenset({
    "GND", "+24V", "+24V_RAW", "+24V_PRE", "+24V_SNS", "+24V_SNS_PRE",
    "+24V_MOT", "+5V", "+3V3",
})

# Parts on these nets must stay near J1 (24V inlet) — but loads only AFTER fuse
RAIL_24_NETS = frozenset({
    "+24V", "+24V_RAW", "+24V_PRE", "+24V_SNS", "+24V_SNS_PRE", "+24V_MOT",
})
POST_FUSE_NETS = frozenset({
    "+24V", "+24V_SNS", "+24V_SNS_PRE", "+24V_MOT",
})  # protected rails (after F1)
PRE_FUSE_REFS = frozenset({"J1", "D3", "F1"})

EDGE_PREF = {
    "SW_BOOT": ("S", 5.0),
    "SW_EN": ("S", 5.0),
    # 24V loads hug west edge near J1
    "U3": ("W", 7.0),
    "PTC_MOT": ("W", 5.5),
    "PTC_SNS": ("W", 5.0),
    "J14": ("W", 6.0),
    "J15": ("W", 6.0),
    "J_DISP": ("S", 7.0),
    "J_KEY": ("S", 6.0),
}

# Spatial bins — POWER/TMC/OPTO packed on west near J1; U1 owns north strip
REGION_BOX = {
    "MCU": (0.35, 0.28, 0.75, 0.65),
    "POWER": (0.04, 0.28, 0.42, 0.72),
    "TMC": (0.04, 0.45, 0.48, 0.88),
    "OPTO": (0.04, 0.32, 0.40, 0.62),
    "HMI": (0.40, 0.55, 0.96, 0.96),
}

REGION_ORDER = ("POWER", "TMC", "OPTO", "MCU", "HMI")


@dataclass
class PlaceCfg:
    board_w: float
    board_h: float
    ox: float
    oy: float
    margin: float
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
    ix0, iy0 = cfg.ox + cfg.margin, cfg.oy + cfg.margin
    ix1, iy1 = cfg.ox + cfg.board_w - cfg.margin, cfg.oy + cfg.board_h - cfg.margin
    by_ref = {p.ref: p for p in parts}

    by_ref["H1"].x, by_ref["H1"].y = cfg.ox + 3.5, cfg.oy + 3.5
    by_ref["H2"].x, by_ref["H2"].y = cfg.ox + cfg.board_w - 3.5, cfg.oy + 3.5
    by_ref["H3"].x, by_ref["H3"].y = cfg.ox + 3.5, cfg.oy + cfg.board_h - 3.5
    by_ref["H4"].x, by_ref["H4"].y = cfg.ox + cfg.board_w - 3.5, cfg.oy + cfg.board_h - 3.5

    movable = [p for p in parts if not p.board_only]
    u1 = by_ref["U1"]
    others = []

    def set_rot(p, rot: float) -> None:
        """Apply rotation; update courtyard w/h. U1/J1/J_USB/D3/F1 locked."""
        if p is u1:
            rot = 180.0
        elif p.ref == "J1":
            rot = 90.0
        elif p.ref == "J_USB":
            rot = 0.0  # local +Y = mouth → world south (outward)
        elif p.ref == "D3":
            rot = 0.0  # anode west → cathode east (RAW→PRE)
        elif p.ref == "F1":
            rot = 90.0  # pad1 PRE north, pad2 +24V south (along west edge)
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
        p.x = min(max(p.x, ix0 + p.w / 2), ix1 - p.w / 2)
        p.y = min(max(p.y, iy0 + p.h / 2), iy1 - p.h / 2)

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
        a_fixed = a.ref in ("U1", "J1", "J_USB", "D3", "F1")
        b_fixed = b.ref in ("U1", "J1", "J_USB", "D3", "F1")

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
        """Keepout in front of antenna tip (north), strip to top board edge."""
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
        if p is u1:
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
        """24V terminal: west/left edge, pins parallel to that edge (rot=90)."""
        set_rot(j1, 90.0)
        j1.x = ix0 + j1.w / 2
        # Below antenna keepout / U1 north strip
        _kx0, _ky0, _kx1, ky1 = antenna_ko()
        ymin = max(iy0 + j1.h / 2, ky1 + j1.h / 2 + 2.0, u1.y + u1.h / 2 + cfg.gap)
        ymax = iy1 - j1.h / 2
        if j1.y < ymin or j1.y > ymax:
            j1.y = min(max(u1.y + 0.28 * cfg.board_h, ymin), ymax)
        j1.y = min(max(j1.y, ymin), ymax)
        clamp(j1)

    def pin_j_usb() -> None:
        """USB Micro-B: flush south Edge.Cuts, mouth +Y outward (rot=0)."""
        set_rot(usb, 0.0)
        # Footprint: mouth at local +Y (silk OUT), pads at −Y (inboard).
        # CrtYd end y=+4.0 → south face on Edge.Cuts.
        south_ext = 4.0
        usb.y = cfg.oy + cfg.board_h - south_ext
        usb.x = cfg.ox + 0.72 * cfg.board_w
        usb.x = min(max(usb.x, ix0 + usb.w / 2), ix1 - usb.w / 2)

    def pin_inlet_chain() -> None:
        """J1 → D3 → F1 along west: fuse vertical, +24V out toward south."""
        pin_j1()
        chain_gap = cfg.gap + 0.5
        set_rot(d3, 0.0)
        d3.x = j1.x + j1.w / 2 + chain_gap + d3.w / 2
        d3.y = j1.y
        d3.y = min(max(d3.y, iy0 + d3.h / 2), iy1 - d3.h / 2)
        # F1 rot=90: tall on west; clear below J1/D3 courtyards
        set_rot(f1, 90.0)
        f1.x = ix0 + f1.w / 2
        y_clear = max(j1.y + j1.h / 2, d3.y + d3.h / 2) + chain_gap
        f1.y = y_clear + f1.h / 2
        f1.y = min(max(f1.y, iy0 + f1.h / 2), iy1 - f1.h / 2)

    def fuse_out_y() -> float:
        """World Y of F1 pad2 (+24V) with rot=90 (local +11.25 → +Y)."""
        return f1.y + 11.25

    def fuse_out_x() -> float:
        """West-strip east face — loads stay east of inlet column."""
        return max(f1.x + f1.w / 2, d3.x + d3.w / 2, j1.x + j1.w / 2)

    def is_post_fuse_load(p) -> bool:
        if p.ref in PRE_FUSE_REFS:
            return False
        return any(n in POST_FUSE_NETS for n in (p.pad_nets or {}).values())

    def enforce_post_fuse() -> None:
        """Keep +24V loads out of pre-fuse inlet pocket (west of column AND north of fuse out).

        Allowed: east of inlet column, or south of fuse output (or both).
        """
        ymin = fuse_out_y() + cfg.gap
        xmin = fuse_out_x() + cfg.gap
        for p in others:
            if not is_post_fuse_load(p):
                continue
            left = p.x - p.w / 2
            top = p.y - p.h / 2
            in_pocket = left < xmin and top < ymin
            if in_pocket:
                # Prefer push east (beside fuse) — denser than forcing everything south
                p.x = xmin + p.w / 2
                if p.y - p.h / 2 < ymin and p.x - p.w / 2 < xmin:
                    p.y = ymin + p.h / 2
            clamp(p)
            eject_keepout(p)

    def pin_locked_edges() -> None:
        pin_inlet_chain()
        pin_j_usb()
        enforce_post_fuse()

    # --- pin U1 + inlet J1→D3→F1 + J_USB ---
    set_rot(u1, 180.0)
    u1.y = cfg.oy + cfg.margin + cfg.ant_clear + cfg.ant_tip
    u1.x = cfg.ox + 0.55 * cfg.board_w
    clamp(u1)

    j1 = by_ref["J1"]
    d3 = by_ref["D3"]
    f1 = by_ref["F1"]
    usb = by_ref["J_USB"]
    locked_refs = {"U1", "J1", "J_USB", "D3", "F1"}
    others = [p for p in movable if p.ref not in locked_refs]

    def is_locked(p) -> bool:
        return p.ref in locked_refs

    j1.y = u1.y + u1.h / 2 + cfg.gap + j1.h / 2 + 1.0  # tight under U1; F1 hangs south
    pin_locked_edges()

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
        if rname in ("POWER", "TMC", "OPTO"):
            # pack beside/below fuse (east of inlet OR south of fuse out)
            x = max(x0 + 1.0, fuse_out_x() + cfg.gap)
            y = max(y0 + 1.0, j1.y - 6.0)
        else:
            x, y = x0 + 1.0, y0 + 1.0
        row_h = 0.0
        for p in group:
            if x + p.w / 2 > x1 - 1.0:
                x = (
                    x0 + 1.0
                    if rname not in ("POWER", "TMC", "OPTO")
                    else max(x0 + 1.0, fuse_out_x() + cfg.gap)
                )
                y += row_h + cfg.gap
                row_h = 0.0
            p.x = min(max(x + p.w / 2, x0 + p.w / 2), x1 - p.w / 2)
            p.y = min(max(y + p.h / 2, y0 + p.h / 2), y1 - p.h / 2)
            if is_post_fuse_load(p):
                xmin = fuse_out_x() + cfg.gap
                ymin = fuse_out_y() + cfg.gap
                if p.x - p.w / 2 < xmin and p.y - p.h / 2 < ymin:
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
            return (p.x, iy1 - p.h / 2, 0.4 * s / 10)
        if side == "W":
            # hug west post-fuse: east of inlet, may sit beside F1
            tx = fuse_out_x() + cfg.gap + p.w / 2 + 1.0
            ty = max(p.y, j1.y)
            return (tx, ty, 0.4 * s / 10)
        if side == "E":
            return (ix1 - p.w / 2, p.y, 0.4 * s / 10)
        return None

    for _ in range(80):
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

    for _ in range(280):
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
                tx = fuse_out_x() + 12.0
                ty = 0.5 * (j1.y + fuse_out_y())
                fx += 0.12 * (tx - p.x)
                fy += 0.08 * (ty - p.y)
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
        return 50.0 * abs(j1.x - (ix0 + j1.w / 2)) + 20.0 * (0.0 if abs(j1.rot - 90.0) < 0.1 else 100.0)

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
                target_x = fuse_out_x() + cfg.gap + p.w / 2 + 1.0
                target_y = max(iy0 + p.h / 2, j1.y)
                s += w * (abs(p.x - target_x) + 0.5 * abs(p.y - target_y))
            elif side == "E":
                s += w * abs(p.x - (ix1 - p.w / 2))
        return s

    def rail_24_cost() -> float:
        """Penalize post-fuse loads inside pre-fuse inlet pocket."""
        s = 0.0
        xmin = fuse_out_x() + cfg.gap
        ymin = fuse_out_y() + cfg.gap
        tx = xmin + 10.0
        ty = 0.5 * (j1.y + fuse_out_y())
        for p in others:
            if not is_post_fuse_load(p):
                continue
            left = p.x - p.w / 2
            top = p.y - p.h / 2
            if left < xmin and top < ymin:
                s += 100.0 * ((xmin - left) ** 2 + (ymin - top) ** 2)
            s += abs(p.x - tx) + 0.5 * abs(p.y - ty)
        return s
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
    pop_n, gens = 12, 14
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
    steps = 2200
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
    for _ in range(800):
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
        step = 1.0
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
    for _pass in range(4):
        offenders = [
            p
            for p in others
            if in_keepout(p) > 0 or any(overlaps(p, q) for q in movable if q is not p)
        ]
        if not offenders:
            break
        for p in sorted(offenders, key=lambda q: q.w * q.h, reverse=True):
            if not try_place(p):
                if _pass == 3:
                    print(f"  WARN: {p.ref} still overlaps/keepout")
                    warns += 1
        for __ in range(1000):
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

    # Soft pull post-fuse 24V loads toward east of inlet (beside fuse)
    tx = fuse_out_x() + 12.0
    ty = 0.5 * (j1.y + fuse_out_y())
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
    for _ in range(1200):
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
