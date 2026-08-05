"""
Adjustable_Chute — máng chữ nhật đáy hở, đặt sát mặt đĩa quay.

Truyền động: BÁNH RĂNG + THANH RĂNG (không vít me), dùng chung toán răng
ISO với model Rotary_Linear (spur_gear_math — răng pinion đồng nhất
polar-copy, rack cùng s/e/α/ha/hf, verify mesh).

2 núm xoay ĐỘC LẬP (2 trục riêng, không liên kết):
  Width_Knob_Pinion  — trục ĐỨNG (// Z) tại x=-30: pinion ăn khớp 2 thanh
                       răng nằm 2 phía đối diện → 2 vách tịnh tiến ngược
                       chiều = chỉnh BỀ RỘNG đối xứng. Vách treo trên ray,
                       đáy vách LUÔN ở z = GAP0 sát mặt đĩa.
  Height_Knob_Pinion — trục NGANG (// Y) tại x≈+76 (NGOÀI đầu máng,
                       x>45): pinion ăn khớp thanh răng đứng trên trụ
                       Height_Gate → giá treo tịnh tiến lên/xuống =
                       chỉnh CHIỀU CAO cửa. KHÔNG hạ độ cao vách đứng.
                       Toàn bộ cụm nằm ngoài phạm vi vách nên KHÔNG chặn
                       2 vách khép về 0.

NÓC ỐNG LỒNG (telescoping — không hở nóc khi chỉnh rộng):
  Roof_S (lớp dưới) + Roof_N (lớp trên) chồng mí nhau ở giữa.
  Mỗi tấm có ngàm (tab) trượt ĐỨNG trong rãnh trên mặt trong vách của nó
  → vách kéo tấm nóc theo khi chỉnh rộng (nóc luôn kín).
  Mỗi tấm có chốt đầu nấm trượt trong rãnh ngang của giá treo Height_Gate
  → cả 2 tấm cùng lên/xuống theo núm chỉnh cao, tự do trượt ngang.

Đáy máng RỖNG: sản phẩm trượt trực tiếp trên mặt đĩa quay (Rotor_Disc).
Chống xoay tấm trần: trụ + thanh răng trượt trong cửa sổ chữ nhật của
cầu trên (Frame_Top_Bridge).

Đường hầm dài CỐ ĐỊNH (90 mm); cửa chỉnh 0×0 → 25×25 mm.

HÃM BI LÒ XO (ball detent) — vặn núm thì tịnh tiến, nhả tay thì khóa:
  Detent_WN / Detent_WS — bi Ø2 + lò xo + ốc siết trên MỖI carriage vách,
      bi tì xuống hàng lỗ lõm (pitch 2 mm) trên mặt trên ray ngang
      → mỗi nấc = 2 mm hành trình vách = 4 mm bề rộng.
  Detent_H — bi ngang trong bầu trên nóc cầu, tì vào hàng lỗ lõm
      (pitch 2 mm) trên mặt trụ tấm trần → mỗi nấc = 2 mm chiều cao.
  Xoay núm: lực răng ép bi thụt lên nén lò xo → trượt sang nấc kế.
  Nhả tay: bi sập vào lỗ, giữ chặt. Ốc siết chỉnh lực giữ mạnh/nhẹ.
"""
from __future__ import annotations

import math
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import FreeCAD as App
import Part

from rotary_linear import (
    spur_gear_math,
    make_involute_pinion_local,
    make_involute_rack,
    verify_rack_pinion_mesh,
    verify_pinion_teeth_uniform,
    place_pinion_axis_y,
)

# ---------------------------------------------------------------------------
# Layout constants (mm). Disc top = Z0.
# ---------------------------------------------------------------------------
DISC_R = 65.0
DISC_T = 6.0            # disc z: -6..0
HUB_D = 24.0
HUB_Z0 = -14.0

GAP0 = 0.4              # khe đáy vách ↔ mặt đĩa (vách "sát" đĩa, không chạm)
WALL_T = 4.0
WALL_L = 90.0           # dọc X: -45..45
WALL_TOP = 40.0         # đỉnh vách; đáy z = GAP0 — CỐ ĐỊNH

RISER_X = 9.0
RISER_TOP = 68.0

BEAM_HX = 5.0
BEAM_Z0, BEAM_Z1 = 43.0, 51.0
BEAM_HY = 68.0

COL_HX = 8.0
COL_Y0, COL_Y1 = 68.0, 80.0
COL_Z0, COL_Z1 = -9.0, 70.0
FOOT_HX, FOOT_Y0, FOOT_Y1 = 18.0, 64.0, 96.0
FOOT_Z0, FOOT_Z1 = -14.0, -9.0

BRIDGE_Z0, BRIDGE_Z1 = 70.0, 78.0
ARM_X0, ARM_X1 = -44.0, 92.0
ARM_HY = 16.0
WIN_X0, WIN_X1, WIN_HY = 48.0, 72.0, 8.0   # cửa sổ dẫn hướng Height_Gate

# --- Shared gear math (giống Rotary_Linear) ---
GEAR_M = 1.5
GEAR_Z = 18
ALPHA_DEG = 20.0
TOOTH_CLEAR = 0.40
CENTER_BL = 0.25
FACE_W = 10.0

# Width drive: pinion trục Z tại (W_CX, 0), răng z 55..65
W_CX = -30.0
W_Z0 = 55.0
# Height drive (toàn bộ NGOÀI đầu máng, x > 45 — không chặn vách khép 0)
RACK_H_X = 62.0        # pitch-plane thanh răng đứng; pinion trục Y phía +X
H_ZPIN = 50.0

STEM_X0, STEM_X1 = 50.0, 57.0
STEM_TOP = 100.0

# Nóc ống lồng: 2 lớp, chốt đầu nấm vào rãnh giá treo
ROOF_T = 1.5           # dày mỗi lớp nóc
ROOF_GAP = 0.1         # khe giữa 2 lớp
ROOF_X0 = -42.0        # đầu -X của nóc
ROOF_PIN_N_X = 48.0    # chốt Roof_N (cánh giá treo phía tây trụ)
ROOF_PIN_S_X = 59.0    # chốt Roof_S (cánh giá treo phía đông trụ)
ROOF_PIN_D = 3.0
ROOF_TAB_X = 30.0      # tab trượt đứng tại x = ±30 trên vách

# Cửa 0×0 → 25×25 mm (đường hầm dài cố định WALL_L)
WIDTH_MIN, WIDTH_MAX = 0.0, 25.0
HEIGHT_MIN, HEIGHT_MAX = 0.0, 25.0
WIDTH_NOM, HEIGHT_NOM = 20.0, 14.0   # nominal phải nằm đúng nấc detent

# --- Ball detent (hãm bi lò xo) ---
DET_PITCH = 2.0        # nấc 2 mm hành trình
DET_BALL_R = 1.0       # bi Ø2
DET_POCKET_R = 1.1     # lỗ lõm cầu (bi hở 0.1)
DET_OFF = 0.55         # tâm lỗ lõm nhô khỏi mặt → sâu 0.55, miệng Ø1.9
DET_WX_N, DET_WX_S = 3.5, -3.5   # lệch X 2 cụm bi vách (không đụng khi khép 0)
DET_H_Z = 84.0         # cao độ bi ngang của detent chỉnh cao

COLORS = {
    "disc": (0.72, 0.72, 0.75),
    "frame": (0.38, 0.48, 0.60),
    "beam": (0.45, 0.55, 0.62),
    "wall": (0.25, 0.72, 0.35),
    "gate": (0.95, 0.55, 0.10),
    "knob": (0.45, 0.25, 0.55),
    "detent": (0.30, 0.30, 0.33),
}


def _refine(shape: Part.Shape) -> Part.Shape:
    try:
        out = shape.removeSplitter()
        return shape if out is None or out.isNull() else out
    except Exception:
        return shape


def _one(shape: Part.Shape) -> Part.Shape:
    shape = _refine(shape)
    sols = list(getattr(shape, "Solids", []) or [])
    if len(sols) <= 1:
        return shape
    out = sols[0]
    for s in sols[1:]:
        try:
            out = out.fuse(s)
        except Exception:
            pass
    return _refine(out)


def _nsol(shape: Part.Shape) -> int:
    return len(list(getattr(shape, "Solids", []) or []))


def _box(dx, dy, dz, x0, y0, z0) -> Part.Shape:
    b = Part.makeBox(dx, dy, dz)
    b.translate(App.Vector(x0, y0, z0))
    return b


def _cyl_z(d, h, x, y, z0) -> Part.Shape:
    c = Part.makeCylinder(d / 2.0, h)
    c.translate(App.Vector(x, y, z0))
    return c


def _cyl_y(d, length, x, y0, z) -> Part.Shape:
    c = Part.makeCylinder(d / 2.0, length)
    c.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), -90.0)
    c.translate(App.Vector(x, y0, z))
    return c


def _cyl_x(d, length, x0, y, z) -> Part.Shape:
    c = Part.makeCylinder(d / 2.0, length)
    c.rotate(App.Vector(0, 0, 0), App.Vector(0, 1, 0), 90.0)
    c.translate(App.Vector(x0, y, z))
    return c


def _sphere(r, x, y, z) -> Part.Shape:
    s = Part.makeSphere(r)
    s.translate(App.Vector(x, y, z))
    return s


def _on_grid(value: float, grid_vals: list) -> bool:
    return any(abs(value - gv) < 0.05 for gv in grid_vals)


def _w_grid() -> list:
    """Tâm lỗ lõm trên ray (|y|): nấc bề rộng 0,4,...,24 → yc = half+2."""
    return [2.0 + k * DET_PITCH for k in range(7)]   # 2..14


def _h_grid(h_nom: float) -> list:
    """Tọa độ z lỗ lõm trên trụ gate (xây tại nominal h_nom).

    Lỗ z_d ăn khớp bi (world z = DET_H_Z) khi h = h_nom + DET_H_Z - z_d.
    """
    return [DET_H_Z + h_nom - (k * DET_PITCH) for k in range(13)]  # h 0..24


def _flutes_y(knob, grip_od, knob_h, x, y0, z):
    for i in range(8):
        a = math.radians(i * 45.0)
        fr = grip_od / 2.0 - 0.5
        knob = knob.cut(
            _cyl_y(4.4, knob_h + 0.6,
                   x + fr * math.cos(a), y0 - 0.3, z + fr * math.sin(a)))
    return knob


def _flutes_z(knob, grip_od, knob_h, x, y, z0):
    for i in range(8):
        a = math.radians(i * 45.0)
        fr = grip_od / 2.0 - 0.5
        knob = knob.cut(
            _cyl_z(4.4, knob_h + 0.6,
                   x + fr * math.cos(a), y + fr * math.sin(a), z0 - 0.3))
    return knob


def _rack_along_y(
    g: dict,
    *,
    x_pitch: float,
    dirx: float,
    y0: float,
    y1: float,
    z0: float,
    face_z: float,
    body_t: float,
) -> Part.Shape:
    """Thanh răng tịnh tiến theo Y — CÙNG toán răng spur_gear_math.

    dirx=+1: răng chỉa +X; dirx=-1: răng chỉa -X.
    Phase: KHOẢNG TRỐNG (space) căn giữa y=0 (điểm ăn khớp với pinion
    tại y=0) → tâm răng tại (i+0.5)·p, giống make_involute_rack.
    """
    p = g["circular_pitch"]
    ha, hf = g["addendum"], g["dedendum"]
    th = g["tooth_half_w"]
    x_tip = x_pitch + dirx * ha
    x_root = x_pitch - dirx * hf
    h_tip = th(+ha)
    h_root = th(-hf)
    if h_root <= h_tip:
        h_root = h_tip + 0.5
    body = _box(body_t, y1 - y0, face_z,
                min(x_root, x_root - dirx * body_t), y0, z0)
    solid = body
    i0 = int(math.floor(y0 / p)) - 2
    i1 = int(math.ceil(y1 / p)) + 2
    for i in range(i0, i1 + 1):
        yc = (i + 0.5) * p
        if yc - h_root < y0 + 0.02 or yc + h_root > y1 - 0.02:
            continue
        pts = [
            App.Vector(x_root, yc - h_root, 0.0),
            App.Vector(x_tip, yc - h_tip, 0.0),
            App.Vector(x_tip, yc + h_tip, 0.0),
            App.Vector(x_root, yc + h_root, 0.0),
            App.Vector(x_root, yc - h_root, 0.0),
        ]
        tooth = Part.Face(Part.makePolygon(pts)).extrude(
            App.Vector(0, 0, face_z))
        tooth.translate(App.Vector(0, 0, z0))
        solid = solid.fuse(tooth)
    return _one(solid)


def _check_clear(pairs: list) -> None:
    bad = []
    for name_a, sa, name_b, sb, max_mm3 in pairs:
        try:
            com = sa.common(sb)
            vol = float(com.Volume) if com is not None and not com.isNull() else 0.0
        except Exception:
            vol = -1.0
        ok = 0.0 <= vol <= max_mm3
        print("ADJ_clear %s vs %s: overlap=%.3f mm3 (max %.2f) -> %s"
              % (name_a, name_b, vol, max_mm3, "PASS" if ok else "FAIL"))
        if not ok:
            bad.append((name_a, name_b, vol))
    if bad:
        raise RuntimeError("Adjustable_Chute collision: %s" % bad)


def make_disc() -> Part.Shape:
    disc = _cyl_z(2.0 * DISC_R, DISC_T, 0, 0, -DISC_T)
    hub = _cyl_z(HUB_D, -HUB_Z0 - DISC_T, 0, 0, HUB_Z0)
    disc = _one(disc.fuse(hub))
    for i in range(12):
        a = math.radians(i * 30.0)
        disc = disc.cut(_cyl_z(5.0, 1.4, 58.0 * math.cos(a), 58.0 * math.sin(a), -1.2))
    return _one(disc)


def make_wall(half: float, side: float, g: dict) -> Part.Shape:
    """Vách + carriage trượt trên ray + thanh răng ngang (// Y).

    side=+1 → vách N (y half..half+4), rack phía +X của pinion, răng chỉa -X.
    side=-1 → vách S, rack phía -X của pinion, răng chỉa +X.
    Đáy vách z = GAP0 cố định — carriage chỉ tịnh tiến theo Y.
    """
    r = g["pitch_radius"]
    y0 = half if side > 0 else -half - WALL_T
    wall = _box(WALL_L, WALL_T, WALL_TOP - GAP0, -WALL_L / 2.0, y0, GAP0)
    riser = _box(2 * RISER_X, WALL_T, RISER_TOP - WALL_TOP, -RISER_X, y0, WALL_TOP)
    sol = _one(wall.fuse(riser))
    if side > 0:
        x_pitch = W_CX + r + CENTER_BL
        rack = _rack_along_y(g, x_pitch=x_pitch, dirx=-1.0, y0=-26.0, y1=36.0,
                             z0=W_Z0, face_z=FACE_W, body_t=4.0)
        # link nối thân rack (mặt +X tại x_root) vào riser — CHỈ trong dải y
        # của vách N, để không đụng riser vách S
        x_root = x_pitch + g["dedendum"]
        link = _box((-8.0) - (x_root - 0.3), WALL_T, FACE_W,
                    x_root - 0.3, y0, W_Z0)
        sol = _one(sol.fuse(rack).fuse(link))
    else:
        x_pitch = W_CX - r - CENTER_BL
        rack = _rack_along_y(g, x_pitch=x_pitch, dirx=+1.0, y0=-36.0, y1=26.0,
                             z0=W_Z0, face_z=FACE_W, body_t=4.0)
        x_root = x_pitch - g["dedendum"]
        # thân rack hạ xuống z 44 + cánh tay ngang dưới pinion về riser S
        drop = _box(4.0, 62.0, W_Z0 - 44.0 + 1.0, x_root - 4.0, -36.0, 44.0)
        arm = _box((-8.0) - (x_root - 0.3), WALL_T, 9.0, x_root - 0.3, y0, 44.0)
        sol = _one(sol.fuse(rack).fuse(drop).fuse(arm))
    # slot ôm ray ngang (clearance 0.4)
    slot = _box(2 * BEAM_HX + 0.8, WALL_T + 8.0, (BEAM_Z1 - BEAM_Z0) + 0.8,
                -(BEAM_HX + 0.4), y0 - 3.0, BEAM_Z0 - 0.4)
    sol = _one(sol.cut(slot))
    # lỗ đứng Ø2.4 lắp cụm bi-lò-xo detent, xuyên riser xuống mặt ray
    x_det = DET_WX_N if side > 0 else DET_WX_S
    sol = _one(sol.cut(_cyl_z(2.4, 18.0, x_det, y0 + 2.0, BEAM_Z0 + 8.0)))
    # RÃNH THOÁT (recess) 2.05 mm dọc mặt trong phần dưới vách (z 0.3..28.7)
    # → mép tấm nóc đối diện trượt lọt vào trong vách khi khép về 0
    if side > 0:
        ry0 = half - 0.05
    else:
        ry0 = -half - 2.0
    recess = _box(WALL_L + 2.0, 2.05, 28.4, -WALL_L / 2.0 - 1.0, ry0, 0.3)
    sol = _one(sol.cut(recess))
    # 2 ngàm trượt ĐỨNG (sâu hơn recess) cho tab của tấm nóc phía mình
    # (tab trượt dọc Z khi chỉnh cao; vách kéo nóc theo khi chỉnh rộng)
    if side > 0:
        gy0 = half + 2.0
    else:
        gy0 = -half - 3.45
    for gx in (ROOF_TAB_X, -ROOF_TAB_X):
        groove = _box(6.7, 1.45, 28.4, gx - 3.35, gy0, 0.3)
        sol = _one(sol.cut(groove))
    return sol


def make_frame_column(side: float) -> Part.Shape:
    y0 = COL_Y0 if side > 0 else -COL_Y1
    col = _box(2 * COL_HX, COL_Y1 - COL_Y0, COL_Z1 - COL_Z0, -COL_HX, y0, COL_Z0)
    fy0 = FOOT_Y0 if side > 0 else -FOOT_Y1
    foot = _box(2 * FOOT_HX, FOOT_Y1 - FOOT_Y0, FOOT_Z1 - FOOT_Z0,
                -FOOT_HX, fy0, FOOT_Z0)
    return _one(col.fuse(foot))


def make_rail_beam() -> Part.Shape:
    """Ray ngang + 2 hàng lỗ lõm detent (pitch 2 mm) trên mặt trên."""
    beam = _box(2 * BEAM_HX, 2 * BEAM_HY, BEAM_Z1 - BEAM_Z0,
                -BEAM_HX, -BEAM_HY, BEAM_Z0)
    zc = BEAM_Z1 + DET_OFF
    for yg in _w_grid():
        beam = beam.cut(_sphere(DET_POCKET_R, DET_WX_N, yg, zc))
        beam = beam.cut(_sphere(DET_POCKET_R, DET_WX_S, -yg, zc))
    return _one(beam)


def make_top_bridge(h_cx: float) -> Part.Shape:
    """Cầu trên: dầm Y + cánh tay X, cửa sổ dẫn hướng gate, 2 ổ trục."""
    bridge = _box(16.0, 148.0, BRIDGE_Z1 - BRIDGE_Z0, -8.0, -74.0, BRIDGE_Z0)
    arm = _box(ARM_X1 - ARM_X0, 2 * ARM_HY, BRIDGE_Z1 - BRIDGE_Z0,
               ARM_X0, -ARM_HY, BRIDGE_Z0)
    sol = _one(bridge.fuse(arm))
    # 2 bản treo ổ trục pinion chỉnh cao (trục // Y)
    for ys in (-ARM_HY, ARM_HY - 4.0):
        plate = _box(16.0, 4.0, BRIDGE_Z0 + 1.0 - 42.0, h_cx - 8.0, ys, 42.0)
        sol = _one(sol.fuse(plate))
    # bầu đỡ cụm bi detent chỉnh cao (bi ngang tì vào mặt -X trụ gate)
    boss = _box(STEM_X0 - 0.8 - 35.8, 10.0, 12.0, 35.8, -5.0, BRIDGE_Z1)
    sol = _one(sol.fuse(boss))
    # cửa sổ chữ nhật: trụ + thanh răng gate trượt qua (chống xoay)
    win = _box(WIN_X1 - WIN_X0, 2 * WIN_HY, 12.0, WIN_X0, -WIN_HY, BRIDGE_Z0 - 2.0)
    sol = _one(sol.cut(win))
    # ổ trục đứng cho Width_Knob_Pinion
    sol = _one(sol.cut(_cyl_z(8.5, 12.0, W_CX, 0.0, BRIDGE_Z0 - 2.0)))
    # ổ trục ngang xuyên 2 bản treo cho Height_Knob_Pinion
    sol = _one(sol.cut(_cyl_y(8.5, 2 * ARM_HY + 8.0, h_cx, -ARM_HY - 4.0, H_ZPIN)))
    # lỗ ngang Ø2.4 xuyên bầu detent (bi + lò xo + ốc siết từ phía -X)
    sol = _one(sol.cut(_cyl_x(2.4, 16.0, 34.0, 0.0, DET_H_Z)))
    return sol


def make_width_knob_pinion(local: Part.Shape) -> Part.Shape:
    """Pinion trục Z + trục + núm trên đỉnh (1 chi tiết). Núm độc lập."""
    pin = local.copy()
    pin.translate(App.Vector(W_CX, 0.0, W_Z0))
    shaft = _cyl_z(8.0, 92.0 - 60.0, W_CX, 0.0, 60.0)
    c1 = _cyl_z(13.0, 2.0, W_CX, 0.0, 67.6)   # vòng chặn dưới cầu
    c2 = _cyl_z(13.0, 2.0, W_CX, 0.0, 78.4)   # vòng chặn trên cầu
    knob = _cyl_z(28.0, 5.0, W_CX, 0.0, 92.0).fuse(
        _cyl_z(22.0, 14.0, W_CX, 0.0, 92.0))
    knob = _flutes_z(knob, 22.0, 14.0, W_CX, 0.0, 92.0)
    return _one(pin.fuse(shaft).fuse(c1).fuse(c2).fuse(knob))


def make_height_knob_pinion(local: Part.Shape, h_cx: float) -> Part.Shape:
    """Pinion trục Y + trục + núm phía +Y (1 chi tiết). Núm độc lập."""
    loc = local.copy()
    loc.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 180.0)
    pin = place_pinion_axis_y(loc, face_w=FACE_W, x=h_cx, y=0.0, z=H_ZPIN)
    shaft = _cyl_y(8.0, 26.0 - (-17.0), h_cx, -17.0, H_ZPIN)
    c1 = _cyl_y(13.0, 2.0, h_cx, -11.7, H_ZPIN)   # chặn trong bản treo S
    c2 = _cyl_y(13.0, 2.0, h_cx, 16.3, H_ZPIN)    # chặn ngoài bản treo N
    knob = _cyl_y(28.0, 5.0, h_cx, 26.0, H_ZPIN).fuse(
        _cyl_y(22.0, 14.0, h_cx, 26.0, H_ZPIN))
    knob = _flutes_y(knob, 22.0, 14.0, h_cx, 26.0, H_ZPIN)
    return _one(pin.fuse(shaft).fuse(c1).fuse(c2).fuse(knob))


def make_height_gate(height_open: float) -> Part.Shape:
    """Giá treo nóc + trụ + thanh răng đứng (1 chi tiết tịnh tiến dọc Z).

    Toàn bộ nằm NGOÀI đầu máng (x >= 46 > 45) → không chặn vách khép 0.
    2 cánh giá treo (wing W/E) có rãnh ngang: chốt đầu nấm của Roof_N/S
    trượt trong rãnh (cùng lên/xuống, tự do trượt ngang theo vách).
    Trụ + rack trượt trong cửa sổ cầu trên → chống xoay.
    Mặt -X trụ (x=STEM_X0) có hàng lỗ lõm detent (pitch 2 mm).
    """
    zb = GAP0 + height_open
    c0, c1 = zb + 3.2, zb + 5.2
    wing_w = _box(50.4 - 46.0, 32.0, c1 - c0, 46.0, -16.0, c0)
    wing_e = _box(61.4 - 56.6, 32.0, c1 - c0, 56.6, -16.0, c0)
    post_n = _box(9.0, 2.5, (zb + 9.0) - c0, 48.0, 13.5, c0)
    post_s = _box(9.0, 2.5, (zb + 9.0) - c0, 48.0, -16.0, c0)
    crossbar = _box(9.0, 32.0, 3.0, 48.0, -16.0, zb + 8.0)
    stem = _box(STEM_X1 - STEM_X0, 8.0, STEM_TOP - (zb + 8.0),
                STEM_X0, -4.0, zb + 8.0)
    rack = make_involute_rack(
        module=GEAR_M,
        length_z=56.0,
        face_y=8.0,
        body_t=4.0,
        x_pitch=RACK_H_X,
        y0=-4.0,
        z0=zb + 12.0,
        mesh_z=H_ZPIN,
        alpha_deg=ALPHA_DEG,
        tooth_clear=TOOTH_CLEAR,
        pinion_teeth=GEAR_Z,
    )
    sol = _one(wing_w.fuse(wing_e).fuse(post_n).fuse(post_s)
               .fuse(crossbar).fuse(stem).fuse(rack))
    # rãnh ngang cho chốt nóc (slot // Y, hở đầu để chốt chạy hết hành trình)
    slot_n = _box(3.4, 17.0, c1 - c0 + 1.0,
                  ROOF_PIN_N_X - 1.7, -4.5, c0 - 0.5)
    slot_s = _box(3.4, 17.0, c1 - c0 + 1.0,
                  ROOF_PIN_S_X - 1.7, -12.5, c0 - 0.5)
    sol = _one(sol.cut(slot_n).cut(slot_s))
    # hàng lỗ lõm detent trên mặt -X của trụ (x = STEM_X0)
    for zd in _h_grid(height_open):
        sol = sol.cut(_sphere(DET_POCKET_R, STEM_X0 - DET_OFF, 0.0, zd))
    return _one(sol)


def make_roof(half: float, height_open: float, side: float) -> Part.Shape:
    """Tấm nóc ống lồng (2 lớp chồng mí — nóc luôn kín khi chỉnh rộng).

    side=-1 → Roof_S lớp DƯỚI (mặt dưới = chiều cao cửa), chốt tại x=59.
    side=+1 → Roof_N lớp TRÊN (chồng lên S), chốt tại x=48.
    Tab tại x=±30 trượt đứng trong rãnh mặt trong vách → vách kéo nóc
    theo khi chỉnh rộng; chốt đầu nấm trượt trong rãnh giá treo → nóc
    lên/xuống cùng Height_Gate.
    """
    zb = GAP0 + height_open
    if side < 0:
        z0, z1 = zb, zb + ROOF_T
        x1 = 63.0
        # tấm chính: từ sát vách S tới +1.95 (mép lọt vào recess vách N khi khép)
        y0, y1 = -half + 0.3, 1.95
        # tab xuyên qua recess vách S vào ngàm sâu (y -half-3.45..-half-2.0)
        y_tab0, y_tab1 = -half - 3.1, -half + 0.4
        # cánh tay mang chốt: chỉ ở x>=46 (ngoài vách) → không cấn vách
        ya0, ya1 = -half + 0.3, max(2.0, -half + 4.5)
        x_pin, y_pin = ROOF_PIN_S_X, -half + 2.5
    else:
        z0, z1 = zb + ROOF_T + ROOF_GAP, zb + 2.0 * ROOF_T + ROOF_GAP
        x1 = 52.0
        y0, y1 = -1.95, half - 0.3
        y_tab0, y_tab1 = half - 0.4, half + 3.1
        ya0, ya1 = min(-1.95, half - 5.0), half - 0.3
        x_pin, y_pin = ROOF_PIN_N_X, half - 2.5
    plate = _box(x1 - ROOF_X0, y1 - y0, z1 - z0, ROOF_X0, y0, z0)
    arm = _box(x1 - 46.0, ya1 - ya0, z1 - z0, 46.0, ya0, z0)
    sol = plate.fuse(arm)
    for gx in (ROOF_TAB_X, -ROOF_TAB_X):
        tab = _box(6.0, y_tab1 - y_tab0, z1 - z0, gx - 3.0, y_tab0, z0)
        sol = sol.fuse(tab)
    # chốt đầu nấm: thân Ø3 xuyên rãnh giá treo + mũ Ø6 giữ theo Z
    pin = _cyl_z(ROOF_PIN_D, (zb + 5.5) - (z1 - 0.2), x_pin, y_pin, z1 - 0.2)
    cap = _cyl_z(6.0, 1.5, x_pin, y_pin, zb + 5.5)
    return _one(sol.fuse(pin).fuse(cap))


def make_detent_w(half: float, side: float) -> Part.Shape:
    """Cụm bi + lò xo + ốc siết trên carriage vách (bi tì xuống ray).

    Bi sập vào lỗ lõm khi carriage đúng nấc; lệch nấc thì bi nén lên
    trượt trên mặt ray. Ốc siết phía trên đỉnh riser chỉnh lực lò xo.
    """
    x = DET_WX_N if side > 0 else DET_WX_S
    yc = (half + 2.0) * (1.0 if side > 0 else -1.0)
    seated = _on_grid(abs(yc), _w_grid())
    zb = BEAM_Z1 + DET_OFF if seated else BEAM_Z1 + DET_BALL_R + 0.05
    ball = _sphere(DET_BALL_R, x, yc, zb)
    spring = _cyl_z(1.8, 58.0 - (zb + DET_BALL_R - 0.3), x, yc,
                    zb + DET_BALL_R - 0.3)
    shank = _cyl_z(2.3, 69.2 - 57.7, x, yc, 57.7)
    head = _cyl_z(6.0, 2.5, x, yc, 69.0)
    return _one(ball.fuse(spring).fuse(shank).fuse(head))


def make_detent_h(height_open: float) -> Part.Shape:
    """Cụm bi ngang trong bầu trên cầu, tì vào hàng lỗ trên trụ gate."""
    seated = _on_grid(DET_H_Z, _h_grid(height_open))
    xb = (STEM_X0 - DET_OFF) if seated else (STEM_X0 - DET_BALL_R - 0.05)
    ball = _sphere(DET_BALL_R, xb, 0.0, DET_H_Z)
    spring = _cyl_x(1.8, (xb - DET_BALL_R + 0.3) - 42.0, 42.0, 0.0, DET_H_Z)
    shank = _cyl_x(2.3, 42.3 - 35.6, 35.6, 0.0, DET_H_Z)
    head = _cyl_x(6.0, 3.0, 32.8, 0.0, DET_H_Z)
    return _one(ball.fuse(spring).fuse(shank).fuse(head))


def build_adjustable_chute_parts(
    width_open: float = WIDTH_NOM,
    height_open: float = HEIGHT_NOM,
) -> list:
    width_open = max(WIDTH_MIN, min(WIDTH_MAX, float(width_open)))
    height_open = max(HEIGHT_MIN, min(HEIGHT_MAX, float(height_open)))
    half = width_open / 2.0

    g = spur_gear_math(GEAR_M, GEAR_Z, alpha_deg=ALPHA_DEG,
                       tooth_clear=TOOTH_CLEAR)
    r = g["pitch_radius"]
    h_cx = RACK_H_X + r + CENTER_BL
    travel = g["travel_per_turn"]

    # --- Pinion local (trục Z tại gốc) — răng đồng nhất polar copy ---
    local = make_involute_pinion_local(
        module=GEAR_M, teeth=GEAR_Z, face_w=FACE_W, bore=0.0,
        alpha_deg=ALPHA_DEG, tooth_clear=TOOTH_CLEAR)
    uni = verify_pinion_teeth_uniform(local, g, face_w=FACE_W)
    print("ADJ_pinion tooth_uniform: %s — max_rel_dev=%.4f"
          % ("PASS" if uni["pass"] else "FAIL",
             float(uni.get("max_rel_dev", 0.0))))
    if not uni["pass"]:
        raise RuntimeError("Pinion teeth not identical: %s"
                           % uni.get("reason", uni))
    # hub phủ 0.25 mm vào chân răng → hàn răng + hub thành 1 solid
    # (rack tip chỉ ăn tới bán kính r-ha+bl = 12.25 > 11.875 → không cấn)
    hub_weld = _cyl_z(2.0 * (g["root_radius"] + 0.25), FACE_W, 0.0, 0.0, 0.0)
    local = _one(local.fuse(hub_weld))

    disc = make_disc()
    wall_s = make_wall(half, -1.0, g)
    wall_n = make_wall(half, +1.0, g)
    col_s = make_frame_column(-1.0)
    col_n = make_frame_column(+1.0)
    beam = make_rail_beam()
    bridge = make_top_bridge(h_cx)
    knob_w = make_width_knob_pinion(local)
    knob_h = make_height_knob_pinion(local, h_cx)
    gate = make_height_gate(height_open)
    roof_s = make_roof(half, height_open, -1.0)
    roof_n = make_roof(half, height_open, +1.0)
    det_wn = make_detent_w(half, +1.0)
    det_ws = make_detent_w(half, -1.0)
    det_h = make_detent_h(height_open)

    # ------------------------------------------------------------------
    # Verify mesh: pinion vs từng rack (shape rack tách riêng để đo)
    # ------------------------------------------------------------------
    pin_w = local.copy()
    pin_w.translate(App.Vector(W_CX, 0.0, W_Z0))
    loc_h = local.copy()
    loc_h.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 180.0)
    pin_h = place_pinion_axis_y(loc_h, face_w=FACE_W, x=h_cx, y=0.0, z=H_ZPIN)

    rack_n = _rack_along_y(g, x_pitch=W_CX + r + CENTER_BL, dirx=-1.0,
                           y0=-26.0, y1=36.0, z0=W_Z0, face_z=FACE_W,
                           body_t=4.0)
    rack_s = _rack_along_y(g, x_pitch=W_CX - r - CENTER_BL, dirx=+1.0,
                           y0=-36.0, y1=26.0, z0=W_Z0, face_z=FACE_W,
                           body_t=4.0)
    rack_h = make_involute_rack(
        module=GEAR_M, length_z=56.0, face_y=8.0, body_t=4.0,
        x_pitch=RACK_H_X, y0=-4.0, z0=GAP0 + height_open + 12.0,
        mesh_z=H_ZPIN,
        alpha_deg=ALPHA_DEG, tooth_clear=TOOTH_CLEAR, pinion_teeth=GEAR_Z)

    for lbl, pin, rk in (("W_rack_N", pin_w, rack_n),
                         ("W_rack_S", pin_w, rack_s),
                         ("H_rack", pin_h, rack_h)):
        m = verify_rack_pinion_mesh(pin, rk)
        ov = m.get("overlap_mm3")
        print("ADJ_mesh %s: %s — overlap=%.2f mm3"
              % (lbl, "PASS" if m["pass"] else "FAIL",
                 ov if ov is not None else -1.0))
        if not m["pass"]:
            raise RuntimeError("Rack/pinion collide (%s): %s" % (lbl, m))

    # Conjugate spot-check: xoay pinion nửa răng + tịnh tiến rack r·θ
    ang = 0.5 * 360.0 / GEAR_Z
    dth = r * math.radians(ang)
    loc2 = make_involute_pinion_local(
        module=GEAR_M, teeth=GEAR_Z, face_w=FACE_W, bore=0.0,
        alpha_deg=ALPHA_DEG, tooth_clear=TOOTH_CLEAR)
    loc2.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), ang)
    pin_w2 = loc2.copy()
    pin_w2.translate(App.Vector(W_CX, 0.0, W_Z0))
    rk_n2 = rack_n.copy()
    rk_n2.translate(App.Vector(0.0, dth, 0.0))
    rk_s2 = rack_s.copy()
    rk_s2.translate(App.Vector(0.0, -dth, 0.0))
    loc3 = make_involute_pinion_local(
        module=GEAR_M, teeth=GEAR_Z, face_w=FACE_W, bore=0.0,
        alpha_deg=ALPHA_DEG, tooth_clear=TOOTH_CLEAR)
    loc3.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 180.0 + ang)
    pin_h2 = place_pinion_axis_y(loc3, face_w=FACE_W, x=h_cx, y=0.0, z=H_ZPIN)
    rk_h2 = rack_h.copy()
    rk_h2.translate(App.Vector(0.0, 0.0, dth))
    for lbl, pin, rk in (("W_rack_N@%.0f°" % ang, pin_w2, rk_n2),
                         ("W_rack_S@%.0f°" % ang, pin_w2, rk_s2),
                         ("H_rack@%.0f°" % ang, pin_h2, rk_h2)):
        m = verify_rack_pinion_mesh(pin, rk)
        ov = m.get("overlap_mm3")
        print("ADJ_mesh_conj %s: %s — overlap=%.2f mm3"
              % (lbl, "PASS" if m["pass"] else "FAIL",
                 ov if ov is not None else -1.0))
        if not m["pass"]:
            raise RuntimeError("Rack/pinion jam conjugate (%s): %s" % (lbl, m))

    print("ADJ_opening: width=%.1f (range %.0f..%.0f) height=%.1f "
          "(range %.0f..%.0f) | đường hầm dài CỐ ĐỊNH %.0f mm"
          % (width_open, WIDTH_MIN, WIDTH_MAX,
             height_open, HEIGHT_MIN, HEIGHT_MAX, WALL_L))
    print("ADJ_wall: bottom z=%.1f (sát đĩa, KHÔNG đổi khi chỉnh) top z=%.1f"
          % (GAP0, WALL_TOP))
    print("ADJ_gear: m=%.1f z=%d α=%.0f° | %.1f mm/vòng | 2 núm ĐỘC LẬP "
          "(2 trục riêng)" % (GEAR_M, GEAR_Z, ALPHA_DEG, travel))
    print("ADJ_detent: bi Ø%.0f, lỗ lõm pitch %.0f mm | nấc cao=%.0f mm, "
          "nấc rộng=%.0f mm | vặn núm → bi nén lên; nhả tay → bi sập "
          "vào lỗ KHÓA CỨNG; ốc siết chỉnh lực"
          % (2 * DET_BALL_R, DET_PITCH, DET_PITCH, 2 * DET_PITCH))
    print("ADJ_detent_seated: WN=%s WS=%s H=%s (nominal đúng nấc?)"
          % (_on_grid(half + 2.0, _w_grid()),
             _on_grid(half + 2.0, _w_grid()),
             _on_grid(DET_H_Z, _h_grid(height_open))))
    print("ADJ_roof: ống lồng 2 lớp — Roof_S dưới + Roof_N trên chồng mí, "
          "tab trượt đứng trong rãnh vách → nóc KÍN mọi bề rộng, vách "
          "khép được về 0 (cụm chỉnh cao nằm ngoài x>45)")
    for name, sh in (("Side_Wall_S", wall_s), ("Side_Wall_N", wall_n),
                     ("Height_Gate", gate), ("Frame_Top_Bridge", bridge),
                     ("Roof_S", roof_s), ("Roof_N", roof_n),
                     ("Width_Knob_Pinion", knob_w),
                     ("Height_Knob_Pinion", knob_h),
                     ("Detent_WN", det_wn), ("Detent_WS", det_ws),
                     ("Detent_H", det_h)):
        print("ADJ_solids %s: %d (want 1)" % (name, _nsol(sh)))

    TIGHT = 0.05
    MESH = 8.0
    _check_clear([
        # cặp ăn khớp răng — cho phép overlap mesh nhỏ
        ("Height_Gate", gate, "Height_Knob_Pinion", knob_h, MESH),
        ("Side_Wall_N", wall_n, "Width_Knob_Pinion", knob_w, MESH),
        ("Side_Wall_S", wall_s, "Width_Knob_Pinion", knob_w, MESH),
        # còn lại: không được chạm
        ("Height_Gate", gate, "Side_Wall_S", wall_s, TIGHT),
        ("Height_Gate", gate, "Side_Wall_N", wall_n, TIGHT),
        ("Height_Gate", gate, "Frame_Top_Bridge", bridge, TIGHT),
        ("Height_Gate", gate, "Width_Knob_Pinion", knob_w, TIGHT),
        ("Height_Gate", gate, "Frame_Rail_Beam", beam, TIGHT),
        ("Side_Wall_S", wall_s, "Side_Wall_N", wall_n, TIGHT),
        ("Side_Wall_S", wall_s, "Rotor_Disc", disc, TIGHT),
        ("Side_Wall_N", wall_n, "Rotor_Disc", disc, TIGHT),
        ("Side_Wall_S", wall_s, "Frame_Rail_Beam", beam, TIGHT),
        ("Side_Wall_N", wall_n, "Frame_Rail_Beam", beam, TIGHT),
        ("Side_Wall_S", wall_s, "Frame_Top_Bridge", bridge, TIGHT),
        ("Side_Wall_N", wall_n, "Frame_Top_Bridge", bridge, TIGHT),
        ("Side_Wall_S", wall_s, "Height_Knob_Pinion", knob_h, TIGHT),
        ("Side_Wall_N", wall_n, "Height_Knob_Pinion", knob_h, TIGHT),
        ("Width_Knob_Pinion", knob_w, "Frame_Top_Bridge", bridge, TIGHT),
        ("Width_Knob_Pinion", knob_w, "Frame_Rail_Beam", beam, TIGHT),
        ("Width_Knob_Pinion", knob_w, "Height_Knob_Pinion", knob_h, TIGHT),
        ("Height_Knob_Pinion", knob_h, "Frame_Top_Bridge", bridge, TIGHT),
        ("Height_Knob_Pinion", knob_h, "Frame_Rail_Beam", beam, TIGHT),
        ("Frame_Column_S", col_s, "Rotor_Disc", disc, TIGHT),
        ("Frame_Column_N", col_n, "Rotor_Disc", disc, TIGHT),
        # detent: bi/lò xo/ốc không được cấn ray, vách, cầu, gate
        ("Detent_WN", det_wn, "Frame_Rail_Beam", beam, TIGHT),
        ("Detent_WN", det_wn, "Side_Wall_N", wall_n, TIGHT),
        ("Detent_WN", det_wn, "Side_Wall_S", wall_s, TIGHT),
        ("Detent_WS", det_ws, "Frame_Rail_Beam", beam, TIGHT),
        ("Detent_WS", det_ws, "Side_Wall_S", wall_s, TIGHT),
        ("Detent_WS", det_ws, "Side_Wall_N", wall_n, TIGHT),
        ("Detent_WN", det_wn, "Detent_WS", det_ws, TIGHT),
        ("Detent_H", det_h, "Height_Gate", gate, TIGHT),
        ("Detent_H", det_h, "Frame_Top_Bridge", bridge, TIGHT),
        ("Detent_H", det_h, "Height_Knob_Pinion", knob_h, TIGHT),
        ("Detent_WN", det_wn, "Width_Knob_Pinion", knob_w, TIGHT),
        # nóc ống lồng: không chạm nhau / vách / giá treo / đĩa / pinion
        ("Roof_S", roof_s, "Roof_N", roof_n, TIGHT),
        ("Roof_S", roof_s, "Side_Wall_S", wall_s, TIGHT),
        ("Roof_S", roof_s, "Side_Wall_N", wall_n, TIGHT),
        ("Roof_N", roof_n, "Side_Wall_N", wall_n, TIGHT),
        ("Roof_N", roof_n, "Side_Wall_S", wall_s, TIGHT),
        ("Roof_S", roof_s, "Height_Gate", gate, TIGHT),
        ("Roof_N", roof_n, "Height_Gate", gate, TIGHT),
        ("Roof_S", roof_s, "Rotor_Disc", disc, TIGHT),
        ("Roof_N", roof_n, "Rotor_Disc", disc, TIGHT),
        ("Roof_S", roof_s, "Height_Knob_Pinion", knob_h, TIGHT),
        ("Roof_N", roof_n, "Height_Knob_Pinion", knob_h, TIGHT),
        ("Roof_S", roof_s, "Frame_Rail_Beam", beam, TIGHT),
        ("Roof_N", roof_n, "Frame_Rail_Beam", beam, TIGHT),
        ("Roof_S", roof_s, "Detent_H", det_h, TIGHT),
    ])

    return [
        ("Rotor_Disc", disc, COLORS["disc"]),
        ("Side_Wall_S", wall_s, COLORS["wall"]),
        ("Side_Wall_N", wall_n, COLORS["wall"]),
        ("Height_Gate", gate, COLORS["gate"]),
        ("Roof_S", roof_s, COLORS["gate"]),
        ("Roof_N", roof_n, (0.98, 0.72, 0.25)),
        ("Frame_Column_S", col_s, COLORS["frame"]),
        ("Frame_Column_N", col_n, COLORS["frame"]),
        ("Frame_Rail_Beam", beam, COLORS["beam"]),
        ("Frame_Top_Bridge", bridge, COLORS["frame"]),
        ("Width_Knob_Pinion", knob_w, COLORS["knob"]),
        ("Height_Knob_Pinion", knob_h, COLORS["knob"]),
        ("Detent_WN", det_wn, COLORS["detent"]),
        ("Detent_WS", det_ws, COLORS["detent"]),
        ("Detent_H", det_h, COLORS["detent"]),
    ]
