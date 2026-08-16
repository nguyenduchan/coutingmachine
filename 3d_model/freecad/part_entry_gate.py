# -*- coding: utf-8 -*-
"""
CỬA CHỈNH CHIỀU CAO ở ĐẦU MÁNG VÀO — thay cụm Crossbar/Width_Carriage 12 giờ.

  Entry_Gate_Post     — trụ CỐ ĐỊNH bắt vào vành Bowl_Tube (2×M3 xuyên tâm),
                        mang ray chữ T ĐỨNG + vạch chia H, nằm NGOÀI vành bát
  Entry_Gate_Slider   — thanh trượt TỊNH TIẾN ĐỨNG: vòng ôm ray T + tay với bắc
                        qua vành bát vào lòng đĩa + cột hạ xuống barrier
  Entry_Gate_Barrier  — barrier chữ L treo dưới thanh trượt

Barrier (nhìn dọc dòng chảy = chữ L):
      ▌            tấm đứng 10 mm, dựng LÊN ở mép ĐÓN vật
      ▌
      ████████     tấm ngang 20 mm = TRẦN chặn
     ─────────── mặt đĩa
Nhìn từ TRÊN: rộng 40 mm theo phương xuyên tâm, cạnh ngoài ôm cung mép đĩa (r = GATE_R_OUT).
Khe dưới trần = H (2–26 mm) = chiều cao tối đa vật lọt vào máng.

Trượt H: nới bu-lông núm trên vòng ôm → nâng/hạ cả cụm; 1 mm trượt = 1 mm H.
"""
from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import FreeCAD as App
import Part

from mech_common import *  # noqa: F401,F403


# ---------------------------------------------------------------------------
# Vị trí cục bộ dùng chung (khung cửa: +x = xuyên tâm, +y = xuôi dòng, mm)
# ---------------------------------------------------------------------------
def _y_stem0() -> float:
    return GATE_WALL_T


def _y_stem1() -> float:
    return GATE_WALL_T + GATE_STEM_ALONG


def _y_arm_center() -> float:
    return 0.5 * (_y_stem0() + _y_stem1())


def _collar_r0() -> float:
    return GATE_RAIL_R0 - GATE_COLLAR_WALL


def _collar_r1() -> float:
    return GATE_RAIL_R0 + GATE_RAIL_FLANGE_T + GATE_COLLAR_WALL


def entry_gate_bolt_site(height_open: float) -> dict:
    """Bu-lông núm KẸP vòng ôm vào bích ray T — phương NGANG (local +y)."""
    g = entry_gate_geo(height_open)
    yc = _y_arm_center()
    half = 0.5 * (GATE_RAIL_FLANGE_W + 2.0 * GATE_COLLAR_WALL)
    x = GATE_RAIL_R0 + 0.5 * GATE_RAIL_FLANGE_T
    z = g["z_arm0_mm"] + 0.5 * GATE_ARM_T
    return {
        "name": "Screw_Gate_H",
        "hole_origin": (x, yc - half - 1.0, z),
        "knob_origin": (x, yc - half - 1.0 - KNOB_L, z),
        "axis": (0.0, 1.0, 0.0),
        "shank_len": 2.0 * half + 2.0,
    }


# ---------------------------------------------------------------------------
# Barrier chữ L
# ---------------------------------------------------------------------------
def make_entry_gate_barrier(height_open: float) -> Part.Shape:
    """Tấm ngang 20 mm (trần) + tấm đứng 10 mm dựng lên ở mép đón vật.

    Tấm dựng THẲNG (đúng 20 mm dọc dòng chảy trên toàn bộ chiều rộng) rồi CẮT
    theo trụ r = GATE_R_OUT ⇒ cạnh gần đĩa ôm đúng cung mép đĩa; bề rộng nhìn
    từ trên (mép cung → mép trong) = GATE_W_MM."""
    g = entry_gate_geo(height_open)
    over = 6.0  # dư ra ngoài rồi cắt theo cung
    roof = _box(
        GATE_W_MM + over, GATE_ROOF_ALONG_MM, GATE_ROOF_T,
        GATE_R_IN, 0.0, g["z_roof0_mm"],
    )
    wall = _box(
        GATE_W_MM + over, GATE_WALL_T, GATE_WALL_H_MM,
        GATE_R_IN, 0.0, g["z_roof1_mm"],
    )
    body = _to_gate_frame(_refine(roof.fuse(wall)))
    keep = _cyl_z(
        2.0 * GATE_R_OUT, GATE_WALL_H_MM + GATE_ROOF_T + 4.0,
        0.0, 0.0, g["z_roof0_mm"] - 1.0,
    )
    try:
        trimmed = body.common(keep)
        if _shape_ok(trimmed, 100.0):
            body = trimmed
    except Exception:
        pass
    return _refine(body)


# ---------------------------------------------------------------------------
# Thanh trượt tịnh tiến (vòng ôm + tay với + cột)
# ---------------------------------------------------------------------------
def make_entry_gate_slider(height_open: float) -> Part.Shape:
    g = entry_gate_geo(height_open)
    y0, y1 = _y_stem0(), _y_stem1()
    yc = _y_arm_center()
    r_mid = g["r_mid_mm"]

    # Đế cột đặt NẰM trên trần barrier, ngay sau tấm đứng (không chồng khối).
    foot = _box(
        GATE_W_MM, GATE_STEM_ALONG, GATE_STEM_FOOT_T,
        GATE_R_IN, y0, g["z_roof1_mm"],
    )
    z_stem0 = g["z_roof1_mm"] + GATE_STEM_FOOT_T
    stem = _box(
        GATE_STEM_W, GATE_STEM_ALONG, max(2.0, g["z_arm0_mm"] - z_stem0),
        r_mid - 0.5 * GATE_STEM_W, y0, z_stem0,
    )
    # Tay với: từ cột ra tới vòng ôm, bắc QUA vành bát (bụng ≥ BOWL_H).
    arm = _box(
        GATE_RAIL_R0 - (r_mid - 0.5 * GATE_STEM_W), GATE_ARM_W, GATE_ARM_T,
        r_mid - 0.5 * GATE_STEM_W, yc - 0.5 * GATE_ARM_W, g["z_arm0_mm"],
    )
    # Vòng ôm chữ C: ôm bích ray T, hở đúng bề cổ ray.
    half_out = 0.5 * (GATE_RAIL_FLANGE_W + 2.0 * GATE_COLLAR_WALL)
    collar = _box(
        _collar_r1() - _collar_r0(), 2.0 * half_out, GATE_COLLAR_H,
        _collar_r0(), yc - half_out, g["z_collar0_mm"],
    )
    pocket = _box(
        GATE_RAIL_FLANGE_T + 2.0 * GATE_FIT,
        GATE_RAIL_FLANGE_W + 2.0 * GATE_FIT,
        GATE_COLLAR_H + 4.0,
        GATE_RAIL_R0 - GATE_FIT,
        yc - 0.5 * GATE_RAIL_FLANGE_W - GATE_FIT,
        g["z_collar0_mm"] - 2.0,
    )
    neck_slot = _box(
        GATE_RAIL_NECK_T + GATE_COLLAR_WALL + 4.0,
        GATE_RAIL_NECK_W + 2.0 * GATE_FIT,
        GATE_COLLAR_H + 4.0,
        GATE_RAIL_R0 + GATE_RAIL_FLANGE_T - GATE_FIT,
        yc - 0.5 * GATE_RAIL_NECK_W - GATE_FIT,
        g["z_collar0_mm"] - 2.0,
    )
    body = foot.fuse(stem).fuse(arm).fuse(collar)
    body = body.cut(pocket).cut(neck_slot)
    site = entry_gate_bolt_site(height_open)
    body = body.cut(_cyl_axis(SCREW_D, site["shank_len"], site["hole_origin"], site["axis"]))
    return _to_gate_frame(_refine(body))


# ---------------------------------------------------------------------------
# Trụ cố định + ray T đứng
# ---------------------------------------------------------------------------
def gate_rail_z_span() -> tuple[float, float]:
    """Ray phải đủ dài cho vòng ôm ở CẢ H_MIN và H_MAX (+ biên)."""
    lo = entry_gate_geo(H_MIN)["z_collar0_mm"] - 2.0
    hi = entry_gate_geo(H_MAX)["z_collar1_mm"] + 2.0
    return lo, hi


def make_entry_gate_post() -> Part.Shape:
    yc = _y_arm_center()
    z0, z1 = gate_rail_z_span()
    h_rail = z1 - z0
    x_neck = GATE_RAIL_R0 + GATE_RAIL_FLANGE_T
    x_spine = x_neck + GATE_RAIL_NECK_T

    flange = _box(
        GATE_RAIL_FLANGE_T, GATE_RAIL_FLANGE_W, h_rail,
        GATE_RAIL_R0, yc - 0.5 * GATE_RAIL_FLANGE_W, z0,
    )
    neck = _box(
        GATE_RAIL_NECK_T, GATE_RAIL_NECK_W, h_rail,
        x_neck, yc - 0.5 * GATE_RAIL_NECK_W, z0,
    )
    spine = _box(
        GATE_RAIL_SPINE_T, GATE_RAIL_SPINE_W, z1 - GATE_FOOT_Z0,
        x_spine, yc - 0.5 * GATE_RAIL_SPINE_W, GATE_FOOT_Z0,
    )
    body = _to_gate_frame(_refine(flange.fuse(neck).fuse(spine)))

    # Chân yên ngựa áp vào MẶT TRONG vành bát (cung tròn) — bắt 2×M3 xuyên tâm.
    # Chỉ có dải z = GATE_FOOT_Z0 → đỉnh bát (6.1 mm) vì thấp hơn nữa là cắt
    # vào chính barrier khi mở H lớn nhất.
    th_c = GATE_TH_DEG - 0.5 * GATE_ROOF_DEG
    d_half = math.degrees(0.5 * (GATE_FOOT_W + 6.0) / BOWL_IR)
    foot = _annular_sector(
        BOWL_IR - GATE_FOOT_T, BOWL_IR + 1.0,
        th_c - d_half, th_c + d_half,
        GATE_FOOT_Z0, (BOWL_Z0 + BOWL_H) - GATE_FOOT_Z0, n=16,
    )
    # Mặt ngoài yên ngựa = HÌNH TRỤ đúng bán kính trong vành bát (giao với trụ
    # thật, không để cung đa giác ăn vào thành bát vài phần mười mm³).
    foot = foot.common(_cyl_z(2.0 * BOWL_IR, BOWL_H + 20.0, 0.0, 0.0, BOWL_Z0 - 10.0))
    body = _refine(body.fuse(foot))
    # Sống ray là khối HỘP nên 4 góc của nó nhô qua mặt trụ BOWL_IR (~0.3 mm).
    # Giao với trụ thật để mặt tì thành cung, ngồi khít vào lòng bát.
    try:
        inside = body.common(_cyl_z(2.0 * BOWL_IR, 400.0, 0.0, 0.0, -100.0))
        if _shape_ok(inside, 0.5 * float(getattr(body, "Volume", 1.0) or 1.0)):
            body = _refine(inside)
    except Exception:
        pass
    body = _cut_m3_sites(body, gate_mount_sites())

    # Vạch chia H: mỗi 2 mm trên MẶT BÊN sống ray (mặt ngoài nay úp vào thành
    # bát nên không đọc được nữa), mốc = bụng tay với.
    y_mark = yc + 0.5 * GATE_RAIL_SPINE_W
    marks = []
    for dh in range(0, int(H_TRAVEL) + 1, 2):
        z = entry_gate_geo(H_MIN + dh)["z_arm0_mm"]
        marks.append(_box(6.0, 1.2, 0.8, x_spine + 1.0, y_mark - 0.6, z))
    if marks:
        tick = marks[0]
        for m in marks[1:]:
            tick = tick.fuse(m)
        try:
            fused = body.fuse(_to_gate_frame(_refine(tick)))
            if _shape_ok(fused, 0.5 * float(getattr(body, "Volume", 1.0) or 1.0)):
                body = fused
        except Exception:
            pass
    return _refine(body)


def build_entry_gate_parts(height_open: float) -> list[tuple]:
    """(name, shape, color) — 3 component của cụm cửa chỉnh chiều cao."""
    return [
        ("Entry_Gate_Post", make_entry_gate_post(), COLORS.get("bar", (0.72, 0.74, 0.78))),
        ("Entry_Gate_Slider", make_entry_gate_slider(height_open), COLORS.get("clamp", (0.55, 0.58, 0.65))),
        ("Entry_Gate_Barrier", make_entry_gate_barrier(height_open), COLORS.get("height", (0.85, 0.45, 0.25))),
    ]
