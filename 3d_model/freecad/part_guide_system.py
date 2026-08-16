"""
Tube_L_Exit_Gate — rotary disc feeder kiểu SchanerDesigns short:
  https://www.youtube.com/shorts/ju5vIg66NNk

Kiến trúc (đáy HỞ — đĩa đẩy vật bằng lực tiếp tuyến):
  Rotor_Disc          — đĩa quay phẳng
  Bowl_Tube           — vành cố định (outer wall của lane)
  Entry_Gate_*        — cửa chỉnh chiều cao ở đầu máng vào (trụ + trượt + barrier)
  Entry_Gate_Barrier  — barrier chữ L (trần 20 mm + tấm đứng 10 mm); H 2–26 mm
  Guide_System        — vòng tròn tâm Ø35 + MỘT vách thẳng tiếp tuyến
  Bowl_Tube_Exit_Chute — máng dốc 40° tại 9 giờ; cạnh trái lòng máng trùng mép đĩa

THAO TÁC CHỈNH (tay với từ trên — giống video):
  W: KHÔNG chỉnh được — luồng cố định = họng ra Guide_System (ENTRANCE_W)
  H: nới Screw_Gate_H → nâng/hạ cụm barrier trên ray T đứng ở đầu máng vào
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



def _spiral_wall(
    r0: float,
    r1: float,
    th0_deg: float,
    th1_deg: float,
    thick: float,
    z0: float,
    h: float,
    n: int = 48,
) -> Part.Shape:
    """Vertical wall along Archimedean spiral r(θ); open bottom (sits above disc)."""
    if r1 <= r0 + 1e-6 or h <= 1e-6 or abs(th1_deg - th0_deg) < 1e-6:
        return _box(0.1, 0.1, 0.1, 0, 0, z0)
    th0, th1 = _deg2rad(th0_deg), _deg2rad(th1_deg)
    n = max(12, int(n))
    half_t = 0.5 * thick
    pts_out, pts_in = [], []
    for i in range(n + 1):
        u = i / n
        th = th0 + (th1 - th0) * u
        r = r0 + (r1 - r0) * u
        c, s = math.cos(th), math.sin(th)
        pts_out.append(App.Vector((r + half_t) * c, (r + half_t) * s, z0))
        pts_in.append(App.Vector((r - half_t) * c, (r - half_t) * s, z0))
    wire = pts_out + list(reversed(pts_in))
    wire.append(wire[0])
    face = Part.Face(Part.makePolygon(wire))
    return _refine(face.extrude(App.Vector(0, 0, h)))


def _spiral_centerline_xy(
    r0: float, r1: float, th0_deg: float, th1_deg: float, n: int
) -> list[tuple[float, float]]:
    pts = []
    for i in range(n + 1):
        u = i / max(1, n)
        th = _deg2rad(th0_deg + (th1_deg - th0_deg) * u)
        r = r0 + (r1 - r0) * u
        pts.append((r * math.cos(th), r * math.sin(th)))
    return pts


def _spiral_tee_wall(
    r0: float,
    r1: float,
    th0_deg: float,
    th1_deg: float,
    web_t: float,
    flange_w: float,
    flange_t: float,
    z0: float,
    h: float,
    n: int = 48,
) -> Part.Shape:
    """
    Tường xoắn chữ T (web đứng + flange đỉnh) — chống uốn/rung tốt hơn tấm mỏng.
    Đáy hở (GAP0); flange nằm trên đỉnh web.
    """
    web = _spiral_wall(r0, r1, th0_deg, th1_deg, web_t, z0, h, n=n)
    if flange_w <= web_t + 0.5 or flange_t < 0.5:
        return web
    pts = _spiral_centerline_xy(r0, r1, th0_deg, th1_deg, n)
    flange = _thickened_path_wall(pts, flange_w, z0 + h - flange_t, flange_t)
    return _refine(web.fuse(flange))


def _cut_flat_at_theta(shape: Part.Shape, th_deg: float, span_deg: float = 150.0) -> Part.Shape:
    """Gọt phần nhô quá mặt xuyên tâm θ, để lại ĐẦU RA PHẲNG.

    Dùng QUẠT góc (θ, θ+span) chứ KHÔNG dùng nửa không gian: nửa không gian xoá
    luôn 180° và ăn mất cả vòng tròn tâm lẫn gốc xoắn ở θ≈250°. Quạt 150° đủ
    gọt phần nhô ở đầu ra mà không chạm hai chỗ đó.
    Chỉ áp cho VÁCH, không áp cho vòng tròn tâm.
    """
    try:
        cutter = _annular_sector(
            0.5, 4.0 * BOWL_OR, th_deg, th_deg + span_deg,
            -2.0 * GUIDE_H, 6.0 * (GAP0 + GUIDE_H), n=24,
        )
        cut = shape.cut(cutter)
        if _shape_ok(cut, 100.0):
            return cut
    except Exception:
        pass
    return shape


def make_guide_system() -> Part.Shape:
    """Guide_System cố định — hai phần:

      (1) VÒNG TRÒN ở tâm: Ø ngoài 50 mm, vành dày 2 mm (lòng Ø46 để trống)
      (2) VÁCH ĐỊNH HƯỚNG = XOẮN ARCHIMEDES (r tuyến tính theo θ), mọc từ đúng
          vòng tròn đó (GUIDE_R0 = 17.5) và quét ra tới khi ĐẦU RA cách mép đĩa
          đúng ENTRANCE_W = 20 mm (mặt ngoài ở r = 80). Đầu ra cắt PHẲNG bằng
          mặt xuyên tâm tại GUIDE_TH1.

    Bích chữ T trên đỉnh (z ≥ GAP0+H_MAX) chống rung cho vách 2 mm; hai chân
    mount ra Bowl_Tube cũng nằm cao hơn H_MAX nên không cản vật.
    Đáy HỞ tại GAP0 — không chạm mặt đĩa.
    """
    blade = _spiral_tee_wall(
        GUIDE_R0, GUIDE_R1, GUIDE_TH0, GUIDE_TH1,
        GUIDE_T, GUIDE_FLANGE_W, GUIDE_FLANGE_T, GAP0, GUIDE_H, n=72,
    )
    # ĐẦU RA PHẲNG — gọt TRƯỚC khi ghép vòng tròn, để vòng tròn còn nguyên 360°
    blade = _cut_flat_at_theta(blade, GUIDE_TH1)
    # VÒNG TRÒN TÂM HOÀN CHỈNH: khép kín 360°, không bị cắt bởi bất kỳ phép nào
    ring = _cyl_z(GUIDE_CIRCLE_D, GUIDE_H, 0.0, 0.0, GAP0)
    ring = ring.cut(_cyl_z(GUIDE_CIRCLE_ID, GUIDE_H + 2.0, 0.0, 0.0, GAP0 - 1.0))
    body = blade.fuse(ring)

    mount_z0 = GAP0 + H_MAX + 2.0
    mount_h = (GAP0 + GUIDE_H) - mount_z0
    for u_ft in (0.55, 0.95):
        th_ft = GUIDE_TH0 + (GUIDE_TH1 - GUIDE_TH0) * u_ft
        r_wall = GUIDE_R0 + (GUIDE_R1 - GUIDE_R0) * u_ft
        r_mid = 0.5 * (r_wall + BOWL_IR)
        foot = _place_oriented_box(
            (BOWL_IR - r_wall) + 4.0, GUIDE_T + 1.0, max(2.0, mount_h),
            r_mid * math.cos(_deg2rad(th_ft)), r_mid * math.sin(_deg2rad(th_ft)),
            mount_z0, th_ft,
        )
        body = body.fuse(foot)

    body = _cut_m3_sites(body, guide_mount_sites())
    return _refine(_enforce_disc_clearance(body))
