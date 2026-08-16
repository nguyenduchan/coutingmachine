"""
Tube_L_Exit_Gate — rotary disc feeder kiểu SchanerDesigns short:
  https://www.youtube.com/shorts/ju5vIg66NNk

Kiến trúc (đáy HỞ — đĩa đẩy vật bằng lực tiếp tuyến):
  Rotor_Disc          — đĩa quay phẳng
  Bowl_Tube           — vành cố định (outer wall của lane)
  Crossbar_Bridge     — thanh ngang có slot, bắc qua đĩa, vít chỉnh từ TRÊN
  Inner_Lane_Rail     — cung Ø20 cm 7h→11h; trượt trên ray T của Chute_Slide
  Chute_Slide         — 2 thanh T nằm trên máng (8h / 10h), nối thành đĩa
  Exit_Track          — (đã bỏ — không máng trên đĩa)
  Bowl_Tube_Exit_Chute — máng nghiêng 40° có đáy, 9 giờ ra Front; cạnh trái
                        lòng máng trùng mép đĩa, thân máng luồn dưới đĩa

THAO TÁC CHỈNH:
  W: kéo Inner_Lane_Rail trượt trên 2 ray T (8h/10h)
  H: nâng/hạ cụm Entry_Gate_* ở đầu máng vào
"""
from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import FreeCAD as App
import Part

# ---------------------------------------------------------------------------
# Layout (mm). Disc top Z=0. CCW: at +X velocity ≈ +Y.
# Ref: SchanerDesigns rotary table + slotted crossbar + open-bottom guides.
# ---------------------------------------------------------------------------

from mech_common import *  # noqa: F401,F403

def make_inner_lane_arc_only() -> Part.Shape:
    """Chỉ cung 7h→11h (không con trượt, không dịch W) — kiểm tra không đụng ray T."""
    r_cline = INNER_LANE_ARC_R - 0.5 * RAIL_T
    h = CHUTE_WALL_H_MM
    th0 = INNER_LANE_CLOCK_TH0_DEG
    th1 = INNER_LANE_CLOCK_TH1_DEG
    n_arc = 48
    arc_pts: list[tuple[float, float]] = []
    for i in range(n_arc + 1):
        u = i / n_arc
        th = _deg2rad(th0 + (th1 - th0) * u)
        arc_pts.append((r_cline * math.cos(th), r_cline * math.sin(th)))
    wall = _thickened_path_wall(arc_pts, RAIL_T, GAP0, h)
    if not _shape_ok(wall, 40.0):
        wall = _wall_from_segments(arc_pts, RAIL_T, GAP0, h)
    return _enforce_disc_clearance(wall)


def make_inner_lane_rail_body(width_open: float) -> Part.Shape:
    """Cung Ø20 cm (7h→11h) + 2 con trượt T trên Chute_Slide; dịch +X theo W."""
    wall = make_inner_lane_arc_only()
    if not _shape_ok(wall, 40.0):
        return _enforce_disc_clearance(Part.Shape())
    for th_clk in (210.0, 150.0):
        try:
            shoe = make_chute_slide_shoe_at_clock(th_clk)
            fused = wall.fuse(shoe)
            if _shape_ok(fused, 0.5 * float(getattr(wall, "Volume", 1.0) or 1.0)):
                wall = fused
        except Exception:
            continue
    dx = inner_lane_slide_x(width_open)
    if abs(dx) > 1e-6:
        wall.translate(App.Vector(dx, 0.0, 0.0))
    return _enforce_disc_clearance(wall)


def make_reject_wiper(width_open: float) -> Part.Shape:
    """Reject tại tip Guide (θ=GUIDE_TH1) — verify trùng Guide_System."""
    _ = width_open
    r_i = GUIDE_R1
    th_tip = GUIDE_TH1
    th_a = _deg2rad(th_tip)
    jx = r_i * math.cos(th_a)
    jy = r_i * math.sin(th_a)
    th_dir = th_tip - 90.0 - REJECT_ANGLE_DEG
    ux = math.cos(_deg2rad(th_dir))
    uy = math.sin(_deg2rad(th_dir))
    r_att = r_i - 0.5 * GUIDE_T
    ax = r_att * math.cos(th_a)
    ay = r_att * math.sin(th_a)
    blade = _place_oriented_box(
        REJECT_LEN, REJECT_T, GUIDE_H,
        ax + 0.5 * REJECT_LEN * ux, ay + 0.5 * REJECT_LEN * uy, GAP0, th_dir,
    )
    join = _place_oriented_box(GUIDE_T + 3.0, GUIDE_T + 1.0, GUIDE_H, jx, jy, GAP0, th_tip - 90.0)
    keep = Part.makeCylinder(GUIDE_R1 + 0.2, GUIDE_H + 4.0, App.Vector(0, 0, GAP0 - 1.0))
    return _refine(blade.fuse(join).common(keep))


def make_inner_lane_rail(width_open: float) -> Part.Shape:
    """Cung DISC_R, 7h→11h. Reject nằm trong Guide_System cố định."""
    return _refine(make_inner_lane_rail_body(width_open))


