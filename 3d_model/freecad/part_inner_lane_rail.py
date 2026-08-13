"""
Tube_L_Exit_Gate — rotary disc feeder kiểu SchanerDesigns short:
  https://www.youtube.com/shorts/ju5vIg66NNk

Kiến trúc (đáy HỞ — đĩa đẩy vật bằng lực tiếp tuyến):
  Rotor_Disc          — đĩa quay phẳng
  Bowl_Tube           — vành cố định (outer wall của lane)
  Crossbar_Bridge     — thanh ngang có slot, bắc qua đĩa, vít chỉnh từ TRÊN
  Inner_Lane_Rail     — tường liên tục + Reject_Wiper dính đầu (cùng dịch W)
  Height_Scraper      — lưỡi 2 mm + thành đầu vào 30×10×2 mm; H chỉnh 2–26 mm
  Funnel_Guide        — (cũ) → Center_Director: lưỡi cày TÂM đĩa, ép vật ra vành
  Outer_Rim_Funnel    — cánh ngoài thu hẹp vào lane
  Exit_Track          — máng 25 mm sát cuối lane; θ=180° đổ −Y ra Front

THAO TÁC CHỈNH (tay với từ trên — giống video):
  W: nới vít trên Crossbar → kéo clamp + Inner_Lane_Rail xuyên tâm
     vào tâm = W↑ | ra vành = W↓ | 1 mm = 1 mm W
  H: nới vít đứng trên clamp → nâng/hạ Height_Scraper
     lên = H↑ | xuống = H↓ | 1 mm = 1 mm H
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

def make_inner_lane_rail_body(width_open: float) -> Part.Shape:
    """Tường lane liên tục: cung + nối G1 xuyên miệng bát chồng máng ra."""
    geo = lane_exit_join_geo(width_open)
    # Cung: Face mượt. Đoạn Hermite: hộp (Face OCC hay nát ở vài W).
    wall = _thickened_path_wall(geo["arc_pts"], RAIL_T, GAP0, RAIL_H)
    if not _shape_ok(wall, 40.0):
        wall = _wall_from_segments(geo["arc_pts"], RAIL_T, GAP0, RAIL_H)
    join_pts = geo["blend_pts"] + geo["straight_pts"][:8]
    try:
        jw = _wall_from_segments(join_pts, RAIL_T, GAP0, RAIL_H)
        fused = wall.fuse(jw)
        if _shape_ok(fused, 0.5 * float(getattr(wall, "Volume", 1.0) or 1.0)):
            wall = fused
    except Exception:
        pass
    # Khóa miệng (cùng tâm Exit_Track) — không cắt bát kẻo OCC nuốt đoạn nối
    try:
        fused = wall.fuse(_join_seal_key(width_open, RAIL_T, RAIL_H))
        if _shape_ok(fused, 0.7 * float(getattr(wall, "Volume", 1.0) or 1.0)):
            wall = fused
    except Exception:
        pass
    # Cắt bao an toàn quanh đường đi thật của viên tại khuỷu (xem
    # _rail_pill_clearance_cut) — chặn triệt để jam_pill_vs_L ở mọi W.
    try:
        trimmed = wall.cut(_rail_pill_clearance_cut(width_open))
        if _shape_ok(trimmed, 0.5 * float(getattr(wall, "Volume", 1.0) or 1.0)):
            wall = trimmed
    except Exception:
        pass
    # Tỉa flash xuyên vành NGOÀI cửa ra (khối cung đơn — vững hơn cut(tube))
    try:
        flash = _annular_sector(
            BOWL_IR - 0.25,
            BOWL_OR + 0.4,
            THETA_EXIT_DEG + 52.0,
            THETA_EXIT_DEG - 54.0 + 360.0,
            GAP0 - 1.0,
            H_MAX + 16.0,
            n=28,
        )
        trimmed = wall.cut(flash)
        if _shape_ok(trimmed, 0.65 * float(getattr(wall, "Volume", 1.0) or 1.0)):
            wall = trimmed
    except Exception:
        pass
    return _refine(wall) if _shape_ok(wall, 40.0) else wall


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
    """Tường lane (cung + uốn exit). Reject nằm trong Guide_System cố định."""
    return _refine(make_inner_lane_rail_body(width_open))


