"""
Tube_L_Exit_Gate — rotary disc feeder kiểu SchanerDesigns short:
  https://www.youtube.com/shorts/ju5vIg66NNk

Kiến trúc (đáy HỞ — đĩa đẩy vật bằng lực tiếp tuyến):
  Rotor_Disc          — đĩa quay phẳng
  Bowl_Tube           — vành cố định (outer wall của lane)
  Entry_Gate_*        — cửa chỉnh chiều cao ở đầu máng vào (trụ + trượt + barrier)
  Inner_Lane_Rail     — tường liên tục + Reject_Wiper dính đầu (cùng dịch W)
  Entry_Gate_Barrier  — barrier chữ L (trần 20 mm + tấm đứng 10 mm); H 2–26 mm
  Funnel_Guide        — (cũ) → Center_Director: lưỡi cày TÂM đĩa, ép vật ra vành
  Outer_Rim_Funnel    — cánh ngoài thu hẹp vào lane
  Bowl_Tube_Exit_Chute — máng dốc 40° tại 9 giờ; cạnh trái lòng máng trùng mép đĩa

THAO TÁC CHỈNH (tay với từ trên — giống video):
  W: kéo Inner_Lane_Rail trượt xuyên tâm trên 2 ray T của Chute_Slide
     vào tâm = W↑ | ra vành = W↓ | 1 mm = 1 mm W
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

def make_rotor_disc() -> Part.Shape:
    """Disc plate only — M3×16 into Hub_Body (nut pocket on disc underside)."""
    z0 = -DISC_T
    disc = _cyl_z(DISC_D, DISC_T, 0, 0, z0)
    disc = disc.cut(_cyl_z(SHAFT_D + 0.2, DISC_T + 2, 0, 0, z0 - 1))
    disc = _cut_m3_z(disc, hub_m3_xy(), z0 - 1.0, DISC_T + 2.0, nut_bottom=z0)
    return _refine(disc)


def make_hub_body() -> Part.Shape:
    """Hub under disc — Ø7 well so M3×16 only clamps remaining pad + disc."""
    z_hub0 = -DISC_T - HUB_H
    hub = _cyl_z(HUB_D, HUB_H, 0, 0, z_hub0)
    hub = hub.cut(_cyl_z(SHAFT_D + 0.2, HUB_H + 2, 0, 0, z_hub0 - 1))
    clamp_t = HUB_CLAMP_T
    well_h = max(1.0, HUB_H - clamp_t)
    for hx, hy in hub_m3_xy():
        try:
            hub = hub.cut(_cyl_z(7.0, well_h + 0.2, hx, hy, z_hub0))
        except Exception:
            pass
    hub = _cut_m3_z(
        hub,
        hub_m3_xy(),
        z_hub0 + well_h - 1.0,
        clamp_t + 2.0,
        cbore_top=z_hub0 + well_h,
    )
    return _refine(hub)


# Biên TRƯỚC θ_exit của khe Bowl_Tube: trước đây -52° (rộng "cho chắc") vô
# tình cắt mất thành bát NGOÀI lane từ θ≈128° — 50°+ TRƯỚC khi viên rời cung
# tròn tại θ_exit=180°! Suốt đoạn 128°→~176° không còn tường ngoài (không
# Bowl, không Exit_Track, không Inner_Lane_Rail) — viên có thể văng thẳng ra
# ngoài ngay trong lòng lane, không qua Exit_Track (máng "hở" người dùng thấy
# trên model). Quét thực nghiệm (freecadcmd, mọi D 2–25mm, bước 1°) cho thấy
# -3° đã đủ AN TOÀN (0 khe hở tới đúng θ_exit, 0 jam rail↔bowl mọi W 2–26).
