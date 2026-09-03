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
    "POWER": (34.0, 76.0),
    "MCU": (30.0, 65.0),
    "TMC": (28.0, 32.0),
    "OPTO": (52.0, 28.0),
    "HMI": (36.0, 42.0),
    "BUP": (12.0, 20.0),
    "BLOWER": (28.0, 14.0),
    "SHIFT": (34.0, 66.0),
    "A1": (34.0, 24.0),
    "A2": (28.0, 24.0),
    "A3": (28.0, 24.0),
}

ANCHOR: Dict[str, Tuple[float, float, float]] = {
    "POWER": (0.12, 0.68, 3.0),
    "MCU": (0.66, 0.50, 4.0),
    "TMC": (0.40, 0.58, 2.0),
    "OPTO": (0.36, 0.22, 2.5),
    "HMI": (0.88, 0.16, 3.0),
    "BUP": (0.08, 0.10, 2.0),
    "BLOWER": (0.26, 0.10, 2.0),
    "SHIFT": (0.88, 0.55, 3.5),
    "A1": (0.28, 0.90, 2.5),
    "A2": (0.44, 0.90, 2.5),
    "A3": (0.58, 0.90, 2.5),
}

ATTRACT = [
    ("POWER", "TMC", 1.5),
    ("POWER", "A1", 1.2),
    ("POWER", "OPTO", 1.0),
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
    span_left = max(left, boxes["POWER"].x1 + gap)
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


def balanced_placement(
    ox, oy, bw, bh,
    edge_clear=10.0, cluster_gap=8.0, mcu_clear=10.0, seed=42,
):
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
    # Pin SHIFT east of MCU keepout (actual Eco often wider than estimate)
    m, s = boxes["MCU"], boxes["SHIFT"]
    min_sx = m.x1 + mcu_clear + 2.0
    if s.x0 < min_sx:
        s.x0 = min(min_sx, ix1 - s.w)
    _project(boxes, ix0, iy0, ix1, iy1, cluster_gap, mcu_clear)

    m, p, t, o = boxes["MCU"], boxes["POWER"], boxes["TMC"], boxes["OPTO"]
    h, s = boxes["HMI"], boxes["SHIFT"]
    a1, a2, a3 = boxes["A1"], boxes["A2"], boxes["A3"]
    bup, blw = boxes["BUP"], boxes["BLOWER"]

    py0, py1 = p.y0 + 4.0, p.y1 - 4.0
    px = p.x0 + 8.0
    ys = [py0 + i * (py1 - py0) / 4.0 for i in range(5)]
    f1y, my, jy, rcy, d1y = ys

    opto_col_pitch = 12.0
    opto_ox = o.cx - 1.5 * opto_col_pitch
    opto_oy = o.cy

    j3x = h.x1 - 4.0
    j3y = h.y0 + 2.0
    j18x = max(h.x0 + 3.0, m.x1 + mcu_clear + 2.0)
    j18y = h.y0 + 6.0
    j15x = (j18x + j3x) / 2.0
    j15y = h.y0 + 2.0

    mod_ctrl_to_q = 17.0
    u10_ctrl_x = s.x0 + 3.0
    u10_q_x = u10_ctrl_x + mod_ctrl_to_q
    u10_y0 = s.y0 + 3.0
    if u10_q_x + 10.0 > ix1:
        u10_ctrl_x = ix1 - 10.0 - mod_ctrl_to_q
        u10_q_x = u10_ctrl_x + mod_ctrl_to_q
    # R4 (OE_595 pull-up) sits NORTH of both module headers: east of J25 it
    # overlapped the 1x24 courtyard, and the space between J24 and J25 is under
    # the 595 module body once it is plugged in.
    r4x = (u10_ctrl_x + u10_q_x) / 2.0
    r4y = u10_y0 - 7.0

    u5x, u5y = a1.cx, a1.cy
    u6x, u6y = a2.cx, a2.cy
    u7x, u7y = a3.cx, a3.cy
    _dip_y = u5y

    return {
        "cost": cost,
        "boxes": {k: (b.x0, b.y0, b.x1, b.y1) for k, b in boxes.items()},
        "mcu_wx0": m.x0,
        "mcu_wy0": m.y0,
        "jx": px,
        "jy": jy,
        "f1x": px + 8.0,
        "f1y": f1y,
        "d1x": px + 4.0,
        "d1y": d1y,
        "mx": px + 10.0,
        "my": my,
        "r10x": px + 12.0,
        "r10y": rcy,
        "c10x": px + 12.0,
        "c10y": rcy + 6.0,
        "tx": t.cx,
        "ty": t.cy,
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
        # C21 (shared ULN COM bulk): north of the DIP row, not west of it --
        # west it either hit the J5 courtyard or pushed A1 under the 8 mm
        # cluster gap to POWER.
        "c21x": u5x - 14.0,
        "c21y": _dip_y - 14.0,
        "MOD_CTRL_TO_Q": mod_ctrl_to_q,
    }


if __name__ == "__main__":
    p = balanced_placement(35.0, 30.0, 220.0, 160.0)
    print(f"cost={p['cost']:.1f}")
    for k, box in p["boxes"].items():
        print(f"  {k:7s} {box}")
