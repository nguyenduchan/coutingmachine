r"""
Exit_Inner_Wall — vách trong tại cửa ra 9 giờ.

Nhìn từ TOP (9 giờ ở bên TRÁI, −Y là xuống dưới màn hình):

        tâm đĩa
           |
      +####+  y=+60 ─── cắt vành đĩa PHÍA TRÊN (θ≈143.1°)
   x=-80   |####|
           |####|        #### = thân vách, dày về phía TÂM
      -----+####+--  y=0  ── 9 giờ (lùi vào tâm 2 cm)
           |####|              lòng luồng x ∈ [−100,−80] để trống
      +####+  y=-60 ─── cắt vành đĩa PHÍA DƯỚI (θ≈216.9°)
        \__ hai đầu vách cắt theo trụ BOWL_IR → ôm khít thành bát

Vách là DÂY CUNG đầy đủ của đĩa tại x = −80 (dài 120 mm giữa hai mép đĩa).

Đáy HỞ tại GAP0 như mọi vách khác — không chạm mặt đĩa.
"""
from __future__ import annotations

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

_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from mech_common import *  # noqa: F401,F403


def make_exit_inner_wall() -> Part.Shape:
    """Vách thẳng x = EXIT_WALL_X — dây cung đầy đủ: từ mép đĩa TRÊN (y=+60)
    qua 9 giờ (y=0) xuống mép đĩa DƯỚI (y=−60)."""
    x0 = EXIT_WALL_X                 # mặt hướng luồng (−80)
    t = EXIT_WALL_T                  # dày về phía tâm
    h = EXIT_WALL_H
    # Dựng dài dư CẢ HAI ĐẦU rồi cắt bằng trụ thành bát → hai đầu ôm cung bát.
    y_over = abs(EXIT_WALL_Y_RIM) + t + 6.0
    body = _box(t, 2.0 * y_over, h, x0, -y_over, GAP0)
    keep = _cyl_z(2.0 * BOWL_IR, h + 4.0, 0.0, 0.0, GAP0 - 1.0)
    try:
        cut = body.common(keep)
        if _shape_ok(cut, 20.0):
            body = cut
    except Exception:
        pass
    return _refine(_enforce_disc_clearance(body))


def make_exit_slide_rail(y_mm: float) -> Part.Shape:
    """Một ray T nằm ngang (+X) neo vào mặt trong Bowl_Tube tại cao độ y.

    Mặt cắt (nhìn dọc +X): thân trên — cổ — bích dưới. Con trượt ôm lấy bích
    từ dưới lên nên vách 2 không nhấc lên được, chỉ trượt dọc +X.
    Ray nằm ở z ≈ 42 mm, cao hơn đỉnh vách (30.5) và cao hơn vật (≤20) nên
    không bao giờ cản đường vật.
    """
    x_bowl = exit_slide_rail_x_bowl(y_mm) - EXIT_SLIDE_BOWL_EMBED
    ln = EXIT_SLIDE_X_IN - x_bowl
    if ln < 10.0:
        return Part.Shape()
    cx = x_bowl + 0.5 * ln
    z_body = EXIT_SLIDE_T_BODY_Z0
    z_neck = z_body - EXIT_SLIDE_T_NECK_H
    z_flange = z_neck - EXIT_SLIDE_T_FLANGE_H
    body = _box(ln, EXIT_SLIDE_RAIL_W, EXIT_SLIDE_RAIL_H,
                cx - 0.5 * ln, y_mm - 0.5 * EXIT_SLIDE_RAIL_W, z_body)
    neck = _box(ln, EXIT_SLIDE_T_NECK_W, EXIT_SLIDE_T_NECK_H,
                cx - 0.5 * ln, y_mm - 0.5 * EXIT_SLIDE_T_NECK_W, z_neck)
    flange = _box(ln, EXIT_SLIDE_T_FLANGE_W, EXIT_SLIDE_T_FLANGE_H,
                  cx - 0.5 * ln, y_mm - 0.5 * EXIT_SLIDE_T_FLANGE_W, z_flange)
    out = body
    for extra in (neck, flange):
        try:
            fused = out.fuse(extra)
            if _shape_ok(fused, 0.5 * float(getattr(out, "Volume", 1.0) or 1.0)):
                out = fused
        except Exception:
            continue
    return _refine(out)


def make_exit_slide() -> Part.Shape:
    """Exit_Slide = 2 ray T cố định (component riêng)."""
    rails = [make_exit_slide_rail(y) for y in EXIT_SLIDE_Y]
    rails = [r for r in rails if _shape_ok(r, 10.0)]
    if not rails:
        return Part.Shape()
    out = rails[0]
    for r in rails[1:]:
        out = out.fuse(r)
    return _refine(out)


def make_exit_slide_shoe(y_mm: float, gap_mm: float | None = None) -> Part.Shape:
    """Con trượt ôm bích ray, mọc từ đỉnh vách 2 lên. Đi theo vách khi chỉnh."""
    x2 = exit_wall2_x(gap_mm)
    z_wall_top = GAP0 + EXIT_WALL_H
    z_body = EXIT_SLIDE_T_BODY_Z0
    z_neck = z_body - EXIT_SLIDE_T_NECK_H
    z_flange = z_neck - EXIT_SLIDE_T_FLANGE_H
    fit = EXIT_SLIDE_FIT
    ln = EXIT_SLIDE_SHOE_LEN
    w = EXIT_SLIDE_T_FLANGE_W + 2.0 * (2.5 + fit)
    # Đáy con trượt phải CAO hơn đỉnh Exit_Inner_Wall: ở gap nhỏ con trượt lùi
    # qua đúng trên đầu vách 1, hạ thấp là cắn vào nó.
    z0 = z_wall_top + 0.6
    h_total = (z_neck + 0.6) - z0
    # thân U: cột từ đỉnh vách lên, ôm quanh bích
    outer = _box(ln, w, h_total, x2 - 0.5 * (ln - EXIT_WALL_T), y_mm - 0.5 * w, z0)
    pocket = _box(ln + 2.0, EXIT_SLIDE_T_FLANGE_W + 2.0 * fit,
                  EXIT_SLIDE_T_FLANGE_H + 2.0 * fit,
                  x2 - 0.5 * (ln - EXIT_WALL_T) - 1.0,
                  y_mm - 0.5 * EXIT_SLIDE_T_FLANGE_W - fit, z_flange - fit)
    neck_cut = _box(ln + 2.0, EXIT_SLIDE_T_NECK_W + 2.0 * fit,
                    EXIT_SLIDE_T_NECK_H + 8.0,
                    x2 - 0.5 * (ln - EXIT_WALL_T) - 1.0,
                    y_mm - 0.5 * EXIT_SLIDE_T_NECK_W - fit, z_neck - fit)
    try:
        shoe = outer.cut(pocket).cut(neck_cut)
    except Exception:
        shoe = outer
    # cột nối xuống thân vách
    # cột nối: chỉ nằm trong bề dày vách 2 nên không bao giờ chạm vách 1
    stem = _box(EXIT_WALL_T, EXIT_SLIDE_T_FLANGE_W, (z0 + 1.0) - (z_wall_top - 6.0),
                x2, y_mm - 0.5 * EXIT_SLIDE_T_FLANGE_W, z_wall_top - 6.0)
    try:
        fused = shoe.fuse(stem)
        if _shape_ok(fused, 0.4 * float(getattr(shoe, "Volume", 1.0) or 1.0)):
            shoe = fused
    except Exception:
        pass
    return _refine(shoe)


def make_exit_inner_wall_2(gap_mm: float | None = None) -> Part.Shape:
    """Vách 2 + 2 con trượt — TỊNH TIẾN theo +X để chỉnh bề rộng kênh.

    gap_mm = bề rộng thông thuỷ giữa hai vách (EXIT_GAP_MIN..EXIT_GAP_MAX).
    KHÔNG cắt bằng trụ bát — đoạn thò ra xuyên qua rãnh khoét trên Bowl_Tube
    (rãnh đã mở rộng phủ hết hành trình, xem exit_wall2_slot_geo).
    """
    g = exit_wall2_geo(gap_mm)
    t = EXIT_WALL_T
    h = EXIT_WALL_H
    y_end = g["y_end"]
    body = _box(t, abs(y_end), h, g["x_in"], y_end, GAP0)
    for y_r in EXIT_SLIDE_Y:
        try:
            shoe = make_exit_slide_shoe(y_r, gap_mm)
            fused = body.fuse(shoe)
            if _shape_ok(fused, 0.5 * float(getattr(body, "Volume", 1.0) or 1.0)):
                body = fused
        except Exception:
            continue
    return _refine(_enforce_disc_clearance(body))


def exit_inner_wall_geo() -> dict:
    """Toạ độ then chốt — dùng khi cần đối chiếu bằng tay trong FreeCAD."""
    shape = make_exit_inner_wall()
    bb = shape.BoundBox
    return {
        "start_xy": (EXIT_WALL_X, 0.0),
        "rim_touch_xy": (EXIT_WALL_X, EXIT_WALL_Y_RIM),
        "offset_from_9h_mm": EXIT_WALL_OFFSET_MM,
        "thickness_mm": EXIT_WALL_T,
        "height_mm": EXIT_WALL_H,
        "z0_mm": GAP0,
        "bbox_x_mm": (round(bb.XMin, 3), round(bb.XMax, 3)),
        "bbox_y_mm": (round(bb.YMin, 3), round(bb.YMax, 3)),
        "bbox_z_mm": (round(bb.ZMin, 3), round(bb.ZMax, 3)),
        "volume_mm3": round(float(shape.Volume), 1),
    }
