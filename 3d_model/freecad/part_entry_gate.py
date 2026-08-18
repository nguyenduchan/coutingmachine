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

  Entry_Gate_Dial     — đĩa số + cột + yên ngựa (CỐ ĐỊNH, bắt vít rời vào bát)
  Entry_Gate_Cam      — đĩa CAM lệch tâm + cổ trục, nhốt trong khung yoke
  Entry_Gate_Knob     — núm vặn tay khía, chốt D vào cổ trục, vít M3 siết ma sát

Chỉnh H bằng NÚM XOAY (cam lệch tâm trong khung Scotch yoke — không lò xo,
không dây thun, không bánh răng):

      ┌───────────────────────┐  ← đỉnh khung (kéo LÊN)
      │   ╭───────╮           │
      │  ╱  đĩa    ╲   ○ trục │  rãnh cao ĐÚNG Ø đĩa cam ⇒ đĩa bị kẹp cả
      │ │   cam     │         │  trên lẫn dưới ⇒ xoay chiều nào khung cũng
      │  ╲ lệch tâm╱          │  bị CƯỠNG BỨC đi theo (positive drive)
      │   ╰───────╯           │
      └───────────────────────┘  ← đáy khung (đẩy XUỐNG)
        └─ rãnh dài ra 2 bên để đĩa cam lắc ngang tự do

  H = H_MAX − e·(1 − cosθ), e = 9 mm ⇒ NỬA VÒNG núm phủ hết 20→2 mm.
  Hai vách ĐẦU rãnh là CHẶN CỨNG: quá 0°/180° chỉ 1.9° là đĩa đụng vách.
  Tự giữ: vít M3 ở tâm núm kẹp đĩa số CỐ ĐỊNH vào giữa (mặt đĩa cam một bên,
  mặt núm bên kia) như phanh đĩa — siết tay là khoá, không cần cóc/lò xo.
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
    return GATE_COLLAR_R0


def _collar_r1() -> float:
    return GATE_COLLAR_R1


def _rot_cam(shape: Part.Shape, theta_deg: float) -> Part.Shape:
    """Quay quanh TRỤC CAM (local +y qua pivot) đi góc θ của núm.

    Quay quanh +y một góc α đưa (x, z) → (x·cosα + z·sinα, −x·sinα + z·cosα),
    nên α = −θ mới cho tâm cam ở (x_p − e·sinθ, z_p + e·cosθ) đúng như
    cam_center_local()."""
    shape.rotate(
        App.Vector(GATE_CAM_PIVOT_X, 0.0, GATE_CAM_PIVOT_Z),
        App.Vector(0.0, 1.0, 0.0),
        -float(theta_deg),
    )
    return shape


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
    body = foot.fuse(stem).fuse(arm).fuse(collar).fuse(_yoke_block(height_open))
    body = body.cut(pocket).cut(neck_slot).cut(_yoke_pocket(height_open))
    site = entry_gate_bolt_site(height_open)
    body = body.cut(_cyl_axis(SCREW_D, site["shank_len"], site["hole_origin"], site["axis"]))
    return _to_gate_frame(_refine(body))


# ---------------------------------------------------------------------------
# Khung Scotch yoke — nhốt đĩa cam, dính vào mặt HẠ LƯU vòng ôm
# ---------------------------------------------------------------------------
def _yoke_block(height_open: float) -> Part.Shape:
    """Khối đặc của khung (chưa khoét rãnh). Nằm ở local y ≥ GATE_YOKE_Y0 nên
    KHÔNG chồng lên ray T (y ∈ ±GATE_RAIL_FLANGE_W/2) dù nó vươn qua cả dải x
    của ray — đó là lý do khung đặt lệch xuôi dòng thay vì ngồi trên vòng ôm."""
    g = entry_gate_cam_geo(height_open)
    return _box(
        g["yoke_x1_mm"] - g["yoke_x0_mm"],
        GATE_YOKE_Y1 - GATE_YOKE_Y0,
        g["yoke_z1_mm"] - g["yoke_z0_mm"],
        g["yoke_x0_mm"], GATE_YOKE_Y0, g["yoke_z0_mm"],
    )


def _yoke_pocket(height_open: float) -> Part.Shape:
    """Rãnh cam: cao ĐÚNG 2(R_cam+fit) ⇒ kẹp đĩa cam hai mặt; dài thêm mỗi bên
    đủ cho tâm cam trượt ngang hết dải ⇒ hai vách đầu thành CHẶN CỨNG."""
    g = entry_gate_cam_geo(height_open)
    return _box(
        g["slot_x1_mm"] - g["slot_x0_mm"],
        (GATE_YOKE_Y1 + 1.0) - (GATE_YOKE_Y0 + GATE_YOKE_BACK_T),
        g["slot_z1_mm"] - g["slot_z0_mm"],
        g["slot_x0_mm"], GATE_YOKE_Y0 + GATE_YOKE_BACK_T, g["slot_z0_mm"],
    )


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


# ---------------------------------------------------------------------------
# Giá đĩa số CỐ ĐỊNH (bạc đỡ cổ trục cam) + bản ốp thành bát đỡ nó
# ---------------------------------------------------------------------------
def _dial_plate_local() -> Part.Shape:
    """Đĩa số Ø52 đứng trong mặt phẳng xuyên tâm, lỗ bạc Ø14 + vạch chia H."""
    x_p, z_p = GATE_CAM_PIVOT_X, GATE_CAM_PIVOT_Z
    disc = _cyl_axis(GATE_DIAL_D, GATE_DIAL_T, (x_p, GATE_DIAL_Y0, z_p), (0.0, 1.0, 0.0))
    # Vạch chia: đặt theo θ(H) — cam hình sin nên vạch KHÔNG cách đều, phải lấy
    # đúng góc từ cam_angle_for_height() chứ không nội suy tuyến tính.
    ticks = None
    for _h, th, long in cam_dial_tick_angles():
        r0 = GATE_DIAL_TICK_R0
        r1 = GATE_DIAL_TICK_R1 if long else GATE_DIAL_TICK_R0 + 3.0
        tick = _box(1.2, 0.8, r1 - r0, x_p - 0.6, GATE_DIAL_Y1, z_p + r0)
        tick = _rot_cam(tick, th)
        ticks = tick if ticks is None else ticks.fuse(tick)
    body = disc if ticks is None else disc.fuse(ticks)
    bore = _cyl_axis(
        GATE_JOURNAL_D + 2.0 * GATE_JOURNAL_FIT, GATE_DIAL_T + 4.0,
        (x_p, GATE_DIAL_Y0 - 2.0, z_p), (0.0, 1.0, 0.0),
    )
    return _refine(body.cut(bore))


def _dial_col_local() -> Part.Shape:
    """CỘT ĐỠ đĩa số: hộp NGỒI TRÊN vành bát (z ≥ đỉnh bát) nên được phép vươn
    quá bán kính bát. Dải local y của nó nằm gọn trong bề dày đĩa số ⇒ đĩa cam
    (y ≤ GATE_CAM_Y1) và núm (y ≥ GATE_KNOB_Y0) đều không bao giờ chạm."""
    return _box(
        GATE_COL_X1 - GATE_COL_X0,
        GATE_COL_Y1 - GATE_COL_Y0,
        GATE_COL_Z1 - GATE_COL_Z0,
        GATE_COL_X0, GATE_COL_Y0, GATE_COL_Z0,
    )


def _dial_skirt_global() -> Part.Shape:
    """Dải yên ngựa ốp MẶT TRONG thành bát: nối chân trụ ray → chân cột đỡ và
    mang 2 vít M3 xuyên tâm. Nằm HẲN dưới đáy khung yoke (z < GATE_YOKE_BOT_Z_MIN)
    nên khung trượt qua bên trên nó tự do.

    Dựng trong khung TOÀN CỤC (cung tròn) ⇒ KHÔNG đi qua _to_gate_frame."""
    skirt = _annular_sector(
        BOWL_IR - GATE_SKIRT_T, BOWL_IR + 1.0,
        _gate_skirt_th0_deg(), GATE_SKIRT_TH1_DEG,
        GATE_FOOT_Z0, (BOWL_Z0 + BOWL_H) - GATE_FOOT_Z0, n=20,
    )
    # Mặt tì phải là HÌNH TRỤ đúng BOWL_IR (cung đa giác n=20 nhô qua ~0.1 mm).
    try:
        inside = skirt.common(_cyl_z(2.0 * BOWL_IR, 400.0, 0.0, 0.0, -100.0))
        if _shape_ok(inside, 100.0):
            skirt = _refine(inside)
    except Exception:
        pass
    return skirt


# ---------------------------------------------------------------------------
# Đĩa cam lệch tâm + cổ trục (một chi tiết in liền)
# ---------------------------------------------------------------------------
def make_entry_gate_cam(height_open: float) -> Part.Shape:
    """Đĩa cam Ø30 lệch tâm 9 mm + cổ trục Ø14 xuyên đĩa số + chốt D vào núm.

    In NẰM (trục thẳng đứng theo hướng in) để mặt trụ cam không bị bậc thang và
    cổ trục không chịu tách lớp khi kéo khung yoke lên."""
    th = cam_angle_for_height(height_open)
    x_p, z_p = GATE_CAM_PIVOT_X, GATE_CAM_PIVOT_Z
    ay = (0.0, 1.0, 0.0)
    cam = _cyl_axis(
        2.0 * GATE_CAM_R, GATE_CAM_T,
        (x_p, GATE_CAM_Y0, z_p + GATE_CAM_ECC), ay,
    )
    # Cổ trục ĂN SÂU vào đĩa cam chứ không chỉ tì mặt ⇒ fuse ra một khối liền.
    journal = _cyl_axis(
        GATE_JOURNAL_D, GATE_JOURNAL_Y1 - (GATE_CAM_Y1 - GATE_JOURNAL_EMBED),
        (x_p, GATE_CAM_Y1 - GATE_JOURNAL_EMBED, z_p), ay,
    )
    body = _refine(cam.fuse(journal))
    # Chốt D: vát một má cổ trục trong đoạn nằm trong núm ⇒ truyền momen, chống
    # núm quay trượt trên trục.
    body = body.cut(_box(
        GATE_JOURNAL_D, GATE_JOURNAL_Y1 - GATE_KNOB_Y0, GATE_JOURNAL_D,
        x_p + GATE_KNOB_DKEY, GATE_KNOB_Y0, z_p - 0.5 * GATE_JOURNAL_D,
    ))
    # Lỗ ép heat-set M3 ở đầu trục — vít từ mặt núm siết vào đây, kẹp đĩa số.
    body = body.cut(_cyl_axis(
        M3_INSERT_D, M3_INSERT_L + 0.5,
        (x_p, GATE_JOURNAL_Y1 - M3_INSERT_L, z_p), ay,
    ))
    return _to_gate_frame(_refine(_rot_cam(body, th)))


# ---------------------------------------------------------------------------
# Núm vặn tay — dáng núm khía tròn phổ thông (8 hõm ngón tay + gân mũi chỉ)
# ---------------------------------------------------------------------------
def make_entry_gate_knob(height_open: float) -> Part.Shape:
    th = cam_angle_for_height(height_open)
    x_p, z_p = GATE_CAM_PIVOT_X, GATE_CAM_PIVOT_Z
    ay = (0.0, 1.0, 0.0)
    body = _cyl_axis(GATE_KNOB_D, GATE_KNOB_T, (x_p, GATE_KNOB_Y0, z_p), ay)
    # Hõm ngón tay quanh vành: khoét N trụ tiếp tuyến ở r = R_núm.
    r_f = 0.5 * GATE_KNOB_D
    for i in range(GATE_KNOB_FLUTES):
        # lệch nửa bước để hướng +z (chỗ đặt gân mũi chỉ) là MÚI chứ không phải hõm
        a = 2.0 * math.pi * (i + 0.5) / GATE_KNOB_FLUTES
        body = body.cut(_cyl_axis(
            GATE_KNOB_FLUTE_D, GATE_KNOB_T + 4.0,
            (x_p + r_f * math.cos(a), GATE_KNOB_Y0 - 2.0, z_p + r_f * math.sin(a)), ay,
        ))
    # Gân MŨI CHỈ: ở θ=0 chỉ thẳng LÊN = H_MAX; quay cùng núm nên luôn trùng
    # hướng lệch tâm của cam, đọc trực tiếp trên vạch đĩa số.
    body = body.fuse(_box(
        GATE_KNOB_PTR_W, GATE_KNOB_PTR_H, GATE_KNOB_PTR_L,
        x_p - 0.5 * GATE_KNOB_PTR_W, GATE_KNOB_Y1, z_p + 2.0,
    ))
    # Lỗ chốt D (khớp cổ trục) + lỗ vít M3 + hốc đầu vít.
    fit = GATE_JOURNAL_FIT
    sock = _cyl_axis(
        GATE_JOURNAL_D + 2.0 * fit, GATE_KNOB_SOCKET_D + 1.0,
        (x_p, GATE_KNOB_Y0 - 0.5, z_p), ay,
    )
    sock = sock.cut(_box(
        GATE_JOURNAL_D, GATE_KNOB_SOCKET_D + 2.0, GATE_JOURNAL_D + 2.0,
        x_p + GATE_KNOB_DKEY + fit, GATE_KNOB_Y0 - 1.0, z_p - 0.5 * GATE_JOURNAL_D - 1.0,
    ))
    body = body.cut(_refine(sock))
    body = body.cut(_cyl_axis(
        M3_CLEAR, GATE_KNOB_T + 4.0, (x_p, GATE_JOURNAL_Y1 - 0.5, z_p), ay,
    ))
    body = body.cut(_cyl_axis(
        M3_HEAD_CB_D, M3_HEAD_CB_H + 0.2,
        (x_p, GATE_KNOB_Y1 - M3_HEAD_CB_H, z_p), ay,
    ))
    return _to_gate_frame(_refine(_rot_cam(body, th)))


def make_entry_gate_dial() -> Part.Shape:
    """ĐĨA SỐ + cột + yên ngựa — CHI TIẾT RỜI, bắt 2 vít M3 xuyên tâm vào bát.

    Vì sao PHẢI rời (không đúc liền vào Entry_Gate_Post): đĩa cam Ø30 phải nằm
    ở y ∈ [22.3, 32.3]; phía +y là đĩa số Ø52 mà lỗ tâm chỉ Ø11.6, phía −y là
    lưng khung yoke ⇒ đúc liền thì KHÔNG có đường nào đưa đĩa cam vào chỗ.
    Rời ra thì lắp được: lắp trụ → lồng thanh trượt → đẩy đĩa cam vào khung yoke
    theo −y → xỏ đĩa số dọc cổ trục rồi bắt vít vào bát → lắp núm."""
    body = _refine(_to_gate_frame(
        _refine(_dial_col_local().fuse(_dial_plate_local()))
    ))
    body = _refine(body.fuse(_dial_skirt_global()))
    return _refine(_cut_m3_sites(body, gate_cam_mount_sites()))


def build_entry_gate_parts(height_open: float) -> list[tuple]:
    """(name, shape, color) — 6 component của cụm cửa chỉnh chiều cao."""
    return [
        ("Entry_Gate_Post", make_entry_gate_post(), COLORS.get("bar", (0.72, 0.74, 0.78))),
        ("Entry_Gate_Dial", make_entry_gate_dial(), COLORS.get("slide", (0.45, 0.48, 0.55))),
        ("Entry_Gate_Slider", make_entry_gate_slider(height_open), COLORS.get("clamp", (0.55, 0.58, 0.65))),
        ("Entry_Gate_Barrier", make_entry_gate_barrier(height_open), COLORS.get("height", (0.85, 0.45, 0.25))),
        ("Entry_Gate_Cam", make_entry_gate_cam(height_open), COLORS.get("rail", (0.85, 0.55, 0.20))),
        ("Entry_Gate_Knob", make_entry_gate_knob(height_open), COLORS.get("mouth", (0.95, 0.25, 0.55))),
    ]
