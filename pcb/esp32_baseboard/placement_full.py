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

# Soft prefs — only inland parts that prefer south (PTC near motors/fuse)
EDGE_PREF = {
    "PTC_MOT": ("S", 4.0),
    "PTC_MOT2": ("S", 4.0),
    "PTC_SNS": ("S", 3.0),
}

# Fractions of the *inland* box (not full board) — dense, little empty mid.
REGION_BOX = {
    "MCU": (0.42, 0.00, 1.00, 0.55),
    "HMI": (0.42, 0.00, 1.00, 0.42),
    "OPTO": (0.00, 0.00, 0.62, 0.58),
    "POWER": (0.00, 0.38, 0.55, 1.00),
    "TMC": (0.25, 0.42, 0.82, 1.00),
    "PWR": (0.52, 0.42, 1.00, 1.00),
}

REGION_ORDER = ("POWER", "TMC", "OPTO", "PWR", "MCU", "HMI")

LOCKED_REFS = frozenset({
    "U1", "J1", "J_USB", "D3", "F1",
    "J_MOT1", "J_MOT2", "U3", "U4",
    "U_PWR1", "U_PWR2", "U_VIB",
    "J14", "J15", "J_IN2", "J_IN3", "J_CNT5",
    "J_KEY", "J_DISP", "J_P24S",
    "SW_BOOT", "SW_NRST",
})

# Field cable jacks on N/S only — keypad + TM1637 sit on the north panel edge.
EDGE_JACK_REFS = frozenset({
    "J1", "J_MOT1", "J_MOT2", "J_P24S",
    "U_PWR1", "U_PWR2", "U_VIB",
    "J14", "J15", "J_IN2", "J_IN3", "J_CNT5",
    "J_KEY", "J_DISP", "J_USB",
})

NORTH_EDGE_JACKS = frozenset({
    "J14", "J15", "J_IN2", "J_IN3", "J_CNT5",
    "J_KEY", "J_DISP", "J_USB",
})
SOUTH_EDGE_JACKS = frozenset({
    "J1", "J_MOT1", "J_MOT2",
    "U_PWR1", "U_PWR2", "U_VIB", "J_P24S",
})
SOUTH_PACK_RIGHT = (
    "J_MOT1", "J_MOT2",
    "U_PWR1", "U_PWR2", "U_VIB",
    "J_P24S",
)
NORTH_PACK_ORDER = (
    "J14", "J15", "J_IN2", "J_IN3",
    "J_CNT5", "J_KEY", "J_DISP", "J_USB",
)
HOLE_REFS = frozenset({"H1", "H2", "H3", "H4"})
HOLE_INSET = 4.5  # M3 center from L/R Edge.Cuts (courtyard r=3.5)
HOLE_NS_INSET = 20.0  # M3 center from N/S edges — inland of jack housings
XH_EDGE_REFS = frozenset({
    "J14", "J15", "J_IN2", "J_IN3", "J_CNT5", "J_DISP",
    "J_MOT1", "J_MOT2", "J_P24S",
})


def pair_courtyard_gap(a_ref: str, b_ref: str, default: float, jack_pack: float) -> float:
    """Courtyard gap: jack↔jack = jack_pack; electronics↔jack ≥3 mm; else default."""
    a_j = a_ref in EDGE_JACK_REFS
    b_j = b_ref in EDGE_JACK_REFS
    if a_j != b_j:
        return max(default, 3.0)
    if a_j and b_j:
        return max(jack_pack, default)
    return default


def jack_hline_union(
    aabbs: dict[str, tuple[float, float, float, float]], refs: frozenset
) -> tuple[float, float]:
    """Union of jack courtyard Y. Every y in [lo, hi] is a horizontal line through a jack."""
    lo, hi = 1e9, -1e9
    n = 0
    for ref in refs:
        box = aabbs.get(ref)
        if box is None:
            continue
        lo = min(lo, box[1])
        hi = max(hi, box[3])
        n += 1
    if n == 0:
        return (0.0, 0.0)
    return (lo, hi)


def dist_aabb_to_hline(ay0: float, ay1: float, y_line: float) -> float:
    """Distance from nearest box edge to a horizontal line. 0 if the line cuts the box."""
    if ay0 <= y_line <= ay1:
        return 0.0
    return min(abs(ay0 - y_line), abs(ay1 - y_line))


@dataclass
class PlaceCfg:
    board_w: float
    board_h: float
    ox: float
    oy: float
    margin: float  # non-jack ≥ this from left/right Edge.Cuts
    jack_margin: float  # field jacks may be closer to N/S
    jack_side_keep: float  # field jacks ≥ this from L/R (box corners / DIN clip)
    jack_pack: float  # courtyard gap between adjacent N/S field jacks
    jack_row_sep: float  # electronics AABB vs full-width jack-row band
    gap: float
    ant_tip: float
    ant_clear: float
    ant_half_w: float
    courtyard_size: Callable[[str], tuple[float, float]]


def _rot_local(x: float, y: float, rot: float) -> tuple[float, float]:
    r = int(rot) % 360
    if r == 90:
        return -y, x
    if r == 180:
        return -x, -y
    if r == 270:
        return y, -x
    return x, y


def _aabb(p) -> tuple[float, float, float, float]:
    """World AABB of the footprint courtyard. Origin (p.x, p.y) is KiCad (0,0)."""
    loc = getattr(p, "aabb_local", None)
    if not loc:
        return (p.x - p.w / 2, p.y - p.h / 2, p.x + p.w / 2, p.y + p.h / 2)
    x0, y0, x1, y1 = loc
    xs: list[float] = []
    ys: list[float] = []
    for x, y in ((x0, y0), (x0, y1), (x1, y0), (x1, y1)):
        rx, ry = _rot_local(x, y, p.rot)
        xs.append(p.x + rx)
        ys.append(p.y + ry)
    return (min(xs), min(ys), max(xs), max(ys))


def _shift_aabb_x0(p, x0: float) -> None:
    ax0, _, _, _ = _aabb(p)
    p.x += x0 - ax0


def _shift_aabb_y0(p, y0: float) -> None:
    _, ay0, _, _ = _aabb(p)
    p.y += y0 - ay0


def _shift_aabb_y1(p, y1: float) -> None:
    _, _, _, ay1 = _aabb(p)
    p.y += y1 - ay1


def _shift_aabb_x1(p, x1: float) -> None:
    _, _, ax1, _ = _aabb(p)
    p.x += x1 - ax1


def _rects_overlap(a, b) -> bool:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return not (ax1 <= bx0 or bx1 <= ax0 or ay1 <= by0 or by1 <= ay0)


def pack_parts(parts: list, cfg: PlaceCfg, seed: int = 42, anchors: dict | None = None) -> dict:
    rng = random.Random(seed)
    sticky = bool(anchors)
    print(
        f"  packing {cfg.board_w:.0f}x{cfg.board_h:.0f}"
        f"{' (min-disp vs PCB)' if sticky else ''} …",
        flush=True,
    )
    # Inner keep-in for non-jacks (≥ margin from L/R Edge.Cuts)
    ix0, iy0 = cfg.ox + cfg.margin, cfg.oy + cfg.margin
    ix1, iy1 = cfg.ox + cfg.board_w - cfg.margin, cfg.oy + cfg.board_h - cfg.margin
    # Field jacks hug N/S; inset from L/R so box walls / DIN clips do not hit housings
    jack_side = max(cfg.jack_margin, getattr(cfg, "jack_side_keep", 6.0))
    jx0, jy0 = cfg.ox + jack_side, cfg.oy + cfg.jack_margin
    jx1, jy1 = cfg.ox + cfg.board_w - jack_side, cfg.oy + cfg.board_h - cfg.jack_margin
    by_ref = {p.ref: p for p in parts}
    jack_row_overflow = [0.0]

    movable = [p for p in parts if not p.board_only]
    holes = [by_ref["H1"], by_ref["H2"], by_ref["H3"], by_ref["H4"]]
    u1 = by_ref["U1"]
    others = []
    # Jack-row lines = every horizontal line that cuts a jack courtyard (union of Y).
    # Electronics AABB must not cut those lines; nearest box edge ≥ jack_row_sep.
    inland_clear = max(cfg.gap, getattr(cfg, "jack_row_sep", 3.0), 3.0)
    n_row_y1 = cfg.oy
    s_row_y0 = cfg.oy + cfg.board_h

    def update_inland_box() -> None:
        """Keep-in: ≥margin from L/R, and ≥jack_row_sep from N/S jack-row h-lines."""
        nonlocal iy0, iy1, n_row_y1, s_row_y0
        boxes = {p.ref: _aabb(p) for p in parts}
        n_lo, n_hi = jack_hline_union(boxes, NORTH_EDGE_JACKS)
        s_lo, s_hi = jack_hline_union(boxes, SOUTH_EDGE_JACKS)
        n_row_y1 = n_hi  # inland-most north jack courtyard line
        s_row_y0 = s_lo  # inland-most south jack courtyard (not TMC)
        iy0 = n_row_y1 + inland_clear
        iy1 = s_row_y0 - inland_clear

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
        elif p.ref in XH_EDGE_REFS:
            # Pads along local +X; extra housing toward +Y.
            # North: rot 0 (body inland). South: rot 180 (body inland).
            rot = 180.0 if p.ref in SOUTH_EDGE_JACKS else 0.0
        elif p.ref in ("J_KEY", "U_PWR1", "U_PWR2", "U_VIB"):
            # Native pad row is local +Y → rot 90 = pin row || N/S edge
            rot = 90.0
        elif p.ref in ("U3", "U4"):
            rot = 0.0  # square StepStick inland (not a field jack)
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
        if p.ref in HOLE_REFS:
            # Holes live in the L/R keep strips — only stay inside Edge.Cuts.
            x0, y0 = cfg.ox + 0.4, cfg.oy + 0.4
            x1, y1 = cfg.ox + cfg.board_w - 0.4, cfg.oy + cfg.board_h - 0.4
        elif p.ref in EDGE_JACK_REFS:
            x0, y0, x1, y1 = jx0, jy0, jx1, jy1
        else:
            # Electronics: ≥ margin from L/R, ≥ jack_row_sep from N/S jack-row lines
            x0, y0, x1, y1 = ix0, iy0, ix1, iy1
        ax0, ay0, ax1, ay1 = _aabb(p)
        if ax0 < x0:
            p.x += x0 - ax0
        if ay0 < y0:
            p.y += y0 - ay0
        if ax1 > x1:
            p.x += x1 - ax1
        if ay1 > y1:
            p.y += y1 - ay1

    def clamp_electronics() -> None:
        """Every non-jack AABB stays inside the inland rectangle (out of jack rows)."""
        update_inland_box()
        for p in parts:
            if p.ref in EDGE_JACK_REFS or p.ref in HOLE_REFS:
                continue
            clamp(p)

    def _need(a, b) -> float:
        return pair_courtyard_gap(a.ref, b.ref, cfg.gap, cfg.jack_pack)

    def overlaps(a, b) -> bool:
        # tol: treat exact gap contact as clear (float edge)
        tol = 1e-3
        g = _need(a, b)
        ax0, ay0, ax1, ay1 = _aabb(a)
        bx0, by0, bx1, by1 = _aabb(b)
        return (
            ax1 + g - tol > bx0
            and bx1 + g - tol > ax0
            and ay1 + g - tol > by0
            and by1 + g - tol > ay0
        )

    def overlap_depth(a, b) -> float:
        tol = 1e-3
        g = _need(a, b)
        ax0, ay0, ax1, ay1 = _aabb(a)
        bx0, by0, bx1, by1 = _aabb(b)

        def shortfall(a0, a1, b0, b1) -> float:
            if a1 <= b0:
                dist = b0 - a1
            elif b1 <= a0:
                dist = a0 - b1
            else:
                dist = -(min(a1, b1) - max(a0, b0))
            return g - dist - tol

        ox = shortfall(ax0, ax1, bx0, bx1)
        oy = shortfall(ay0, ay1, by0, by1)
        if ox <= 0 or oy <= 0:
            return 0.0
        return min(ox, oy)

    def separate_pair(a, b) -> bool:
        """Push apart so AABB + gap no longer overlap. Returns True if moved."""
        a_jack = a.ref in EDGE_JACK_REFS
        b_jack = b.ref in EDGE_JACK_REFS
        if a_jack != b_jack and a.ref not in HOLE_REFS and b.ref not in HOLE_REFS:
            elec = b if a_jack else a
            ea = _aabb(elec)
            moved = False
            if dist_aabb_to_hline(ea[1], ea[3], n_row_y1) < inland_clear:
                elec.y += (n_row_y1 + inland_clear) - ea[1]
                clamp(elec)
                moved = True
            ea = _aabb(elec)
            if dist_aabb_to_hline(ea[1], ea[3], s_row_y0) < inland_clear:
                elec.y += (s_row_y0 - inland_clear) - ea[3]
                clamp(elec)
                moved = True
            if moved:
                return True
        d = overlap_depth(a, b)
        if d <= 0:
            return False
        ac = _aabb(a)
        bc = _aabb(b)
        dx = (bc[0] + bc[2]) / 2 - (ac[0] + ac[2]) / 2
        dy = (bc[1] + bc[3]) / 2 - (ac[1] + ac[3]) / 2
        if abs(dx) < 1e-9 and abs(dy) < 1e-9:
            dx, dy = 1.0, 0.0
        ax0, ay0, ax1, ay1 = ac
        bx0, by0, bx1, by1 = bc
        g = _need(a, b)
        min_dx = (ax1 - ax0 + bx1 - bx0) / 2 + g
        min_dy = (ay1 - ay0 + by1 - by0) / 2 + g
        ox = min_dx - abs(dx)
        oy = min_dy - abs(dy)
        eps = 0.05
        a_fixed = a.ref in locked_refs or a_jack or a.ref.startswith("H")
        b_fixed = b.ref in locked_refs or b_jack or b.ref.startswith("H")
        if a_fixed and b_fixed:
            if a_jack and not b_jack:
                b_fixed = False
            elif b_jack and not a_jack:
                a_fixed = False

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
        _shift_aabb_y1(j1, jy1)
        _shift_aabb_x0(j1, jx0)
        clamp(j1)

    def pin_inlet_inland() -> None:
        """D3/F1 inland of J1, ≥3 mm from jack-row line and from nearby jack courtyards."""
        chain_gap = max(cfg.gap, inland_clear)
        set_rot(d3, 0.0)
        y1 = min(iy1, _aabb(j1)[1] - chain_gap)
        _shift_aabb_x0(d3, _aabb(j1)[2] + chain_gap)
        _shift_aabb_y1(d3, y1)
        clamp(d3)
        set_rot(f1, 0.0)
        _shift_aabb_x0(f1, _aabb(d3)[2] + chain_gap)
        _shift_aabb_y1(f1, y1)
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

    def pack_row_even(
        refs: tuple[str, ...], x0: float, x1: float, min_gap: float, target_gap: float,
        flush_y, *, spread_extra: bool = True,
    ) -> float:
        """Place refs W→E in [x0,x1]. Courtyard gap ≥ min_gap.

        If spread_extra, leftover span is split between jacks (even row).
        Else jacks sit at target_gap and unused space stays east of the last.
        Returns overflow mm (0 if the row fits).
        """
        items = [(ref, by_ref[ref]) for ref in refs if ref in by_ref]
        n = len(items)
        if n == 0:
            return 0.0
        widths = [_aabb(p)[2] - _aabb(p)[0] for _, p in items]
        gaps_n = max(n - 1, 0)
        avail = x1 - x0
        need = sum(widths) + target_gap * gaps_n
        extra = avail - need
        if extra >= -1e-3 and gaps_n:
            gap = target_gap + (extra / gaps_n if spread_extra else 0.0)
        elif gaps_n:
            gap = (avail - sum(widths)) / gaps_n
        else:
            gap = target_gap
        overflow = 0.0
        if gap < min_gap - 1e-3:
            overflow = (min_gap - gap) * gaps_n
            gap = min_gap
        x = x0
        for (_ref, p), _w in zip(items, widths):
            flush_y(p)
            _shift_aabb_x0(p, x)
            x = _aabb(p)[2] + gap
        last = items[-1][1]
        if _aabb(last)[2] > x1 + 1e-3:
            overflow = max(overflow, _aabb(last)[2] - x1)
        return overflow

    def pin_edge_jacks() -> None:
        """Field jacks on N/S only.

        North: sensors → keypad → TM1637 → USB, packed at jack_pack (no inflated gaps).
        South: J1 SW then MOT/PWR even-packed to the east keep.
        """
        pack = max(cfg.jack_pack, cfg.gap)
        # North is tight (KEY+DISP on the edge). Do not inflate gaps above jack_pack.
        n_target = pack
        s_target = max(pack, 6.0)

        for ref in NORTH_PACK_ORDER:
            if ref not in by_ref:
                continue
            p = by_ref[ref]
            if ref == "J_USB":
                set_rot(p, 180.0)
            elif ref == "J_KEY":
                set_rot(p, 90.0)
            else:
                set_rot(p, 0.0)

        n_ov = pack_row_even(
            NORTH_PACK_ORDER, jx0, jx1, pack, n_target,
            lambda p: _shift_aabb_y0(p, jy0),
            spread_extra=False,
        )

        set_rot(j1, 0.0)
        for ref in SOUTH_PACK_RIGHT:
            if ref not in by_ref:
                continue
            p = by_ref[ref]
            if ref in ("U_PWR1", "U_PWR2", "U_VIB"):
                set_rot(p, 90.0)
            else:
                set_rot(p, 180.0)
        s_ov = pack_row_even(
            ("J1",) + SOUTH_PACK_RIGHT,
            jx0,
            jx1,
            pack,
            s_target,
            lambda p: _shift_aabb_y1(p, jy1),
        )
        jack_row_overflow[0] = max(n_ov, s_ov)
        update_inland_box()

    def pin_tmc_inland() -> None:
        """U3/U4 StepStick modules sit inland, not in the field-jack row."""
        gap = max(cfg.gap, inland_clear)
        u3, u4 = by_ref["U3"], by_ref["U4"]
        set_rot(u3, 0.0)
        set_rot(u4, 0.0)
        _shift_aabb_y1(u3, iy1)
        _shift_aabb_y1(u4, iy1)
        mot1 = _aabb(by_ref["J_MOT1"])
        _shift_aabb_x0(u3, max(_aabb(f1)[2] + gap, mot1[0]))
        clamp(u3)
        _shift_aabb_x0(u4, _aabb(u3)[2] + gap)
        _shift_aabb_y1(u4, iy1)
        clamp(u4)

    def pin_boot_switches() -> None:
        """SW_BOOT + SW_NRST inland of J_USB, fully inside the east keep."""
        usb = by_ref["J_USB"]
        gap = max(cfg.gap, inland_clear)
        boots = ("SW_BOOT", "SW_NRST")
        for sref in boots:
            set_rot(by_ref[sref], 0.0)
        sw0 = by_ref["SW_BOOT"]
        sw1 = by_ref["SW_NRST"]
        y0 = iy0
        for ref in NORTH_EDGE_JACKS:
            if ref in by_ref:
                y0 = max(y0, _aabb(by_ref[ref])[3] + inland_clear)
        usb_box = _aabb(usb)
        # NRST at the east face of USB; BOOT west of NRST — never clamp-stack on ix1.
        _shift_aabb_y0(sw1, y0)
        _shift_aabb_x1(sw1, min(ix1, usb_box[2]))
        _shift_aabb_y0(sw0, y0)
        _shift_aabb_x1(sw0, _aabb(sw1)[0] - gap)

    def pin_holes() -> None:
        """M3 on L/R keep strips — DIN clips / box side bosses, not in N/S jack rows."""
        hx0 = cfg.ox + HOLE_INSET
        hx1 = cfg.ox + cfg.board_w - HOLE_INSET
        hy0 = cfg.oy + HOLE_NS_INSET
        hy1 = cfg.oy + cfg.board_h - HOLE_NS_INSET
        spots = {
            "H1": (hx0, hy0),
            "H2": (hx1, hy0),
            "H3": (hx0, hy1),
            "H4": (hx1, hy1),
        }
        for href, (x, y) in spots.items():
            h = by_ref[href]
            h.x, h.y = x, y
            clamp(h)

    def apply_anchors() -> None:
        """Seed every part from saved/live PCB poses (minimum displacement)."""
        if not anchors:
            return
        for p in parts:
            rec = anchors.get(p.ref)
            if rec is None:
                continue
            x, y, r = rec
            set_rot(p, r)
            p.x, p.y = x, y

    def flush_user_jacks() -> None:
        """Keep user jack X; snap to N/S; push neighbors apart if courtyards clash."""
        pack = max(cfg.jack_pack, cfg.gap)
        for ref in NORTH_PACK_ORDER:
            if ref not in by_ref:
                continue
            p = by_ref[ref]
            if ref == "J_USB":
                set_rot(p, 180.0)
            elif ref == "J_KEY":
                set_rot(p, 90.0)
            else:
                set_rot(p, 0.0)
            _shift_aabb_y0(p, jy0)
            clamp(p)
        set_rot(j1, 0.0)
        _shift_aabb_y1(j1, jy1)
        clamp(j1)
        for ref in SOUTH_PACK_RIGHT:
            if ref not in by_ref:
                continue
            p = by_ref[ref]
            if ref in ("U_PWR1", "U_PWR2", "U_VIB"):
                set_rot(p, 90.0)
            else:
                set_rot(p, 180.0)
            _shift_aabb_y1(p, jy1)
            clamp(p)

        overflow = 0.0
        for row in (NORTH_PACK_ORDER, ("J1",) + SOUTH_PACK_RIGHT):
            # Keep W→E pack order (KEY origin is pin 1; courtyard hangs west at rot 90).
            items = [by_ref[r] for r in row if r in by_ref]
            for i in range(len(items) - 1):
                a, b = items[i], items[i + 1]
                need = _aabb(a)[2] + pack
                if _aabb(b)[0] < need - 1e-3:
                    _shift_aabb_x0(b, need)
                    clamp(b)
            if items and _aabb(items[-1])[2] > jx1 + 1e-3:
                overflow = max(overflow, _aabb(items[-1])[2] - jx1)
                _shift_aabb_x1(items[-1], jx1)
                for i in range(len(items) - 2, -1, -1):
                    a, b = items[i], items[i + 1]
                    limit = _aabb(b)[0] - pack
                    if _aabb(a)[2] > limit + 1e-3:
                        _shift_aabb_x1(a, limit)
                        clamp(a)
            if items and _aabb(items[0])[0] < jx0 - 1e-3:
                overflow = max(overflow, jx0 - _aabb(items[0])[0])
        jack_row_overflow[0] = overflow
        update_inland_box()

    def pin_u1_open() -> None:
        """STM32 east-north 3V3, with air below BOOT/NRST and off the east keep."""
        set_rot(u1, 0.0)
        update_inland_box()
        air = 8.0
        y0 = iy0 + air
        for ref in ("SW_BOOT", "SW_NRST"):
            if ref in by_ref:
                y0 = max(y0, _aabb(by_ref[ref])[3] + air)
        _shift_aabb_y0(u1, y0)
        _shift_aabb_x1(u1, ix1 - 3.0)
        # SW_BOOT is north of U1 (Y already cleared); only keep X vs same-band parts.
        west_lim = ix0
        for ref in ("R_BOOT",):
            if ref in by_ref:
                rb = _aabb(by_ref[ref])
                ua = _aabb(u1)
                y_hit = not (rb[3] + cfg.gap <= ua[1] or ua[3] + cfg.gap <= rb[1])
                if y_hit:
                    west_lim = max(west_lim, rb[2] + cfg.gap)
        if _aabb(u1)[0] < west_lim:
            _shift_aabb_x0(u1, west_lim)
        clamp(u1)

    def pin_locked_edges() -> None:
        if sticky:
            # Hand-tuned / saved poses stay put — do not re-pack N/S rows.
            update_inland_box()
            return
        pin_j1()
        pin_edge_jacks()
        update_inland_box()
        pin_inlet_inland()
        pin_tmc_inland()
        pin_boot_switches()
        pin_holes()
        pin_u1_open()
        for pref in ("D3", "F1", "U3", "U4"):
            clamp(by_ref[pref])
        enforce_post_fuse()
        clamp_electronics()

    def eject_holes() -> None:
        for p in others:
            for h in holes:
                separate_pair(h, p)
            clamp(p)

    j1 = by_ref["J1"]
    d3 = by_ref["D3"]
    f1 = by_ref["F1"]
    usb = by_ref["J_USB"]
    locked_refs = set(LOCKED_REFS)
    if sticky and anchors:
        locked_refs.update(anchors)
    others = [p for p in movable if p.ref not in locked_refs]

    def is_locked(p) -> bool:
        return p.ref in locked_refs

    if sticky:
        apply_anchors()
    pin_locked_edges()
    # Sticky: U1 stays on saved pose. Fresh pack: pin_u1_open set it.

    def pull_to_anchors() -> bool:
        """Greedy step toward PCB coords if the trial pose stays legal."""
        if not anchors:
            return False
        moved = False
        for p in others:
            rec = anchors.get(p.ref)
            if rec is None:
                continue
            ax, ay, _ = rec
            for k in (1.0, 0.5, 0.25, 0.12, 0.05):
                ox, oy = p.x, p.y
                p.x = ox + k * (ax - ox)
                p.y = oy + k * (ay - oy)
                clamp(p)
                eject_keepout(p)
                ok = in_keepout(p) <= 0 and all(
                    q is p or not overlaps(p, q) for q in movable + holes
                )
                if ok and abs(p.x - ox) + abs(p.y - oy) > 0.02:
                    moved = True
                    break
                p.x, p.y = ox, oy
        return moved

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
        """Map cluster fractions onto the inland keep-in (jack rows excluded)."""
        x0, y0, x1, y1 = REGION_BOX[name]
        return (
            ix0 + x0 * (ix1 - ix0),
            iy0 + y0 * (iy1 - iy0),
            ix0 + x1 * (ix1 - ix0),
            iy0 + y1 * (iy1 - iy0),
        )

    def shelf_pack(group: list, bx0: float, by0: float, bx1: float, by1: float) -> None:
        """Left-to-right, top-to-bottom pack using real courtyard AABB."""
        x, y = bx0, by0
        row_h = 0.0
        for p in group:
            ax0, ay0, ax1, ay1 = _aabb(p)
            w, h = ax1 - ax0, ay1 - ay0
            if x > bx0 + 0.01 and x + w > bx1:
                x = bx0
                y += row_h + cfg.gap
                row_h = 0.0
            _shift_aabb_x0(p, x)
            _shift_aabb_y0(p, y)
            clamp(p)
            ax0, ay0, ax1, ay1 = _aabb(p)
            x = ax1 + cfg.gap
            row_h = max(row_h, ay1 - ay0)

    def compact_inland() -> None:
        """Shelf-pack inland clusters into non-overlapping bands, skipping locked bodies."""
        def fits(p) -> bool:
            return all(q is p or not overlaps(p, q) for q in movable + holes)

        def pack_group(group: list, bx0: float, by0: float, bx1: float, by1: float) -> None:
            step = 1.5
            for p in group:
                placed = False
                y = by0
                while not placed and y < by1:
                    x = bx0
                    while not placed and x < bx1:
                        _shift_aabb_x0(p, x)
                        _shift_aabb_y0(p, y)
                        clamp(p)
                        if fits(p):
                            placed = True
                            break
                        x += step
                    y += step
                if not placed:
                    clamp(p)

        mx = 0.50 * (ix0 + ix1)
        my = 0.48 * (iy0 + iy1)
        bands = (
            ("OPTO", ix0, iy0, mx + 4.0, my),
            ("MCU", mx - 4.0, iy0, ix1, my),
            ("HMI", mx - 4.0, iy0, ix1, my),
            ("POWER", ix0, my - 4.0, mx, iy1),
            ("TMC", mx - 10.0, my - 4.0, mx + 18.0, iy1),
            ("PWR", mx + 8.0, my - 4.0, ix1, iy1),
        )
        for rname, bx0, by0, bx1, by1 in bands:
            group = sorted(
                [p for p in others if part_of.get(p.ref, p.cluster) == rname],
                key=lambda q: q.w * q.h,
                reverse=True,
            )
            if group:
                pack_group(group, bx0, by0, bx1, by1)

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

    if not sticky:
        fm_refine()

        # seed place: dense shelf inside each inland cluster band
        compact_inland()
        for p in others:
            if is_post_fuse_load(p):
                xmin = fuse_out_x() + cfg.gap
                ax0, ay0, ax1, ay1 = _aabb(p)
                if ax1 < xmin and ay1 > fuse_out_y() - 2.0:
                    _shift_aabb_x0(p, xmin)
            clamp(p)
            eject_keepout(p)

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

    for _ in range(0 if sticky else 40):
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
        # Keep clusters in their inland bands (no pull toward empty board center)
        rname = part_of.get(p.ref, "MCU")
        box = region_box(rname)
        mx = 0.5 * (box[0] + box[2])
        my = 0.5 * (box[1] + box[3])
        fx += 0.10 * (mx - p.x)
        fy += 0.10 * (my - p.y)
        return fx, fy

    for _ in range(0 if sticky else 30):
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
    pop_n, gens = 1, 0
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
    steps = 0 if sticky else 0
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
    for _ in range(60):
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
        if sticky and pull_to_anchors():
            moved = True
        pin_locked_edges()
        if not sticky:
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
    for _pass in range(0 if sticky else 2):
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
            clamp_electronics()
            if not moved:
                break

    for p in others:
        eject_keepout(p)
    pin_locked_edges()
    clamp_electronics()

    # Soft pull post-fuse 24V loads toward south band east of fuse
    tx = fuse_out_x() + 14.0
    ty = iy1 - 20.0
    for _ in range(0 if sticky else 40):
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

    if not sticky:
        compact_inland()
        pin_locked_edges()
        clamp(u1)
    eject_holes()
    if sticky:
        pull_to_anchors()

    # Final courtyard separation
    for _ in range(80):
        moved = False
        for i, a in enumerate(movable):
            for b in movable[i + 1 :]:
                if separate_pair(a, b):
                    moved = True
        for p in others:
            clamp(p)
            eject_keepout(p)
        eject_holes()
        if sticky and pull_to_anchors():
            moved = True
        pin_locked_edges()
        clamp_electronics()
        if not moved:
            break

    overlaps_n = sum(
        1 for i, a in enumerate(movable) for b in movable[i + 1 :] if overlaps(a, b)
    )
    if overlaps_n > 0:
        warns += overlaps_n
        shown = 0
        for i, a in enumerate(movable):
            for b in movable[i + 1 :]:
                if not overlaps(a, b):
                    continue
                d = overlap_depth(a, b)
                print(f"  overlap {a.ref}/{b.ref} depth={d:.2f}", flush=True)
                shown += 1
                if shown >= 8:
                    break
            if shown >= 8:
                break
    if jack_row_overflow[0] > 0.05:
        warns += 1
        print(f"  WARN: N/S jack row overflow {jack_row_overflow[0]:.1f}mm (grow board)")
    ant_hits = sum(1 for p in others if in_keepout(p) > 0.05)
    disp_rms = disp_mean = disp_max = 0.0
    disp_ref = ""
    if sticky and anchors:
        ds = []
        for p in movable:
            rec = anchors.get(p.ref)
            if rec is None:
                continue
            d = math.hypot(p.x - rec[0], p.y - rec[1])
            ds.append((d, p.ref))
        if ds:
            disp_rms = (sum(d * d for d, _ in ds) / len(ds)) ** 0.5
            disp_mean = sum(d for d, _ in ds) / len(ds)
            disp_max, disp_ref = max(ds)
            print(
                f"  min-disp vs PCB: rms={disp_rms:.2f} mean={disp_mean:.2f} "
                f"max={disp_max:.2f}mm ({disp_ref})"
            )
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
        "disp_rms": disp_rms,
        "disp_max": disp_max,
    }
    tag = "min-disp" if sticky else "mincut+quad+force+GA+SA"
    print(
        f"Placement {cfg.board_w:.0f}x{cfg.board_h:.0f}: parts={len(movable)} "
        f"overlaps={overlaps_n} ant_hits={ant_hits} warns={warns} "
        f"cost={best_cost:.1f} cut={metrics['cut']:.1f} gap={cfg.gap} "
        f"[{tag}]"
    )
    return metrics
