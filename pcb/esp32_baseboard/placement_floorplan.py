#!/usr/bin/env python3
"""Traditional cluster floorplan for esp32_baseboard.

Algorithms:
  1) Force-directed (spring-electrical) on cluster centers
  2) Simulated annealing polish — COM offset, quadrant CV, overlaps, gaps
  3) Within-cluster even packing — AXIS row, POWER column, HMI pack, OPTO strip
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple

CLUSTER_SIZE: Dict[str, Tuple[float, float]] = {
    "POWER": (44.0, 28.0),  # J1→D3→F1→+12V OUT rectangle (+ RC SNS)
    "BUCK": (26.0, 22.0),   # MP1584 U2 alone — near MCU
    "MCU": (30.0, 65.0),
    "TMC": (28.0, 32.0),
    "OPTO": (30.0, 40.0),  # on-carrier PC817×4 ~26×34 + margin
    "HMI": (36.0, 42.0),
    "BUP": (12.0, 20.0),
    "BLOWER": (28.0, 14.0),
    "SHIFT": (34.0, 66.0),
    "A1": (34.0, 38.0),
    "A2": (34.0, 38.0),
    "A3": (34.0, 38.0),
}

ANCHOR: Dict[str, Tuple[float, float, float]] = {
    "POWER": (0.12, 0.72, 3.0),
    "BUCK": (0.42, 0.52, 3.5),
    "MCU": (0.66, 0.50, 4.0),
    "TMC": (0.40, 0.58, 2.0),
    "OPTO": (0.36, 0.22, 2.5),
    "HMI": (0.88, 0.14, 3.0),
    "BUP": (0.08, 0.10, 2.0),
    "BLOWER": (0.26, 0.10, 2.0),
    "SHIFT": (0.88, 0.58, 3.5),
    "A1": (0.36, 0.88, 2.5),
    "A2": (0.52, 0.88, 2.5),
    "A3": (0.68, 0.88, 2.5),
}

ATTRACT = [
    ("POWER", "TMC", 1.5),
    ("POWER", "A1", 0.6),
    ("POWER", "BUCK", 1.2),
    ("BUCK", "MCU", 3.5),
    ("POWER", "OPTO", 0.8),
    ("POWER", "BLOWER", 0.8),
    ("POWER", "BUP", 0.8),
    ("MCU", "SHIFT", 2.5),
    ("MCU", "HMI", 1.5),
    ("MCU", "TMC", 1.0),
    ("MCU", "OPTO", 0.8),
    ("A1", "A2", 2.0),
    ("A2", "A3", 2.0),
    ("A1", "OPTO", 0.6),
    ("BUP", "BLOWER", 1.0),
    ("SHIFT", "HMI", 0.5),
]


@dataclass
class Box:
    x0: float
    y0: float
    w: float
    h: float

    @property
    def x1(self) -> float:
        return self.x0 + self.w

    @property
    def y1(self) -> float:
        return self.y0 + self.h

    @property
    def cx(self) -> float:
        return self.x0 + self.w / 2

    @property
    def cy(self) -> float:
        return self.y0 + self.h / 2

    def area(self) -> float:
        return self.w * self.h


def _overlap(a: Box, b: Box, gap: float) -> Tuple[float, float]:
    raw_ox = min(a.x1, b.x1) - max(a.x0, b.x0)
    raw_oy = min(a.y1, b.y1) - max(a.y0, b.y0)
    if raw_ox > 0 and raw_oy > 0:
        return raw_ox + gap, raw_oy + gap
    if raw_ox > 0:
        gy = max(a.y0, b.y0) - min(a.y1, b.y1)
        if 0 < gy < gap:
            return 0.0, gap - gy
        return 0.0, 0.0
    if raw_oy > 0:
        gx = max(a.x0, b.x0) - min(a.x1, b.x1)
        if 0 < gx < gap:
            return gap - gx, 0.0
        return 0.0, 0.0
    return 0.0, 0.0


def _project(boxes, ix0, iy0, ix1, iy1, gap, mcu_clear):
    for k, b in boxes.items():
        b.x0 = min(max(b.x0, ix0), ix1 - b.w)
        b.y0 = min(max(b.y0, iy0), iy1 - b.h)

    m = boxes["MCU"]
    kx0, ky0 = m.x0 - mcu_clear, m.y0 - mcu_clear
    kx1, ky1 = m.x1 + mcu_clear, m.y1 + mcu_clear
    for k, b in boxes.items():
        if k == "MCU":
            continue
        ox = min(b.x1, kx1) - max(b.x0, kx0)
        oy = min(b.y1, ky1) - max(b.y0, ky0)
        if ox <= 0 or oy <= 0:
            continue
        if ox < oy:
            b.x0 = kx0 - b.w if b.cx < m.cx else kx1
        else:
            b.y0 = ky0 - b.h if b.cy < m.cy else ky1
        b.x0 = min(max(b.x0, ix0), ix1 - b.w)
        b.y0 = min(max(b.y0, iy0), iy1 - b.h)

    keys = list(boxes.keys())
    for _ in range(8):
        moved = False
        for i, ka in enumerate(keys):
            for kb in keys[i + 1 :]:
                a, b = boxes[ka], boxes[kb]
                ox = min(a.x1, b.x1) - max(a.x0, b.x0)
                oy = min(a.y1, b.y1) - max(a.y0, b.y0)
                if ox > 0 and oy > 0:
                    if ox <= oy:
                        push = ox / 2 + 0.05
                        if ka != "MCU":
                            a.x0 -= push
                        if kb != "MCU":
                            b.x0 += push
                    else:
                        push = oy / 2 + 0.05
                        if ka != "MCU":
                            a.y0 -= push
                        if kb != "MCU":
                            b.y0 += push
                    moved = True
                    continue
                if ox > 0:
                    gy = max(a.y0, b.y0) - min(a.y1, b.y1)
                    if 0 < gy < gap:
                        push = (gap - gy) / 2
                        if a.cy < b.cy:
                            if ka != "MCU":
                                a.y0 -= push
                            if kb != "MCU":
                                b.y0 += push
                        else:
                            if ka != "MCU":
                                a.y0 += push
                            if kb != "MCU":
                                b.y0 -= push
                        moved = True
                elif oy > 0:
                    gx = max(a.x0, b.x0) - min(a.x1, b.x1)
                    if 0 < gx < gap:
                        push = (gap - gx) / 2
                        if a.cx < b.cx:
                            if ka != "MCU":
                                a.x0 -= push
                            if kb != "MCU":
                                b.x0 += push
                        else:
                            if ka != "MCU":
                                a.x0 += push
                            if kb != "MCU":
                                b.x0 -= push
                        moved = True
        for k, b in boxes.items():
            b.x0 = min(max(b.x0, ix0), ix1 - b.w)
            b.y0 = min(max(b.y0, iy0), iy1 - b.h)
        if not moved:
            break


def _cost(boxes, ix0, iy0, ix1, iy1, gap, bcx, bcy):
    keys = list(boxes.keys())
    at = sum(b.area() for b in boxes.values())
    comx = sum(b.cx * b.area() for b in boxes.values()) / at
    comy = sum(b.cy * b.area() for b in boxes.values()) / at
    cost = 2.5 * ((comx - bcx) ** 2 + (comy - bcy) ** 2)
    q = {"NW": 0.0, "NE": 0.0, "SW": 0.0, "SE": 0.0}
    for b in boxes.values():
        qn = ("N" if b.cy < bcy else "S") + ("W" if b.cx < bcx else "E")
        q[qn] += b.area()
    mean = sum(q.values()) / 4
    if mean:
        cv = (sum((v - mean) ** 2 for v in q.values()) / 4) ** 0.5 / mean
        cost += 8000.0 * cv
    for i, ka in enumerate(keys):
        for kb in keys[i + 1 :]:
            ox, oy = _overlap(boxes[ka], boxes[kb], gap)
            if ox > 0 and oy > 0:
                cost += 500.0 * ox * oy
            elif ox > 0:
                cost += 200.0 * ox
            elif oy > 0:
                cost += 200.0 * oy
    uw, uh = ix1 - ix0, iy1 - iy0
    for k, b in boxes.items():
        ax, ay, w = ANCHOR[k]
        tx, ty = ix0 + ax * uw, iy0 + ay * uh
        cost += w * ((b.cx - tx) ** 2 + (b.cy - ty) ** 2)
    for a, b, s in ATTRACT:
        da, db = boxes[a], boxes[b]
        dist = math.hypot(da.cx - db.cx, da.cy - db.cy)
        ideal = 0.5 * (math.hypot(da.w, da.h) + math.hypot(db.w, db.h)) + gap
        cost += s * (dist - ideal) ** 2 * 0.05
    return cost


def force_directed(boxes, ix0, iy0, ix1, iy1, gap, mcu_clear, steps=100):
    area = (ix1 - ix0) * (iy1 - iy0)
    k = math.sqrt(area / max(len(boxes), 1))
    keys = list(boxes.keys())
    uw, uh = ix1 - ix0, iy1 - iy0
    for t in range(steps):
        cool = 1.0 - t / steps
        disp = {name: [0.0, 0.0] for name in keys}
        for i, ka in enumerate(keys):
            for kb in keys[i + 1 :]:
                a, b = boxes[ka], boxes[kb]
                dx, dy = a.cx - b.cx, a.cy - b.cy
                d2 = dx * dx + dy * dy + 1e-3
                d = math.sqrt(d2)
                f = (k * k) / d
                fx, fy = f * dx / d, f * dy / d
                disp[ka][0] += fx
                disp[ka][1] += fy
                disp[kb][0] -= fx
                disp[kb][1] -= fy
        for a, b, s in ATTRACT:
            da, db = boxes[a], boxes[b]
            dx, dy = db.cx - da.cx, db.cy - da.cy
            d = math.hypot(dx, dy) + 1e-3
            f = (d * d) / k * 0.15 * s
            disp[a][0] += f * dx / d
            disp[a][1] += f * dy / d
            disp[b][0] -= f * dx / d
            disp[b][1] -= f * dy / d
        for name, b in boxes.items():
            ax, ay, w = ANCHOR[name]
            tx, ty = ix0 + ax * uw, iy0 + ay * uh
            disp[name][0] += 0.08 * w * (tx - b.cx)
            disp[name][1] += 0.08 * w * (ty - b.cy)
        for name, b in boxes.items():
            pin = 0.15 if name == "MCU" else 1.0
            dx, dy = disp[name]
            lim = 8.0 * cool
            mag = math.hypot(dx, dy) + 1e-9
            scale = min(lim, mag) / mag * pin * cool
            b.x0 += dx * scale
            b.y0 += dy * scale
        _project(boxes, ix0, iy0, ix1, iy1, gap, mcu_clear)


def anneal(boxes, ix0, iy0, ix1, iy1, gap, mcu_clear, bcx, bcy, iters=1200, seed=42):
    rng = random.Random(seed)
    keys = [k for k in boxes if k != "MCU"]
    best = {k: Box(b.x0, b.y0, b.w, b.h) for k, b in boxes.items()}
    best_c = _cost(boxes, ix0, iy0, ix1, iy1, gap, bcx, bcy)
    cur_c = best_c
    t0 = 400.0
    for i in range(iters):
        t = t0 * (1.0 - i / iters)
        k = rng.choice(keys)
        b = boxes[k]
        ox, oy = b.x0, b.y0
        b.x0 += rng.uniform(-6, 6)
        b.y0 += rng.uniform(-6, 6)
        _project(boxes, ix0, iy0, ix1, iy1, gap, mcu_clear)
        if k in ("A1", "A2", "A3"):
            y = boxes["A1"].y0
            boxes["A1"].y0 = boxes["A2"].y0 = boxes["A3"].y0 = y
        nc = _cost(boxes, ix0, iy0, ix1, iy1, gap, bcx, bcy)
        d = nc - cur_c
        if d < 0 or rng.random() < math.exp(-d / max(t, 1e-3)):
            cur_c = nc
            if nc < best_c:
                best_c = nc
                best = {kk: Box(bb.x0, bb.y0, bb.w, bb.h) for kk, bb in boxes.items()}
        else:
            b.x0, b.y0 = ox, oy
    for k, b in best.items():
        boxes[k].x0, boxes[k].y0 = b.x0, b.y0
    _project(boxes, ix0, iy0, ix1, iy1, gap, mcu_clear)
    return best_c


def _even_axis_row(boxes, ix0, ix1, gap):
    axes = ["A1", "A2", "A3"]
    widths = [boxes[a].w for a in axes]
    right = boxes["SHIFT"].x0 - gap
    left = ix0 + 4.0
    # Extra margin: Eco outlines (ULN module courtyard) bleed past cluster AABB
    span_left = max(left, boxes["POWER"].x1 + gap + 6.0)
    avail = right - span_left
    total_w = sum(widths)
    if avail < total_w + 2 * gap:
        span_left = max(left, right - total_w - 2 * gap)
        avail = right - span_left
    slack = max(0.0, avail - total_w)
    g = max(slack / 2.0 if slack else gap, gap)
    y = min(boxes[a].y0 for a in axes)
    # Snap AXIS to south usable band
    y = max(y, boxes["MCU"].y1 + gap)
    x = span_left
    for a, w in zip(axes, widths):
        boxes[a].x0 = x
        boxes[a].y0 = y
        x += w + g


def _fp_from_boxes(
    ox, oy, ix0, iy0, ix1, iy1,
    boxes, cluster_gap, mcu_clear, cost=0.0, *, r4_north=False,
):
    """Map cluster boxes → footprint anchors (shared by SA + compact layouts)."""
    m, p, t, o = boxes["MCU"], boxes["POWER"], boxes["TMC"], boxes["OPTO"]
    h, s = boxes["HMI"], boxes["SHIFT"]
    a1, a2, a3 = boxes["A1"], boxes["A2"], boxes["A3"]
    bup, blw = boxes["BUP"], boxes["BLOWER"]
    bk = boxes["BUCK"]

    # POWER protect rectangle only: J1@90 → D3@0 → F1@0 → +12V OUT east
    _tb = 5.0
    _fuse_half = 11.25
    _d_half = 3.75
    _gap = 2.0
    jx = p.x0 + 5.0
    jy = p.y0 + 9.5
    rail_y = jy - _tb / 2.0
    d3x = jx + 4.0 + _gap + _d_half
    d3y = rail_y
    f1x = d3x + _d_half + _gap + _fuse_half
    f1y = rail_y
    d1x = f1x + _fuse_half
    d1y = rail_y + 8.0
    # RC SNS stays with POWER (row under protect strip), not with 5V buck
    r10y = min(p.y1 - 3.5, max(d1y + 5.5, rail_y + 10.0))
    r10x = p.x0 + 8.0
    c10x, c10y = r10x + 7.0, r10y

    # BUCK U2 — own Eco, pack centered (near MCU west)
    mx, my = bk.cx, bk.cy

    # OPTO on-carrier (was M2): 4-col stack — dy matches gen_submodules.M2_HDR_DY
    opto_hdr_dy = 30.0
    opto_ox = o.x0 + 1.0
    opto_oy = o.y0 + 1.0

    j3x = min(h.x1 - 8.0, s.x0 - cluster_gap - 6.0, ix1 - 14.0)
    j3y = max(h.y0 + 8.0, oy + 20.0)
    j18x = min(j3x - 12.0, h.x0 + max(3.0, h.w * 0.35))
    j18x = max(j18x, h.x0 + 3.0)
    j18y = max(h.y0 + 10.0, j3y + 2.0)
    j15x = (j18x + j3x) / 2.0
    j15y = j3y

    mod_ctrl_to_q = 17.0
    # Prefer Q at east edge so SHIFT Eco stays far from HMI/MCU.
    u10_q_x = min(s.x1 - 4.0, ix1 - 6.0)
    u10_ctrl_x = u10_q_x - mod_ctrl_to_q
    if u10_ctrl_x < s.x0 + 2.0:
        u10_ctrl_x = s.x0 + 2.0
        u10_q_x = u10_ctrl_x + mod_ctrl_to_q
    u10_y0 = s.y0 + 3.0

    if r4_north:
        r4x = (u10_ctrl_x + u10_q_x) / 2.0
        r4y = u10_y0 - 7.0
    else:
        hmi_south_est = j18y + 33.0
        min_u10 = hmi_south_est + cluster_gap + 2.0
        ox_hs = min(h.x1, s.x1) - max(h.x0, s.x0)
        if ox_hs > 0 and u10_y0 < min_u10 and min_u10 + 58.0 <= iy1:
            u10_y0 = min_u10
            s.y0 = u10_y0 - 3.0
        r4x = (u10_ctrl_x + u10_q_x) / 2.0
        r4y = u10_y0 + 23 * 2.54 + 6.0
        if r4y + 4.0 > iy1:
            u10_y0 = max(s.y0 + 3.0, iy1 - (23 * 2.54 + 10.0))
            r4y = u10_y0 + 23 * 2.54 + 6.0

    u5x, u5y = a1.cx + 2.0, a1.y1 - 14.0
    u6x, u6y = a2.cx + 2.0, a2.y1 - 14.0
    u7x, u7y = a3.cx + 2.0, a3.y1 - 14.0
    _dip_y = u5y

    # Nudge TMC inside west column (centered); do not push east into MCU
    tx = t.cx
    ty = t.cy

    return {
        "cost": cost,
        "boxes": {k: (b.x0, b.y0, b.x1, b.y1) for k, b in boxes.items()},
        "mcu_wx0": m.x0,
        "mcu_wy0": m.y0,
        "jx": jx,
        "jy": jy,
        "d3x": d3x,
        "d3y": d3y,
        "f1x": f1x,
        "f1y": f1y,
        "d1x": d1x,
        "d1y": d1y,
        "d3_rot": 0,
        "f1_rot": 0,
        "d1_rot": 270,  # K north → +12V OUT, A south → GND
        "j31ax": opto_ox,
        "j31ay": opto_oy,
        "j31bx": opto_ox,
        "j31by": opto_oy + opto_hdr_dy,
        "j31x": opto_ox,
        "j31y": opto_oy,
        "j31_rot": 90,  # dual horizontal rows (pin1 west)
        "mx": mx,
        "my": my,
        "r10x": r10x,
        "r10y": r10y,
        "c10x": c10x,
        "c10y": c10y,
        "tx": tx,
        "ty": ty,
        "opto_origin": (opto_ox, opto_oy),
        "j3x": j3x,
        "j3y": j3y,
        "j18x": j18x,
        "j18y": j18y,
        "j15x": j15x,
        "j15y": j15y,
        "j16x": blw.cx,
        "j16y": blw.y0 + 3.0,
        "j14x": bup.cx,
        "j14y": bup.y0 + 2.0,
        "u5x": u5x,
        "u5y": u5y,
        "u6x": u6x,
        "u6y": u6y,
        "u7x": u7x,
        "u7y": u7y,
        "_dip_y": _dip_y,
        "u10_ctrl_x": u10_ctrl_x,
        "u10_q_x": u10_q_x,
        "u10_y0": u10_y0,
        "r4x": r4x,
        "r4y": r4y,
        "c21x": u5x - 14.0,
        "c21y": _dip_y - 8.0,
        "MOD_CTRL_TO_Q": mod_ctrl_to_q,
    }


def compact_placement_170x150(
    ox, oy, bw, bh,
    edge_clear=10.0, cluster_gap=8.0, mcu_clear=10.0, seed=42,
    layout_bh=None,
):
    """Hand floorplan for ~180×150–155 (E11 gaps).

    Width is too tight for POWER|BUCK|MCU|HMI|SHIFT in one row, so:
      West column (Y-stack): TMC → BUCK → POWER; AXIS south
      Mid: MCU; East: HMI | SHIFT
      North: BUP above MCU; OPTO east of MCU; BLOWER NE

    layout_bh: if set, place modules as on that taller board so shrinking
    Edge.Cuts (bh) does not move cluster XY (must still clear E11.10).
    """
    del seed
    g = 8.0
    bh_place = float(layout_bh) if layout_bh is not None else float(bh)
    ix0, iy0 = ox + edge_clear, oy + edge_clear
    ix1 = ox + bw - edge_clear
    iy1 = oy + bh_place - edge_clear  # freeze Y stack to layout_bh
    iy1_board = oy + bh - edge_clear

    pw_w, pw_h = 44.0, 28.0  # J1→D3→F1 protect rectangle (+ RC SNS)
    bk_w, bk_h = 26.0, 22.0  # U2 MP1584 alone (west column, near MCU Y)
    tm_w, tm_h = 30.0, 26.0  # C20/R2/C24 beside U3
    mc_w, mc_h = 30.0, 65.0
    hm_w, hm_h = 17.0, 42.0
    sh_w, sh_h = 22.0, 66.0
    ax_w, ax_h = 26.0, 24.0  # HOME west/north of ULN; keep MCU Y budget
    bu_w, bu_h = 9.0, 17.0
    bl_w, bl_h = 24.0, 11.0
    op_w, op_h = 28.0, 36.0  # on-carrier PC817×4 (~26×34) + Eco margin


    # South AXIS
    ax_y0 = iy1 - ax_h
    ax_span = 3 * ax_w + 2 * g
    ax_x0 = ix0 + max(pw_w, bk_w, tm_w) + g
    if ax_x0 + ax_span > ix1 - sh_w - g:
        ax_x0 = max(ix0, ix1 - sh_w - g - ax_span)

    # SHIFT far east, Y-clear of AXIS
    sh_x0 = ix1 - sh_w
    sh_y0 = ax_y0 - g - sh_h

    # West column Y-stack: TMC → BUCK → POWER (BUCK near MCU without eating X corridor)
    y_bleed = 4.0
    axis_power_gap = g + 6.0
    pw_x0 = ix0
    pw_y1 = ax_y0 - axis_power_gap
    pw_y0 = pw_y1 - pw_h
    bk_x0 = ix0
    bk_y1 = pw_y0 - g
    bk_y0 = bk_y1 - bk_h
    tm_x0 = ix0
    tm_y1 = bk_y0 - g - y_bleed
    tm_y0 = max(iy0 + 2.0, tm_y1 - tm_h)
    if tm_y1 > bk_y0 - g:
        # Compress: keep POWER south, shrink bleed
        tm_y1 = bk_y0 - g
        tm_y0 = tm_y1 - tm_h
        if tm_y0 < iy0 + 2.0:
            tm_y0 = iy0 + 2.0
            tm_y1 = tm_y0 + tm_h
            bk_y0 = tm_y1 + g
            bk_y1 = bk_y0 + bk_h
            pw_y0 = bk_y1 + g
            pw_y1 = pw_y0 + pw_h
            if pw_y1 > ax_y0 - axis_power_gap:
                pw_y1 = ax_y0 - axis_power_gap
                pw_y0 = pw_y1 - pw_h

    # MCU east of west column (BUCK shares west X — no extra corridor width)
    west_x1 = max(pw_x0 + pw_w, tm_x0 + tm_w, bk_x0 + bk_w)
    mc_x0 = west_x1 + g + 6.0
    mc_x1_cap = sh_x0 - mcu_clear
    if mc_x0 + mc_w > mc_x1_cap:
        mc_w = max(28.0, mc_x1_cap - mc_x0)

    # BLOWER far NE; OPTO east of MCU (no X-overlap with DevKit Eco)
    bl_x0 = ix1 - bl_w - 2.0  # footprint AABB bleed past Eco
    bl_y0 = iy0
    bu_x0, bu_y0 = mc_x0, iy0
    op_x0 = mc_x0 + mc_w + 8.0
    op_y0 = iy0
    op_w = min(op_w, bl_x0 - g - op_x0)
    if op_x0 + op_w + g > bl_x0:
        op_w = max(24.0, bl_x0 - g - op_x0)

    # HMI west of SHIFT, *south* of OPTO (X-corridor too tight for side-by-side)
    hm_x0 = sh_x0 - g - hm_w
    hm_y0 = op_y0 + op_h + g
    if hm_y0 + hm_h > sh_y0 - 2.0:
        hm_h = max(28.0, sh_y0 - 2.0 - hm_y0)
    if hm_x0 < op_x0:
        hm_x0 = max(op_x0, sh_x0 - g - hm_w)

    if bl_x0 < hm_x0 + hm_w + g and bl_y0 + bl_h > hm_y0:
        bl_x0 = max(bl_x0, hm_x0 + hm_w + g)
    if bl_x0 + bl_w > ix1 - 1.0:
        bl_w = max(18.0, ix1 - 1.0 - bl_x0)
        bl_x0 = ix1 - bl_w
    if bl_y0 + bl_h + g > sh_y0:
        bl_y0 = max(iy0, sh_y0 - g - bl_h)
    # Keep OPTO clear of BLOWER after blower nudges
    if op_x0 + op_w + g > bl_x0 and bl_y0 < op_y0 + op_h:
        op_w = max(24.0, bl_x0 - g - op_x0)

    north_y1 = bu_y0 + bu_h
    op_overlaps_mcu_x = (op_x0 < mc_x0 + mc_w) and (mc_x0 < op_x0 + op_w)
    if op_overlaps_mcu_x:
        north_y1 = max(north_y1, op_y0 + op_h)
    bup_mcu_y = bu_y0 + bu_h + mcu_clear + 2.0
    mc_y0 = max(iy0 + 12.0, north_y1 + g + 2.0, bup_mcu_y)
    if op_overlaps_mcu_x:
        mc_y0 = max(mc_y0, op_y0 + op_h + mcu_clear + 2.0)
    max_mc_y1 = ax_y0 - 16.0
    if mc_y0 + mc_h > max_mc_y1:
        mc_h = max(48.0, max_mc_y1 - mc_y0)
        if mc_y0 + mc_h > max_mc_y1:
            mc_y0 = max(iy0 + 8.0, max_mc_y1 - mc_h)

    # Slide BUCK east toward MCU (E11.12 ≥ mcu_clear) for short +5V
    bk_x0 = mc_x0 - mcu_clear - bk_w
    bk_x0 = max(ix0, bk_x0)
    prefer_y = max(tm_y1 + g, min(mc_y0 + 10.0, mc_y0 + mc_h - bk_h - 2.0))
    if prefer_y + bk_h <= pw_y0 - g:
        bk_y0 = prefer_y

    boxes = {
        "POWER": Box(pw_x0, pw_y0, pw_w, pw_h),
        "BUCK": Box(bk_x0, bk_y0, bk_w, bk_h),
        "MCU": Box(mc_x0, mc_y0, mc_w, mc_h),
        "TMC": Box(tm_x0, tm_y0, tm_w, tm_h),
        "OPTO": Box(op_x0, op_y0, op_w, op_h),
        "HMI": Box(hm_x0, hm_y0, hm_w, hm_h),
        "BUP": Box(bu_x0, bu_y0, bu_w, bu_h),
        "BLOWER": Box(bl_x0, bl_y0, bl_w, bl_h),
        "SHIFT": Box(sh_x0, sh_y0, sh_w, sh_h),
        "A1": Box(ax_x0, ax_y0, ax_w, ax_h),
        "A2": Box(ax_x0 + ax_w + g, ax_y0, ax_w, ax_h),
        "A3": Box(ax_x0 + 2 * (ax_w + g), ax_y0, ax_w, ax_h),
    }
    for b in boxes.values():
        b.x0 = min(max(b.x0, ix0), ix1 - b.w)
        # Clamp to layout Y (frozen), not the possibly shorter board — E11.10
        # still enforces real Eco vs Edge.Cuts on the shrunk board.
        b.y0 = min(max(b.y0, iy0), iy1 - b.h)
        if b.y1 > iy1_board + edge_clear:
            # Soft warn only in debug; keep pose
            pass

    return _fp_from_boxes(
        ox, oy, ix0, iy0, ix1, iy1_board, boxes, 8.0, mcu_clear, cost=0.0, r4_north=True,
    )


def balanced_placement(
    ox, oy, bw, bh,
    edge_clear=10.0, cluster_gap=8.0, mcu_clear=10.0, seed=42,
    layout_bh=None,
):
    # Dense hand layout for compact carrier (≤180×155).
    if bw <= 185.0 and bh <= 155.0:
        return compact_placement_170x150(
            ox, oy, bw, bh,
            edge_clear=edge_clear,
            cluster_gap=cluster_gap,
            mcu_clear=mcu_clear,
            seed=seed,
            layout_bh=layout_bh,
        )

    ix0, iy0 = ox + edge_clear, oy + edge_clear
    ix1, iy1 = ox + bw - edge_clear, oy + bh - edge_clear
    bcx, bcy = (ix0 + ix1) / 2, (iy0 + iy1) / 2
    uw, uh = ix1 - ix0, iy1 - iy0

    boxes = {}
    for name, (w, h) in CLUSTER_SIZE.items():
        ax, ay, _ = ANCHOR[name]
        cx, cy = ix0 + ax * uw, iy0 + ay * uh
        boxes[name] = Box(cx - w / 2, cy - h / 2, w, h)

    mw, mh = CLUSTER_SIZE["MCU"]
    boxes["MCU"] = Box(ix0 + 0.55 * uw - mw / 2, iy0 + 0.42 * uh - mh / 2, mw, mh)
    _project(boxes, ix0, iy0, ix1, iy1, cluster_gap, mcu_clear)
    force_directed(boxes, ix0, iy0, ix1, iy1, cluster_gap, mcu_clear, steps=100)
    cost = anneal(boxes, ix0, iy0, ix1, iy1, cluster_gap, mcu_clear, bcx, bcy, seed=seed)
    _even_axis_row(boxes, ix0, ix1, cluster_gap)
    m, s = boxes["MCU"], boxes["SHIFT"]
    min_sx = m.x1 + mcu_clear + 2.0
    if s.x0 < min_sx:
        s.x0 = min(min_sx, ix1 - s.w)
    _project(boxes, ix0, iy0, ix1, iy1, cluster_gap, mcu_clear)

    return _fp_from_boxes(
        ox, oy, ix0, iy0, ix1, iy1, boxes, cluster_gap, mcu_clear, cost=cost,
    )


if __name__ == "__main__":
    p = balanced_placement(35.0, 30.0, 220.0, 160.0)
    print(f"cost={p['cost']:.1f}")
    for k, box in p["boxes"].items():
        print(f"  {k:7s} {box}")
