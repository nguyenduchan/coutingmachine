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

def make_bowl_tube() -> Part.Shape:
    outer = _cyl_z(BOWL_OD, BOWL_H, 0, 0, BOWL_Z0)
    inner = _cyl_z(BOWL_ID, BOWL_H + 2, 0, 0, BOWL_Z0 - 1)
    tube = outer.cut(inner)
    # Cửa cung: chỉ mở từ sát θ_exit trở đi — thành bát vẫn bao NGOÀI lane
    # suốt θ_mouth→θ_exit (xem BOWL_SLOT_BEFORE_EXIT_DEG).
    slot = _annular_sector(
        CHANNEL_R_OUTER - W_MAX - 10.0,
        BOWL_OR + 8.0,
        THETA_EXIT_DEG - BOWL_SLOT_BEFORE_EXIT_DEG,
        THETA_EXIT_DEG + BOWL_SLOT_AFTER_EXIT_DEG,
        GAP0 - 1.0,
        H_MAX + 14.0,
        n=32,
    )
    tube = tube.cut(slot)
    tube = _cut_m3_sites(tube, guide_mount_sites())
    return _refine(tube)


