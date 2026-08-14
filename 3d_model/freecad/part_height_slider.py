"""
Tube_L_Exit_Gate — rotary disc feeder kiểu SchanerDesigns short:
  https://www.youtube.com/shorts/ju5vIg66NNk

Module rieng: THANH TINH TIEN DOC (slider) — om cot chu T ray H tren
Width_Carriage, mang Height_Scraper truot len/xuong de chinh H. Kep bang
bu-long num van lon, phuong ngang (xem _height_bolt_site trong mech_common).

make_height_scraper() = ghep vach dieu chinh do cao (part_height_wall.py) +
thanh tinh tien doc (module nay) thanh 1 part hoan chinh "Height_Scraper" —
dung cho build_tube_l_exit_gate_parts() va cac ham verify_* trong
tube_l_exit_gate.py (giu nguyen ten cong khai, khong doi API ben ngoai).
"""
from __future__ import annotations

import FreeCAD as App
import Part

from mech_common import *  # noqa: F401,F403
from part_width_carriage import make_width_carriage
from part_height_wall import make_height_wall


def make_height_slider(width_open: float, height_open: float) -> Part.Shape:
    """Thanh tịnh tiến dọc: ôm cột T ray H trên Width_Carriage (U hẹp trong khe
    thanh + C rộng chỉ phía trên thanh), mang Height_Scraper trượt theo H."""
    ap = aperture_from_opens(width_open, height_open)
    z1 = height_scraper_z(height_open)
    s = width_clamp_s(width_open)
    z_rail = BAR_Z + BAR_T
    z_top = z_rail + SLIDE_W_H
    stem_x0 = s + 2.8
    # U hẹp trong khe thanh + C rộng chỉ phía trên thanh (không xuyên đặc bar)
    z_hi = z_top + CLAMP_H + H_TRAVEL + 4.0
    uy_slot = 0.5 * (BAR_SLOT_W - 1.6)
    x0_n = stem_x0 - 0.4
    xw_n = H_RAIL_NECK + 2.4
    below = _box(xw_n, 2.0 * uy_slot, max(2.0, (BAR_Z - 0.5) - z1), x0_n, -uy_slot, z1)
    through = _box(xw_n - 0.6, 2.0 * uy_slot - 1.2, BAR_T + 1.2, x0_n + 0.3, -(uy_slot - 0.6), BAR_Z - 0.5)
    above = _box(
        H_RAIL_TOP + 5.0, 2.0 * uy_slot, z_hi - (z_rail + 0.35),
        stem_x0 - 0.6, -uy_slot, z_rail + 0.35,
    )
    cut_n = _box(
        H_RAIL_NECK + 2.0 * STEM_FIT,
        STEM_T + 1.0 + 2.0 * STEM_FIT,
        z_hi + 8.0,
        stem_x0 - STEM_FIT,
        -0.5 * (STEM_T + 1.0 + 2.0 * STEM_FIT),
        z1 - 4.0,
    )
    cut_t = _box(
        H_RAIL_TOP + 2.0 * STEM_FIT,
        STEM_T + 1.0 + 2.0 * STEM_FIT,
        z_hi,
        stem_x0 + H_RAIL_NECK - 0.5 - STEM_FIT,
        -0.5 * (STEM_T + 1.0 + 2.0 * STEM_FIT),
        z_rail + 0.2,
    )
    slider = below.fuse(through).fuse(above)
    # Lo bu-long kep H — phuong ngang (truc Y), xuyen vong om "above" ep vao mat
    # bich H_RAIL_TOP (thay lo xo ti cu). Xem _height_bolt_site().
    h_site = _height_bolt_site(s)
    slider = slider.cut(_cyl_axis(SCREW_D, h_site["shank_len"], h_site["hole_origin"], h_site["axis"]))
    slider = slider.cut(cut_n).cut(cut_t)
    body = _to_adj_frame(slider)
    try:
        body = _refine(body.cut(make_crossbar_bridge()))
    except Exception:
        pass
    try:
        body = _refine(body.cut(make_width_carriage(width_open)))
    except Exception:
        pass
    return _refine(body)


def make_height_scraper(width_open: float, height_open: float) -> Part.Shape:
    """Height_Scraper hoàn chỉnh = vách điều chỉnh độ cao (make_height_wall) +
    thanh tịnh tiến dọc (make_height_slider). Tương đương chính xác make_height_scraper
    gốc (A∪B)\\C = (A\\C)∪(B\\C) — chỉ tách file, không đổi hình học."""
    wall = make_height_wall(width_open, height_open)
    slider = make_height_slider(width_open, height_open)
    return _refine(wall.fuse(slider))
