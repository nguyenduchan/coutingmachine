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


def make_guide_system() -> Part.Shape:
    """
    Guide_System cố định — một khối:
      • Xoắn chữ T hub → r = bowl−ENTRANCE_W (hở họng ENTRANCE_W với Bowl)
      • Tip kéo qua θ_mouth vào cung lane = tường trong lối vào (CCW thấy rõ)
      • Reject dính tip (inboard) — cùng khối, không khe
      • Cơ cấu giữ: 2 chân mount NẰM CAO (từ H_MAX+GAP0 lên đỉnh Guide_System,
        tức z≈28.5–34.5mm) nối xuyên tâm ra Bowl_Tube — cao hơn hẳn viên thuốc
        cao nhất (H_MAX=26mm) nên KHÔNG chặn đường viên đi trong khe hở
        ENTRANCE_W giữa Guide_System/Bowl_Tube; đĩa (z≤0) ở rất xa phía dưới nên
        không thể chạm. (Mount qua tâm — post xuyên xuống dưới đĩa — KHÔNG khả
        thi: đĩa là khối đặc bán kính 100mm ở z=[-15,0], không có khe hở nào
        ngoài lỗ trục Ø8mm ở chính giữa.)
    Lực đĩa = tiếp tuyến; Guide đứng yên → vật trượt ra vành rồi vào họng.
    """
    blade = _spiral_tee_wall(
        GUIDE_R0, GUIDE_R1, GUIDE_TH0, GUIDE_TH1,
        GUIDE_T, GUIDE_FLANGE_W, GUIDE_FLANGE_T, GAP0, GUIDE_H, n=72,
    )
    th_n = _deg2rad(GUIDE_TH0)
    cx, cy = GUIDE_R0 * math.cos(th_n), GUIDE_R0 * math.sin(th_n)
    nose = _cyl_z(GUIDE_T + 6.0, GUIDE_H, cx, cy, GAP0)
    hub = _cyl_z(DIR_HUB_D, GUIDE_H, 0.0, 0.0, GAP0)
    hub = hub.cut(_cyl_z(HUB_D + 2.0, GUIDE_H + 2.0, 0.0, 0.0, GAP0 - 1.0))
    # Chan mount ra Bowl_Tube — dat CAO (z tu H_MAX+GAP0 toi dinh Guide_System),
    # han han moi vien thuoc (cao toi da H_MAX) nen khong bao gio can duong.
    mount_z0 = GAP0 + H_MAX + 2.0  # 28.5mm — an toan tren moi vien
    mount_h = (GAP0 + GUIDE_H) - mount_z0  # toi dinh Guide_System (~34.5mm)
    mount_feet = []
    for u_ft in (0.30, 0.70):
        th_ft = GUIDE_TH0 + (GUIDE_TH1 - GUIDE_TH0) * u_ft
        r_wall = GUIDE_R0 + (GUIDE_R1 - GUIDE_R0) * u_ft
        r_mid = 0.5 * (r_wall + BOWL_IR)
        foot = _place_oriented_box(
            (BOWL_IR - r_wall) + 4.0, GUIDE_T + 1.0, max(2.0, mount_h),
            r_mid * math.cos(_deg2rad(th_ft)), r_mid * math.sin(_deg2rad(th_ft)),
            mount_z0, th_ft,
        )
        mount_feet.append(foot)
    gusset = _place_oriented_box(
        GUIDE_R0 - 2.0, GUIDE_T + 2.0, GUIDE_H,
        0.5 * (GUIDE_R0 + 2.0) * math.cos(th_n),
        0.5 * (GUIDE_R0 + 2.0) * math.sin(th_n),
        GAP0,
        GUIDE_TH0,
    )
    u_br = 0.40
    th_br = GUIDE_TH0 + (GUIDE_TH1 - GUIDE_TH0) * u_br
    r_br = GUIDE_R0 + (GUIDE_R1 - GUIDE_R0) * u_br
    brace = _place_oriented_box(
        max(8.0, r_br - 6.0), GUIDE_T + 1.0, GUIDE_H * 0.55,
        0.5 * (r_br + 6.0) * math.cos(_deg2rad(th_br)),
        0.5 * (r_br + 6.0) * math.sin(_deg2rad(th_br)),
        GAP0 + GUIDE_H * 0.45,
        th_br,
    )
    # Reject tại tip Guide (upstream miệng) — inboard, không bịt họng ra Bowl
    th_tip = GUIDE_TH1
    r_att = GUIDE_R1 - 0.5 * GUIDE_T
    th_dir = th_tip - 90.0 - REJECT_ANGLE_DEG
    ux, uy = math.cos(_deg2rad(th_dir)), math.sin(_deg2rad(th_dir))
    ax = r_att * math.cos(_deg2rad(th_tip))
    ay = r_att * math.sin(_deg2rad(th_tip))
    reject = _place_oriented_box(
        REJECT_LEN, REJECT_T, GUIDE_H,
        ax + 0.5 * REJECT_LEN * ux, ay + 0.5 * REJECT_LEN * uy, GAP0, th_dir,
    )
    join_rej = _place_oriented_box(
        GUIDE_T + 3.0, GUIDE_T + 1.0, GUIDE_H,
        GUIDE_R1 * math.cos(_deg2rad(th_tip)),
        GUIDE_R1 * math.sin(_deg2rad(th_tip)),
        GAP0,
        th_tip - 90.0,
    )
    rej_keep = Part.makeCylinder(
        GUIDE_R1 + 0.2, GUIDE_H + 4.0, App.Vector(0, 0, GAP0 - 1.0)
    )
    reject = _refine(reject.fuse(join_rej).common(rej_keep))
    body = blade.fuse(nose).fuse(hub).fuse(gusset).fuse(brace).fuse(reject)
    for foot in mount_feet:
        body = body.fuse(foot)
    body = _cut_m3_sites(body, guide_mount_sites())
    return _refine(body)


