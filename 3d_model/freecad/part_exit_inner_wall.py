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

CHỈNH BỀ RỘNG (W) BẰNG NÚM XOAY — cam lệch tâm trong khung Scotch yoke NẰM
NGANG, trục THẲNG ĐỨNG, vặn từ trên xuống:

   nhìn từ TRÊN                       nhìn từ SƯỜN (theo −Y)
   ┌──────────────────────┐              ╔═══╗  ← núm vặn Ø36     z 68.4–81.4
   │ ┌──────────────────┐ │           ═══╩═══╩═══ đĩa số Ø52      z 58.4–68.4
   │ │  ╭────╮          │ │   rãnh    ┌───┼───┐
   │ │ │ cam  │  ← lắc  │ │ ← DÀI     │ ▓▓▓▓▓ │ ← tấm yoke + cam  z 48–58
   │ │  ╰────╯    theo Y│ │   theo Y  └───┼───┘
   │ └──────────────────┘ │             ══╪══ ray T (Exit_Slide)  z 36.4–47
   └──────────────────────┘               │  cầu nối len giữa 2 con trượt
     ↑ KẸP theo X = 2·R_cam                │
       ⇒ đẩy ra VÀ kéo vào đều cưỡng bức  vách 2

  gap = EXIT_GAP_MAX − e·(1 − cosθ), e = 5 mm ⇒ NỬA VÒNG núm phủ hết 13→3 mm.
  Hai vách ĐẦU rãnh (theo Y) là CHẶN CỨNG hai đầu dải gap.
  Tự giữ: vít M3 ở tâm núm kẹp đĩa số CỐ ĐỊNH vào giữa (đỉnh đĩa cam một bên,
  đáy núm bên kia) như phanh đĩa — không lò xo, không dây thun, không bánh răng.
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


def make_exit_dial() -> Part.Shape:
    """ĐĨA SỐ Ø52 nằm ngang + tai bắt vít — CHI TIẾT RỜI, 2 vít M3 thẳng đứng
    xuống đỉnh cột của Exit_Slide.

    Vì sao PHẢI rời (không đúc liền vào Exit_Slide): đĩa cam Ø30 phải nằm ở
    z ∈ [47.6, 58.4]; trên nó là đĩa số Ø52 mà lỗ tâm chỉ Ø11.6, dưới nó chỉ còn
    0.6 mm tới đỉnh ray T ⇒ đúc liền thì KHÔNG có đường nào đưa đĩa cam vào chỗ.
    Rời ra thì lắp được: lắp ray+cột → lồng vách 2 → THẢ đĩa cam từ trên xuống
    rãnh yoke → úp đĩa số lên, bắt 2 vít → lắp núm."""
    x_p, y_p = EXIT_CAM_PIVOT_X, EXIT_CAM_PIVOT_Y
    disc = _cyl_z(EXIT_DIAL_D, EXIT_DIAL_T, x_p, y_p, EXIT_DIAL_Z0)
    tab = _box(
        EXIT_DIAL_TAB_X1 - EXIT_DIAL_TAB_X0, 2.0 * EXIT_DIAL_TAB_HALF_W, EXIT_DIAL_T,
        EXIT_DIAL_TAB_X0, y_p - EXIT_DIAL_TAB_HALF_W, EXIT_DIAL_Z0,
    )
    disc = disc.fuse(tab)
    ticks = None
    for _g, th, long in exit_cam_dial_tick_angles():
        r0 = EXIT_DIAL_TICK_R0
        r1 = EXIT_DIAL_TICK_R1 if long else EXIT_DIAL_TICK_R0 + 3.0
        tick = _box(r1 - r0, 1.2, 0.8, x_p + r0, y_p - 0.6, EXIT_DIAL_Z1)
        tick = _exit_rot_cam(tick, th)
        ticks = tick if ticks is None else ticks.fuse(tick)
    body = disc if ticks is None else disc.fuse(ticks)
    bore = _cyl_z(GATE_JOURNAL_D + 2.0 * GATE_JOURNAL_FIT, EXIT_DIAL_T + 4.0,
                  x_p, y_p, EXIT_DIAL_Z0 - 2.0)
    body = body.cut(bore)
    for bx, by in exit_dial_bolt_sites():
        body = body.cut(_cyl_z(M3_CLEAR, EXIT_DIAL_T + 4.0, bx, by, EXIT_DIAL_Z0 - 2.0))
        body = body.cut(_cyl_z(M3_HEAD_CB_D, M3_HEAD_CB_H + 0.2, bx, by,
                               EXIT_DIAL_Z1 - M3_HEAD_CB_H))
    return _refine(body)


def _exit_dial_col() -> Part.Shape:
    """CỘT ốp mặt trong thành bát (hàn liền ray T y = −20), đỉnh phẳng ở mặt dưới
    đĩa số, mang 2 heat-set M3 để bắt đĩa số RỜI xuống.

    Mép TRONG của bản ốp đặt tại EXIT_COL_X1 — ngoài hành trình xa nhất của tấm
    yoke (tấm lùi hết ở gap nhỏ nhất). Chính điều kiện này quyết định bán kính
    đặt trục cam: đẩy trục vào gần tâm hơn thì bản ốp không còn chỗ đi vào."""
    col = _box(
        (EXIT_COL_X1 + 14.0) - (EXIT_COL_X1 - 14.0), EXIT_COL_Y1 - EXIT_COL_Y0,
        EXIT_COL_Z1 - EXIT_COL_Z0,
        EXIT_COL_X1 - 14.0, EXIT_COL_Y0, EXIT_COL_Z0,
    )
    # mép trong THẲNG (không theo cung) để luôn cách tấm yoke đúng 1.2 mm
    col = col.cut(_box(60.0, 200.0, 200.0, EXIT_COL_X1, -150.0, -50.0))
    # mặt ngoài ôm thành bát, cắm vào bát EXIT_SLIDE_BOWL_EMBED như ray T
    col = col.common(_cyl_z(2.0 * EXIT_COL_R_OUT, 200.0, 0.0, 0.0, -50.0))
    for bx, by in exit_dial_bolt_sites():
        col = col.cut(_cyl_z(M3_INSERT_D, M3_INSERT_L + 0.5, bx, by,
                             EXIT_COL_Z1 - M3_INSERT_L))
    return _refine(col)


def make_exit_slide() -> Part.Shape:
    """Exit_Slide = 2 ray T cố định + CỘT đỡ đĩa số (đĩa số là chi tiết rời)."""
    rails = [make_exit_slide_rail(y) for y in EXIT_SLIDE_Y]
    rails = [r for r in rails if _shape_ok(r, 10.0)]
    if not rails:
        return Part.Shape()
    out = rails[0]
    for r in rails[1:]:
        out = out.fuse(r)
    for extra in (_exit_dial_col(),):
        try:
            fused = out.fuse(extra)
            if _shape_ok(fused, 0.5 * float(getattr(out, "Volume", 1.0) or 1.0)):
                out = fused
        except Exception:
            continue
    return _refine(out)


# ---------------------------------------------------------------------------
# Đĩa cam W + cổ trục (in liền) và núm vặn rời
# ---------------------------------------------------------------------------
def make_exit_cam(gap_mm: float | None = None) -> Part.Shape:
    """Đĩa cam Ø30 lệch tâm 9 mm, trục ĐỨNG, cổ trục Ø14 xuyên đĩa số lên núm."""
    th = exit_cam_angle_for_gap(gap_mm)
    x_p, y_p = EXIT_CAM_PIVOT_X, EXIT_CAM_PIVOT_Y
    cam = _cyl_z(2.0 * EXIT_CAM_R, EXIT_CAM_T,
                 x_p + EXIT_CAM_ECC, y_p, EXIT_CAM_Z0)
    # Cổ trục ĂN SÂU vào đĩa cam GATE_JOURNAL_EMBED chứ không chỉ tì mặt: trục
    # nằm cách tâm đĩa đúng e < R nên phần cắm vào hoàn toàn trong lòng đĩa ⇒
    # fuse ra một khối liền, in một lần, không có mối nối phẳng dễ tách lớp.
    journal = _cyl_z(
        GATE_JOURNAL_D, EXIT_JOURNAL_Z1 - (EXIT_CAM_Z1 - GATE_JOURNAL_EMBED),
        x_p, y_p, EXIT_CAM_Z1 - GATE_JOURNAL_EMBED,
    )
    body = _refine(cam.fuse(journal))
    # chốt D trong đoạn nằm trong núm
    body = body.cut(_box(
        GATE_JOURNAL_D, GATE_JOURNAL_D, EXIT_JOURNAL_Z1 - EXIT_KNOB_Z0,
        x_p + GATE_KNOB_DKEY, y_p - 0.5 * GATE_JOURNAL_D, EXIT_KNOB_Z0,
    ))
    # lỗ ép heat-set M3 ở đầu trục — vít từ đỉnh núm siết xuống, kẹp đĩa số
    body = body.cut(_cyl_z(M3_INSERT_D, M3_INSERT_L + 0.5, x_p, y_p,
                           EXIT_JOURNAL_Z1 - M3_INSERT_L))
    return _refine(_exit_rot_cam(body, th))


def make_exit_knob(gap_mm: float | None = None) -> Part.Shape:
    """Núm vặn W — cùng dáng núm khía với núm H, ngửa lên trời."""
    th = exit_cam_angle_for_gap(gap_mm)
    x_p, y_p = EXIT_CAM_PIVOT_X, EXIT_CAM_PIVOT_Y
    body = _cyl_z(GATE_KNOB_D, GATE_KNOB_T, x_p, y_p, EXIT_KNOB_Z0)
    r_f = 0.5 * GATE_KNOB_D
    for i in range(GATE_KNOB_FLUTES):
        a = 2.0 * math.pi * (i + 0.5) / GATE_KNOB_FLUTES
        body = body.cut(_cyl_z(
            GATE_KNOB_FLUTE_D, GATE_KNOB_T + 4.0,
            x_p + r_f * math.cos(a), y_p + r_f * math.sin(a), EXIT_KNOB_Z0 - 2.0,
        ))
    # gân mũi chỉ: θ=0 chỉ theo +X = gap lớn nhất
    body = body.fuse(_box(
        GATE_KNOB_PTR_L, GATE_KNOB_PTR_W, GATE_KNOB_PTR_H,
        x_p + 2.0, y_p - 0.5 * GATE_KNOB_PTR_W, EXIT_KNOB_Z1,
    ))
    fit = GATE_JOURNAL_FIT
    sock = _cyl_z(GATE_JOURNAL_D + 2.0 * fit, GATE_KNOB_SOCKET_D + 1.0,
                  x_p, y_p, EXIT_KNOB_Z0 - 0.5)
    sock = sock.cut(_box(
        GATE_JOURNAL_D, GATE_JOURNAL_D + 2.0, GATE_KNOB_SOCKET_D + 2.0,
        x_p + GATE_KNOB_DKEY + fit, y_p - 0.5 * GATE_JOURNAL_D - 1.0, EXIT_KNOB_Z0 - 1.0,
    ))
    body = body.cut(_refine(sock))
    body = body.cut(_cyl_z(M3_CLEAR, GATE_KNOB_T + 4.0, x_p, y_p, EXIT_JOURNAL_Z1 - 0.5))
    body = body.cut(_cyl_z(M3_HEAD_CB_D, M3_HEAD_CB_H + 0.2, x_p, y_p,
                           EXIT_KNOB_Z1 - M3_HEAD_CB_H))
    return _refine(_exit_rot_cam(body, th))


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


def _exit_rot_cam(shape: Part.Shape, theta_deg: float) -> Part.Shape:
    """Quay quanh TRỤC CAM W (thẳng đứng qua pivot) đi góc θ của núm.

    Quay quanh +z góc α đưa (e, 0) → (e·cosα, e·sinα) nên α = −θ mới cho tâm cam
    ở (x_p + e·cosθ, y_p − e·sinθ) đúng như exit_cam_center()."""
    shape.rotate(
        App.Vector(EXIT_CAM_PIVOT_X, EXIT_CAM_PIVOT_Y, 0.0),
        App.Vector(0.0, 0.0, 1.0),
        -float(theta_deg),
    )
    return shape


def _exit_yoke_plate(gap_mm: float | None = None) -> Part.Shape:
    """Tấm yoke NẰM NGANG + cầu nối xuống đỉnh vách 2.

    Cầu nối bám vào dải thịt phía +X của tấm (đĩa cam không bao giờ ra khỏi rãnh
    nên chỗ đó luôn trống), và len GIỮA HAI con trượt theo Y nên không đụng ray."""
    g = exit_cam_geo(gap_mm)
    x2 = g["wall2_x_in"]
    dy = EXIT_RISER_Y1 - EXIT_RISER_Y0
    plate = _box(
        g["yoke_x1_mm"] - g["yoke_x0_mm"], g["yoke_y1_mm"] - g["yoke_y0_mm"], EXIT_YOKE_T,
        g["yoke_x0_mm"], g["yoke_y0_mm"], EXIT_YOKE_Z0,
    )
    slot = _box(
        g["slot_x1_mm"] - g["slot_x0_mm"], g["slot_y1_mm"] - g["slot_y0_mm"],
        EXIT_YOKE_T + 4.0,
        g["slot_x0_mm"], g["slot_y0_mm"], EXIT_YOKE_Z0 - 2.0,
    )
    body = plate.cut(slot)
    z_wall_top = GAP0 + EXIT_WALL_H
    # bệ trên đỉnh vách 2 → dầm ngang (lọt dưới đáy đĩa cam) → cột lên tấm yoke
    post = _box(EXIT_RISER_POST_W, dy, EXIT_BEAM_Z1 - z_wall_top,
                x2, EXIT_RISER_Y0, z_wall_top)
    beam = _box(g["yoke_x1_mm"] - x2, dy, EXIT_BEAM_T,
                x2, EXIT_RISER_Y0, EXIT_BEAM_Z1 - EXIT_BEAM_T)
    riser = _box(g["yoke_x1_mm"] - g["slot_x1_mm"], dy,
                 EXIT_YOKE_Z1 - (EXIT_BEAM_Z1 - EXIT_BEAM_T),
                 g["slot_x1_mm"], EXIT_RISER_Y0, EXIT_BEAM_Z1 - EXIT_BEAM_T)
    for extra in (post, beam, riser):
        try:
            fused = body.fuse(extra)
            if _shape_ok(fused, 0.5 * float(getattr(body, "Volume", 1.0) or 1.0)):
                body = fused
        except Exception:
            continue
    return _refine(body)


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
    try:
        fused = body.fuse(_exit_yoke_plate(gap_mm))
        if _shape_ok(fused, 0.5 * float(getattr(body, "Volume", 1.0) or 1.0)):
            body = fused
    except Exception:
        pass
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
