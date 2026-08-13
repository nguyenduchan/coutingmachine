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

def _t_rail_clearance_local(s: float) -> Part.Shape:
    """Ray chữ T trên thanh (local) + FIT — cắt khỏi carriage top."""
    pad = SLIDE_W_FIT + 0.55
    half_len = 0.5 * CLAMP_L + 6.0
    neck = _box(
        2.0 * half_len, SLIDE_W_NECK + 2.0 * pad, SLIDE_W_H + 1.2,
        s - half_len, -0.5 * (SLIDE_W_NECK + 2.0 * pad), BAR_Z + BAR_T - 0.4,
    )
    flange = _box(
        2.0 * half_len, SLIDE_W_TOP + 2.0 * pad, 3.2 + pad,
        s - half_len, -0.5 * (SLIDE_W_TOP + 2.0 * pad),
        BAR_Z + BAR_T + SLIDE_W_H - 2.6,
    )
    return _refine(neck.fuse(flange))


def make_width_clamp(width_open: float) -> Part.Shape:
    """
    Width_Carriage — trượt trên ray chữ T của Crossbar:
      • rãnh T ôm ray W (cut clearance — không lấn solid)
      • cổ ray H mỏng xuyên slot thanh; chữ T đầy đủ chỉ phía trên thanh
      • hang treo rail DỪNG dưới mặt dưới thanh
      • trim trong Ø bowl — không lấn Bowl_Tube
    """
    s = width_clamp_s(width_open)
    z_rail = BAR_Z + BAR_T
    z_top = z_rail + SLIDE_W_H
    top = _box(CLAMP_L, CLAMP_W, CLAMP_H, s - 0.5 * CLAMP_L, -0.5 * CLAMP_W, z_top - 1.0)
    jaw_h = BAR_T + SLIDE_W_H + 2.0
    y_l = -0.5 * BAR_W - CLAMP_FIT - CLAMP_JAW_T
    y_r = 0.5 * BAR_W + CLAMP_FIT
    jaw_l = _box(CLAMP_L - 2.0, CLAMP_JAW_T, jaw_h, s - 0.5 * (CLAMP_L - 2.0), y_l, BAR_Z - 1.0)
    jaw_r = _box(CLAMP_L - 2.0, CLAMP_JAW_T, jaw_h, s - 0.5 * (CLAMP_L - 2.0), y_r, BAR_Z - 1.0)
    hang_z1 = BAR_Z - 2.0
    hang_z0 = GAP0 + RAIL_H - 2.0
    if hang_z1 - hang_z0 < 2.0:
        hang_z0 = hang_z1 - 2.0
    hang_h = hang_z1 - hang_z0
    hang = _box(
        RAIL_T + 2.5, CLAMP_W - 6.0, hang_h,
        s - RAIL_T - 1.2, -0.5 * (CLAMP_W - 6.0), hang_z0,
    )
    stem_x0 = s + 2.8
    # Cổ ray H: dưới thanh dừng trước đáy; xuyên khe chỉ bản mỏng
    neck_y = min(STEM_T + 0.4, BAR_SLOT_W - 6.0)
    h_neck_low = _box(
        H_RAIL_NECK, neck_y, max(2.0, (BAR_Z - 0.6) - hang_z0),
        stem_x0, -0.5 * neck_y, hang_z0,
    )
    slot_neck = _box(
        H_RAIL_NECK - 0.4, min(neck_y, BAR_SLOT_W - 2.4), BAR_T + 1.4,
        stem_x0 + 0.2, -0.5 * min(neck_y, BAR_SLOT_W - 2.4), BAR_Z - 0.6,
    )
    col_z0 = z_rail + 0.3
    col_h = (z_top + CLAMP_H + 2.0) - col_z0
    h_neck_hi = _box(
        H_RAIL_NECK, STEM_T + 1.0, col_h,
        stem_x0, -0.5 * (STEM_T + 1.0), col_z0,
    )
    h_flange = _box(
        H_RAIL_TOP, STEM_T + 1.0, col_h,
        stem_x0 + H_RAIL_NECK - 0.5, -0.5 * (STEM_T + 1.0), col_z0,
    )
    tongue_w = min(BAR_SLOT_W - 1.2, 5.0)
    tongue = _box(
        CLAMP_L - 10.0, tongue_w, BAR_T - 0.5,
        s - 0.5 * (CLAMP_L - 10.0), -0.5 * tongue_w, BAR_Z + 0.25,
    )
    # Pocket xuyên top: slider H đi 2–26 mm không cắt đặc carriage
    pocket = _box(
        H_RAIL_TOP + 8.0, 10.5, CLAMP_H + SLIDE_W_H + 10.0,
        stem_x0 - 1.2, -5.25, BAR_Z + BAR_T - 1.0,
    )
    body = top.fuse(jaw_l).fuse(jaw_r).fuse(hang).fuse(tongue)
    body = body.cut(_t_rail_clearance_local(s))
    body = body.cut(pocket)
    body = body.fuse(h_neck_low).fuse(slot_neck).fuse(h_neck_hi).fuse(h_flange)
    # Lỗ bu-lông kẹp W — phương ngang (trục Y), xuyên má trái→phải qua khe ray T
    # (thay lò xo tì cũ). Xem _width_bolt_sites().
    for site in _width_bolt_sites(s):
        body = body.cut(_cyl_axis(SCREW_D, site["shank_len"], site["hole_origin"], site["axis"]))
    body = _to_adj_frame(_refine(body))
    try:
        body = _refine(body.cut(make_crossbar_bridge()))
    except Exception:
        pass
    keep = _cyl_z(BOWL_ID - 1.0, BOWL_H + 80.0, 0.0, 0.0, -20.0)
    try:
        trimmed = body.common(keep)
        if float(getattr(trimmed, "Volume", 0.0) or 0.0) > 0.35 * float(body.Volume):
            body = _refine(trimmed)
    except Exception:
        pass
    return body


def make_width_carriage(width_open: float) -> Part.Shape:
    """Alias tên rõ — ray trượt W."""
    return make_width_clamp(width_open)


