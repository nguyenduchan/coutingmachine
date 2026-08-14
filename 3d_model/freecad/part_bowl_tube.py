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
    """Vành bát cố định — chỉ thành, không gồm máng exit."""
    outer = _cyl_z(BOWL_OD, BOWL_H, 0, 0, BOWL_Z0)
    inner = _cyl_z(BOWL_ID, BOWL_H + 2, 0, 0, BOWL_Z0 - 1)
    tube = outer.cut(inner)
    # Cửa cung: chỉ hở đúng chỗ máng thoát (θ_exit + peel). Thành bát liền
    # quanh đĩa suốt θ_mouth→θ_exit (xem BOWL_SLOT_* trong mech_common).
    slot = _annular_sector(
        CHANNEL_R_OUTER - CHUTE_W_MM - 10.0,
        BOWL_OR + 2.0,
        THETA_EXIT_DEG - BOWL_SLOT_BEFORE_EXIT_DEG,
        THETA_EXIT_DEG + BOWL_SLOT_AFTER_EXIT_DEG,
        GAP0 - 1.0,
        H_MAX + 14.0,
        n=32,
    )
    tube = tube.cut(slot)
    tube = _cut_m3_sites(tube, guide_mount_sites())
    return _refine(tube)


def make_bowl_exit_chute_fitted() -> Part.Shape:
    """Máng 40° cắt khỏi thành bát đặc — chỉ nằm trong cửa slot + phía ngoài."""
    chute = make_bowl_exit_chute()
    wall = make_bowl_tube()
    try:
        cut = chute.cut(wall)
        if _shape_ok(cut, 200.0):
            return _refine(cut)
    except Exception:
        pass
    return chute


def make_bowl_tube_complete() -> Part.Shape:
    """Thành bát + máng exit nghiêng (cùng volume với App::Part Bowl_Tube)."""
    wall = make_bowl_tube()
    chute = make_bowl_exit_chute_fitted()
    try:
        fused = wall.fuse(chute)
        if _shape_ok(fused, 0.5 * float(getattr(wall, "Volume", 1.0) or 1.0)):
            return _refine(fused)
    except Exception:
        pass
    return wall


def write_bowl_tube_component(path, color=(0.92, 0.92, 0.94), style_fn=None) -> None:
    """Bowl_Tube.FCStd: parent App::Part + Wall + Exit_Chute."""
    doc = App.newDocument("Bowl_Tube")
    wall = doc.addObject("Part::Feature", "Bowl_Tube_Wall")
    wall.Shape = make_bowl_tube()
    wall.Label = "Bowl_Tube_Wall"
    chute = doc.addObject("Part::Feature", "Bowl_Tube_Exit_Chute")
    chute.Shape = make_bowl_exit_chute_fitted()
    chute.Label = "Bowl_Tube_Exit_Chute"
    if style_fn is not None:
        style_fn(wall, color, 55)
        style_fn(chute, (0.12, 0.12, 0.12), 0)
    grp = doc.addObject("App::Part", "Bowl_Tube")
    grp.Label = "Bowl_Tube"
    kids = [wall, chute]
    if hasattr(grp, "addObjects"):
        grp.addObjects(kids)
    else:
        grp.Group = kids
    try:
        origin = getattr(grp, "Origin", None)
        if origin is not None and hasattr(origin, "Visibility"):
            origin.Visibility = False
    except Exception:
        pass
    doc.recompute()
    doc.saveAs(str(path))
    App.closeDocument(doc.Name)


