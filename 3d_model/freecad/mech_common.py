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

DISC_D = 200.0
DISC_T = 5.0
DISC_R = 0.5 * DISC_D
HUB_D = 28.0
HUB_H = 10.0
SHAFT_D = 8.0

DISC_RADIAL_CLEAR = 0.8
WALL_T = 4.0
BOWL_ID = DISC_D + 2.0 * DISC_RADIAL_CLEAR
BOWL_OD = BOWL_ID + 2.0 * WALL_T
BOWL_IR = 0.5 * BOWL_ID
BOWL_OR = 0.5 * BOWL_OD
BOWL_H = 40.0
BOWL_Z0 = 0.0

# Đĩa: mặt trên Z=0. Mọi vật nằm trên đĩa (tiếp xúc). Guide/rail đáy HỞ tại GAP0.
DISC_TOP_Z = 0.0
GAP0 = 0.5  # khe đáy mở của guide/rail phía trên đĩa (không đỡ viên)

# Lane → exit trên mặt FreeCAD Front (camera nhìn theo +Y).
# θ_exit = 180° (−X, bên TRÁI màn Front): tiếp tuyến CCW = (0,−1) = đổ RA ngoài về phía người nhìn.
# Lane CCW: miệng vào θ=90° (+Y) → cửa ra θ=180°.
THETA_MOUTH_DEG = 90.0
THETA_EXIT_DEG = 180.0
CHUTE_ARC_DEG = THETA_EXIT_DEG - THETA_MOUTH_DEG

W_MAX = 26.0  # khe chỉnh max = bề rộng máng Exit_Track
H_MAX = 26.0  # chỉnh H: 2–26 mm
W_MIN = 2.0  # dải chỉnh W: 2–26 mm
H_MIN = 2.0
# Outer of free lane = inner face of bowl rim (video: white ring)
CHANNEL_R_OUTER = BOWL_IR
RAIL_T = 3.0
RAIL_H = H_MAX + 10.0  # tường đủ cao hơn H_MAX

# Crossbar + ray trượt chỉnh W/H — sát miệng lane (θ_mouth), không giữa cung
TH_ADJ_DEG = THETA_MOUTH_DEG
# BAR_Z=36.0 (= H_MAX+10, đúng bằng ngưỡng tối thiểu của check hand_top) khiến cần nối
# (hang, trong make_width_clamp) gần như KHÔNG còn chỗ: hang_z1=BAR_Z-2=34 <
# hang_z0=GAP0+RAIL_H-2=34.5 → an toàn bằng cách kẹp về mẩu 2mm lửng lơ, không thực sự
# chạm xuống đỉnh Inner_Lane_Rail. Nâng lên 42.0 để cần nối có khoang ~5.5mm, chạm liền
# xuống ray — vẫn giữ hand_top=True (42>=36) và moi z-offset khac deu tinh tuong doi
# theo BAR_Z nen khong lech hinh hoc noi khac.
BAR_Z = 42.0
BAR_W = 20.0
BAR_T = 8.0
BAR_SLOT_W = 11.0  # cổ ray H + thành U scraper (trượt H 2–26, không kẹt thanh)
# Ray trượt W: ray chữ T trên crossbar (nhìn rõ hướng xuyên tâm)
SLIDE_W_NECK = 5.0
SLIDE_W_TOP = 11.0
SLIDE_W_H = 5.5
SLIDE_W_FIT = 0.25
# M3 printed-part fastener — holes only (never model bolt/nut solids)
M3_CLEAR = 3.6  # ISO 273 medium + FDM margin
M3_HEAD_CB_D = 6.5
M3_HEAD_CB_H = 2.2
M3_NUT_POCKET_AF = 6.0
M3_NUT_POCKET_H = 2.8
M3_BOLT_L = 16.0  # grip ≤ ~12 mm + nut 2.4
HUB_M3_PCD = 18.0
HUB_CLAMP_T = 6.0
SCREW_D = M3_CLEAR  # clamp / assembly holes = M3 clearance
CLAMP_L = 34.0
CLAMP_JAW_T = 5.0
CLAMP_FIT = 0.18
CLAMP_H = 14.0
CLAMP_W = BAR_W + 2.0 * (CLAMP_JAW_T + CLAMP_FIT)
LOCK_SPAN = 16.0
POST_H = BAR_Z + 6.0
SCRAPER_T = 2.4  # FDM 6 perimeters @ 0.4 mm (was 2.0)
# Lưỡi ngang sát mặt miệng lane (vào trong máng một đoạn ngắn)
SCRAPER_BLADE_ALONG = 6.0
# Thành L chỉ nối lưỡi tại miệng — KHÔNG quét đĩa
SCRAPER_ENTRY_LEN = 5.0
SCRAPER_ENTRY_H = 8.0
SCRAPER_ENTRY_T = 2.4  # FDM 6 perimeters @ 0.4 mm (was 2.0)
SCRAPER_ENTRY_MAX_INBOARD = 6.0
# Ray trượt H: cột đứng chữ T trên carriage W
STEM_W = 8.0
STEM_T = 4.0
STEM_FIT = 0.25
H_RAIL_TOP = 12.0   # mặt T của ray H
H_RAIL_NECK = 5.0
H_SLIDER_H = 16.0   # khối trượt H ôm ray
HAND_TOP_CLEAR = 8.0
# Bu-lông kẹp (thay lò xo tì trước đây) — núm vặn LỚN (siết tay, không cần dụng cụ),
# xuyên theo phương NGANG (trục Y cục bộ — vuông góc hướng trượt), siết trực tiếp
# thanh tịnh tiến (má kẹp W trên ray T; vòng ôm ray H) — vị trí bu-lông cố định theo
# thân carriage/slider (luôn nằm đúng trên ray dù trượt tới đâu trong dải W_MIN..W_MAX
# / H_MIN..H_MAX vì ray là thanh liền suốt hành trình). Đặt ở độ cao thấp, trong lòng
# đĩa (ngang mức má kẹp/vòng ray), không nhô cao khỏi mép bát như thiết kế cũ.
KNOB_D = 11.0
KNOB_L = 5.0

W_TRAVEL = W_MAX - W_MIN
H_TRAVEL = H_MAX - H_MIN
S_AT_WMAX = CHANNEL_R_OUTER - W_MAX
S_AT_WMIN = CHANNEL_R_OUTER - W_MIN

# Guide_System cố định — xoắn hub→vành; HỌNG LANE mở theo CCW (lực tiếp tuyến)
# Tip Guide DỪNG trước θ_mouth → khe góc + khe bán kính với Bowl = lối vào nhìn thấy
ENTRANCE_W = 26.0  # họng Guide↔Bowl = W_MAX — nhận vật 2–26 mm
# Dung sai "bắt được tường" trong simulate_pill_mechanics (viên phải nằm cách
# tường không quá clear+TOL để coi là chạm). 0.35mm cũ để lại một dải chết hẹp
# ~1.2mm sát trục cho viên rất nhỏ (D=2mm): r0 ∈ [hub-touch, GUIDE_R0-clear)
# không bao giờ được xoắn Guide "vợt" vào — viên quay mãi không thoát (đã phát
# hiện bằng quét toàn dải bán kính, xem verify_recirculation_full_sweep).
# 2.0mm đủ đóng dải chết ở mọi D 2–25mm (đã verify), vẫn nhỏ so R0=20mm nên
# không đổi hành vi bắt/không-bắt ở các vị trí xa tường khác.
WALL_CAPTURE_TOL_MM = 2.0
GUIDE_R0 = 0.5 * HUB_D + 6.0
GUIDE_R1 = CHANNEL_R_OUTER - ENTRANCE_W
GUIDE_TH0 = THETA_MOUTH_DEG - 200.0
GUIDE_TH1 = THETA_MOUTH_DEG - 18.0  # trước miệng — không bịt lối vào
GUIDE_T = 4.5
GUIDE_FLANGE_W = 10.0
GUIDE_FLANGE_T = 3.5
GUIDE_H = H_MAX + 8.0
DIR_CLAMP_S = 0.0
DIR_CLAMP_L = 36.0
DIR_CLAMP_W = 22.0
DIR_CLAMP_H = 14.0
DIR_SCREW_SPAN = 16.0
DIR_STEM = 12.0
DIR_HUB_D = 38.0
_GUIDE_SPAN_R = GUIDE_R1 - GUIDE_R0
_GUIDE_SPAN_TH = GUIDE_TH1 - GUIDE_TH0
_GUIDE_U_MID = 0.38
DIR_R0 = GUIDE_R0
DIR_R1 = GUIDE_R0 + _GUIDE_U_MID * _GUIDE_SPAN_R
DIR_TH0 = GUIDE_TH0
DIR_TH1 = GUIDE_TH0 + _GUIDE_U_MID * _GUIDE_SPAN_TH
DIR_T = GUIDE_T
DIR_FLANGE_W = GUIDE_FLANGE_W
DIR_FLANGE_T = GUIDE_FLANGE_T
DIR_H = GUIDE_H
FUNNEL_R0 = DIR_R1
FUNNEL_R1 = GUIDE_R1
FUNNEL_TH0 = DIR_TH1
FUNNEL_TH1 = GUIDE_TH1
FUNNEL_T = GUIDE_T
FUNNEL_FLANGE_W = GUIDE_FLANGE_W
FUNNEL_FLANGE_T = GUIDE_FLANGE_T
FUNNEL_H = GUIDE_H
FUNNEL_N_FEET = 0
GUIDE_N_FEET = 0
GUIDE_HANDOFF_R = GUIDE_R1 - RAIL_T - 2.0
REJECT_LEN = 8.0  # chỉ bịt khe tip Guide↔rail — không quét đĩa
REJECT_T = RAIL_T
REJECT_ANGLE_DEG = 55.0
REJECT_R_CLEAR = 1.5
# Cửa vào (góc): từ tip Guide → θ_mouth — trống để thấy họng
ENTRANCE_TH0 = GUIDE_TH1
ENTRANCE_TH1 = THETA_MOUTH_DEG + 10.0

# Cuối Inner_Lane_Rail: bóc theo máng. Không hàng rào phía tâm (chặn vật quay vòng vào lane).
EXIT_GUARD_INBOARD = 0.0
EXIT_GUARD_ALONG = 22.0
EXIT_GUARD_T = RAIL_T
EXIT_GUARD_H = RAIL_H
EXIT_PEEL_PAST_RIM = 28.0  # tường trong máng nhô quá mép đĩa

EXIT_TRACK_LEN = BOWL_OR + 55.0  # nhô quá mép đĩa (hướng gần xuyên tâm)
EXIT_TRACK_WALL = 3.0  # FDM chute wall (was 2.5)
# Ma sát thành máng (Coulomb): tường CCW tự hãm nếu tan(β) ≤ μ_wall.
# F_đĩa = F ê_θ; N_tường = F cos β; F_dọc máng = F (sin β − μ cos β).
# Đẩy ra được ⇔ tan β > μ  ⇔  β > arctan(μ).
# PETG in / viên khô: μ_s ≈ 0.30–0.40; lấy 0.35 + biên 5° (tĩnh + nhám lớp in).
MU_WALL = 0.35
MU_DISC = 0.40
EXIT_FRICTION_MARGIN_DEG = 5.0


def exit_wall_friction_beta(
    mu_wall: float = MU_WALL,
    margin_deg: float = EXIT_FRICTION_MARGIN_DEG,
) -> dict:
    """β tối thiểu để đĩa đẩy viên dọc máng khi thành máng có ma sát."""
    beta_lock_deg = math.degrees(math.atan(mu_wall))
    beta_deg = beta_lock_deg + float(margin_deg)
    br = math.radians(beta_deg)
    sin_b, cos_b = math.sin(br), math.cos(br)
    drive_raw = sin_b
    drive_net = sin_b - mu_wall * cos_b
    return {
        "mu_wall": float(mu_wall),
        "mu_disc": MU_DISC,
        "beta_lock_deg": beta_lock_deg,
        "margin_deg": float(margin_deg),
        "beta_deg": beta_deg,
        "drive_raw": drive_raw,
        "drive_net": drive_net,
        "unlock": drive_net > 1e-9 and beta_deg > beta_lock_deg + 1e-9,
        "eq": "F_along = F*(sin(beta)-mu*cos(beta)); tan(beta)>mu",
    }


_EXIT_FRIC = exit_wall_friction_beta()
EXIT_FROM_RADIAL_DEG = _EXIT_FRIC["beta_deg"]
# Máng ra = khẩu độ chỉnh (W×H); khi set pill: W=D+1, H=T+1
# EXIT_TRACK_W giữ alias legacy (= W_MAX) — kích thước thật theo width_open
EXIT_TRACK_W = W_MAX
# Mép vào máng sát mặt phẳng θ_exit của lane (không lệch ra BOWL_OR)
EXIT_X0_ALONG = 0.0
# Nối lane → máng ra: Hermite G1 (không góc gãy a2/b2)
JOIN_BLEND_S = 20.0
JOIN_HANDLE_FRAC = 0.40
JOIN_N = 28
JOIN_MAX_TURN_DEG = 45.0  # cũ a2/b2 ~90°; nối mới <45°/mẫu
JOIN_BLEND_TH0 = THETA_EXIT_DEG - 12.0
JOIN_SEAL_OVERLAP_MM = 8.0  # rail xuyên miệng chồng Exit_Track
JOIN_MAX_GAP_MM = 0.35  # không khe hở vách W ↔ máng ra

WIDTH_MIN, WIDTH_MAX = W_MIN, W_MAX
HEIGHT_MIN, HEIGHT_MAX = H_MIN, H_MAX

# Máng / khe: rộng hơn và cao hơn vật đúng 1 mm
PILL_CLEAR_XY = 1.0
PILL_CLEAR_Z = 1.0

PILL_DATASETS: list[dict] = [
    {"id": "tiny_5x2.5", "D": 5.0, "T": 2.5, "shape": "tablet"},
    {"id": "small_6x3", "D": 6.0, "T": 3.0, "shape": "tablet"},
    {"id": "medium_8x4", "D": 8.0, "T": 4.0, "shape": "tablet"},
    {"id": "large_10x5", "D": 10.0, "T": 5.0, "shape": "tablet"},
    {"id": "xl_12x6", "D": 12.0, "T": 6.0, "shape": "tablet"},
    {"id": "softgel_9", "D": 9.0, "T": 9.0, "shape": "ball"},
    {"id": "caplet_eq_7x4", "D": 7.0, "T": 4.0, "shape": "tablet"},
    {"id": "thick_8x7", "D": 8.0, "T": 7.0, "shape": "tablet"},
    {"id": "mini_4x2", "D": 4.0, "T": 2.0, "shape": "tablet"},
    {"id": "oblong_11x5", "D": 11.0, "T": 5.0, "shape": "tablet"},
    {"id": "softgel_7", "D": 7.0, "T": 7.0, "shape": "ball"},
    {"id": "flat_9x3", "D": 9.0, "T": 3.0, "shape": "tablet"},
]

COLORS = {
    "disc": (0.22, 0.22, 0.24),
    "bowl": (0.92, 0.92, 0.94),
    "bar": (0.72, 0.74, 0.78),
    "clamp": (0.18, 0.18, 0.22),
    "slide": (0.45, 0.48, 0.55),
    "rail": (0.85, 0.55, 0.20),
    "height": (0.30, 0.55, 0.90),
    "funnel": (0.30, 0.52, 0.62),
    "director": (0.30, 0.52, 0.62),
    "guide": (0.30, 0.52, 0.62),
    "reject": (0.90, 0.25, 0.25),
    "exit": (0.12, 0.12, 0.12),
    "mouth": (0.95, 0.25, 0.55),
    "screw": (0.35, 0.35, 0.38),
}


def _refine(shape: Part.Shape) -> Part.Shape:
    try:
        out = shape.removeSplitter()
        return shape if out is None or out.isNull() else out
    except Exception:
        return shape


def _shape_ok(shape: Part.Shape, min_vol: float = 2.0) -> bool:
    try:
        if shape is None or shape.isNull():
            return False
        return float(getattr(shape, "Volume", 0.0) or 0.0) >= min_vol
    except Exception:
        return False


def _box(dx, dy, dz, x0, y0, z0) -> Part.Shape:
    b = Part.makeBox(dx, dy, dz)
    b.translate(App.Vector(x0, y0, z0))
    return b


def _cyl_z(d, h, x=0.0, y=0.0, z0=0.0) -> Part.Shape:
    c = Part.makeCylinder(d / 2.0, h)
    c.translate(App.Vector(x, y, z0))
    return c


def _unit3(v: tuple[float, float, float]) -> tuple[float, float, float]:
    n = math.hypot(v[0], v[1], v[2]) or 1.0
    return (v[0] / n, v[1] / n, v[2] / n)


def _cyl_axis(d: float, h: float, origin, axis) -> Part.Shape:
    o = App.Vector(float(origin[0]), float(origin[1]), float(origin[2]))
    a = _unit3(axis)
    return Part.makeCylinder(d / 2.0, h, o, App.Vector(a[0], a[1], a[2]))


def hub_m3_xy() -> list[tuple[float, float]]:
    r = 0.5 * HUB_M3_PCD
    out = []
    for i in range(4):
        a = math.radians(45.0 + i * 90.0)
        out.append((r * math.cos(a), r * math.sin(a)))
    return out


def _m3_nut_pocket_z(x: float, y: float, z_bottom: float) -> Part.Shape:
    af = M3_NUT_POCKET_AF
    box = Part.makeBox(af, af, M3_NUT_POCKET_H + 0.2)
    box.translate(App.Vector(x - af / 2.0, y - af / 2.0, z_bottom - 0.1))
    return box


def _m3_cbore_z(x: float, y: float, z_top: float) -> Part.Shape:
    c = Part.makeCylinder(M3_HEAD_CB_D / 2.0, M3_HEAD_CB_H + 0.2)
    c.translate(App.Vector(x, y, z_top - M3_HEAD_CB_H - 0.2))
    return c


def _cut_m3_z(
    shape: Part.Shape,
    xy: list[tuple[float, float]],
    z0: float,
    h: float,
    *,
    cbore_top: float | None = None,
    nut_bottom: float | None = None,
) -> Part.Shape:
    out = shape
    for x, y in xy:
        try:
            nxt = out.cut(_cyl_z(M3_CLEAR, h, x, y, z0))
            if nxt is not None and getattr(nxt, "Solids", None):
                out = nxt
        except Exception:
            continue
        if cbore_top is not None:
            try:
                nxt = out.cut(_m3_cbore_z(x, y, cbore_top))
                if nxt is not None and getattr(nxt, "Solids", None):
                    out = nxt
            except Exception:
                pass
        if nut_bottom is not None:
            try:
                nxt = out.cut(_m3_nut_pocket_z(x, y, nut_bottom))
                if nxt is not None and getattr(nxt, "Solids", None):
                    out = nxt
            except Exception:
                pass
    return out


def guide_mount_sites() -> list[dict]:
    """Radial M3 through Guide feet into Bowl_Tube (above H_MAX)."""
    mount_z0 = GAP0 + H_MAX + 2.0
    mount_h = (GAP0 + GUIDE_H) - mount_z0
    z = mount_z0 + 0.5 * max(2.0, mount_h)
    out = []
    for u_ft in (0.30, 0.70):
        th_ft = GUIDE_TH0 + (GUIDE_TH1 - GUIDE_TH0) * u_ft
        r_wall = GUIDE_R0 + (GUIDE_R1 - GUIDE_R0) * u_ft
        c, s = math.cos(_deg2rad(th_ft)), math.sin(_deg2rad(th_ft))
        r0 = r_wall - 2.0
        out.append(
            {
                "origin": (r0 * c, r0 * s, z),
                "axis": (c, s, 0.0),
                "h": (BOWL_OR - r0) + 6.0,
                "th_deg": th_ft,
            }
        )
    return out


def _cut_m3_sites(shape: Part.Shape, sites: list[dict]) -> Part.Shape:
    out = shape
    for site in sites:
        try:
            nxt = out.cut(_cyl_axis(M3_CLEAR, float(site["h"]), site["origin"], site["axis"]))
            if nxt is not None and getattr(nxt, "Solids", None):
                out = nxt
        except Exception:
            continue
    return out


def hole_is_empty(shape: Part.Shape, x: float, y: float, z: float, tol: float = 0.5) -> bool:
    if shape is None or not getattr(shape, "Solids", None):
        return False
    try:
        return not bool(shape.isInside(App.Vector(x, y, z), tol, True))
    except Exception:
        return False


def _knob_bolt_along(origin, axis, shank_len: float) -> Part.Shape:
    """Bu-lông núm vặn lớn: núm (KNOB_D×KNOB_L) tại origin, thân ren (SCREW_D) dài
    shank_len tiếp theo cùng huống axis — dùng cho ca kep W va H (thay lo xo)."""
    ax = _unit3(axis)
    knob = _cyl_axis(KNOB_D, KNOB_L, origin, ax)
    shank_origin = (
        origin[0] + KNOB_L * ax[0],
        origin[1] + KNOB_L * ax[1],
        origin[2] + KNOB_L * ax[2],
    )
    shank = _cyl_axis(SCREW_D, shank_len, shank_origin, ax)
    return _refine(knob.fuse(shank))


def _width_bolt_sites(s: float) -> list[dict]:
    """2 bu-lông kẹp má W — phương NGANG (trục Y), xuyên qua má kẹp + khe ray T,
    núm ở mép ngoài má trái (y nhỏ nhất — phía trong lòng đĩa, thấp ngang tâm má
    kẹp, không nhô cao như vít đứng cũ). Vị trí (s+ds) bám theo carriage nên LUÔN
    nằm đúng trên ray T (ray liền suốt hành trình W_MIN..W_MAX) dù trượt tới đâu."""
    y_l = -0.5 * BAR_W - CLAMP_FIT - CLAMP_JAW_T
    z_bolt = (BAR_Z - 1.0) + 0.5 * (BAR_T + SLIDE_W_H + 2.0)
    span = CLAMP_W + 2.0
    out = []
    for i, ds in enumerate((-0.5 * LOCK_SPAN, 0.5 * LOCK_SPAN)):
        out.append({
            "name": f"Screw_Width_{i + 1}",
            "knob_origin": (s + ds, y_l - KNOB_L - 1.0, z_bolt),
            "hole_origin": (s + ds, y_l - 1.0, z_bolt),
            "axis": (0.0, 1.0, 0.0),
            "shank_len": span,
        })
    return out


def _height_bolt_site(s: float) -> dict:
    """1 bu-lông kẹp vòng ôm ray H — phương NGANG (trục Y), xuyên qua vòng ôm
    (collar "above" trong make_height_scraper), siết ép vào mặt bích H_RAIL_TOP.
    Vị trí bám theo stem_x0 (=s+2.8) nên luôn đúng ray dù H thay đổi (ray T doc
    theo carriage, lien suot H_MIN..H_MAX)."""
    stem_x0 = s + 2.8
    uy_slot = 0.5 * (BAR_SLOT_W - 1.6)
    z_rail = BAR_Z + BAR_T
    x_bolt = stem_x0 - 0.6 + 0.5 * (H_RAIL_TOP + 5.0)
    z_bolt = z_rail + 0.35 + 4.0
    span = 2.0 * uy_slot + 4.0
    return {
        "name": "Screw_Height",
        "knob_origin": (x_bolt, -uy_slot - 1.0 - KNOB_L, z_bolt),
        "hole_origin": (x_bolt, -uy_slot - 1.0, z_bolt),
        "axis": (0.0, 1.0, 0.0),
        "shank_len": span,
    }


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(v)))


def _deg2rad(d: float) -> float:
    return d * math.pi / 180.0


def _annular_sector(
    r_in: float,
    r_out: float,
    th0_deg: float,
    th1_deg: float,
    z0: float,
    h: float,
    n: int = 36,
) -> Part.Shape:
    if r_out <= r_in + 1e-6 or h <= 1e-6:
        return _box(0.1, 0.1, 0.1, 0, 0, z0)
    th0, th1 = _deg2rad(th0_deg), _deg2rad(th1_deg)
    if th1 < th0:
        th0, th1 = th1, th0
    n = max(8, int(n))
    pts_out, pts_in = [], []
    for i in range(n + 1):
        t = th0 + (th1 - th0) * (i / n)
        pts_out.append(App.Vector(r_out * math.cos(t), r_out * math.sin(t), z0))
        pts_in.append(App.Vector(r_in * math.cos(t), r_in * math.sin(t), z0))
    wire = pts_out + list(reversed(pts_in))
    wire.append(wire[0])
    face = Part.Face(Part.makePolygon(wire))
    return _refine(face.extrude(App.Vector(0, 0, h)))


def _place_oriented_box(
    length, thick, height, cx, cy, z0, heading_deg
) -> Part.Shape:
    b = _box(length, thick, height, -0.5 * length, -0.5 * thick, z0)
    b.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), heading_deg)
    b.translate(App.Vector(cx, cy, 0))
    return _refine(b)


def exit_tangent_pose(width_open: float, height_open: float) -> dict:
    """
    Cửa ra: neo tại tâm lane; hướng GẦN XUYÊN TÂM + lệch CCW β.
    β = arctan(μ_wall) + biên — đủ lớn để F_dọc = F(sinβ − μ cosβ) > 0
    (thành máng ma sát không tự hãm; đĩa chậm vẫn đẩy). Đáy hở tới r > DISC_R.
    """
    ap = aperture_from_opens(width_open, height_open)
    th_deg = THETA_EXIT_DEG
    th = _deg2rad(th_deg)
    r_lane = 0.5 * (ap["r_inner"] + ap["r_outer"])
    r_anchor = r_lane
    tx, ty = -math.sin(th), math.cos(th)
    nx, ny = math.cos(th), math.sin(th)
    fric = exit_wall_friction_beta()
    beta = fric["beta_deg"]
    heading = th_deg + beta  # 0=radial out, 90=tangent CCW
    hx, hy = math.cos(_deg2rad(heading)), math.sin(_deg2rad(heading))
    x0_along = EXIT_X0_ALONG
    return {
        "theta_deg": th_deg,
        "heading_tangent_deg": heading,
        "heading_chute_deg": heading,
        "from_radial_deg": beta,
        "r_center_mm": r_anchor,
        "r_lane_mm": r_lane,
        "r_anchor_mm": r_anchor,
        "x0_along_mm": x0_along,
        "anchor_xy": (r_anchor * math.cos(th), r_anchor * math.sin(th)),
        "lane_center_xy": (r_lane * math.cos(th), r_lane * math.sin(th)),
        "tangent": (tx, ty),
        "radial_out": (nx, ny),
        "chute_dir": (hx, hy),
        "drive_along_chute": fric["drive_raw"],
        "drive_net_friction": fric["drive_net"],
        "mu_wall": fric["mu_wall"],
        "mu_disc": fric["mu_disc"],
        "beta_lock_deg": fric["beta_lock_deg"],
        "friction_unlock": fric["unlock"],
        "exit_track_w_mm": ap["width_mm"],
        "W": ap["width_mm"],
        "H": ap["height_mm"],
        "matched_to_lane": abs(r_anchor - r_lane) < 1e-9,
        "flush_to_lane": abs(x0_along) < 1e-9,
        "open_bottom_on_disc": True,
    }


def _place_tangent_exit(shape: Part.Shape, width_open: float, height_open: float) -> Part.Shape:
    pose = exit_tangent_pose(width_open, height_open)
    ax, ay = pose["anchor_xy"]
    shape.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), pose["heading_tangent_deg"])
    shape.translate(App.Vector(ax, ay, 0))
    return _refine(shape)


def aperture_from_opens(width_open: float, height_open: float) -> dict:
    w = _clamp(width_open, WIDTH_MIN, WIDTH_MAX)
    h = _clamp(height_open, HEIGHT_MIN, HEIGHT_MAX)
    r_outer = CHANNEL_R_OUTER
    r_inner = r_outer - w
    return {
        "width_mm": w,
        "height_mm": h,
        "r_inner": r_inner,
        "r_outer": r_outer,
        "z0": GAP0,
        "z1": GAP0 + h,
        "theta_mouth_deg": THETA_MOUTH_DEG,
        "theta_exit_deg": THETA_EXIT_DEG,
        "arc_deg": CHUTE_ARC_DEG,
    }


def width_clamp_s(width_open: float) -> float:
    """Slide along crossbar (+radial @ TH_ADJ). s = r_inner = R_outer - W."""
    w = _clamp(width_open, WIDTH_MIN, WIDTH_MAX)
    return CHANNEL_R_OUTER - w


def height_scraper_z(height_open: float) -> float:
    """Bottom face Z of height scraper."""
    return GAP0 + _clamp(height_open, HEIGHT_MIN, HEIGHT_MAX)


def width_clamp_r(width_open: float) -> float:
    return width_clamp_s(width_open)


def adjust_pose_math(width_open: float, height_open: float) -> dict:
    """Closed-form pose — source of truth for CAD + verify."""
    ap = aperture_from_opens(width_open, height_open)
    s = width_clamp_s(width_open)
    z1 = height_scraper_z(height_open)
    return {
        "W": ap["width_mm"],
        "H": ap["height_mm"],
        "s_mm": round(s, 6),
        "r_inner_mm": ap["r_inner"],
        "r_outer_mm": ap["r_outer"],
        "z_scraper_mm": round(z1, 6),
        "theta_adj_deg": TH_ADJ_DEG,
        "eq_W": "W = CHANNEL_R_OUTER - s",
        "eq_H": "H = z_scraper - GAP0",
        "eq_s": "s = CHANNEL_R_OUTER - W",
        "check_W_from_s": abs((CHANNEL_R_OUTER - s) - ap["width_mm"]) < 1e-9,
        "check_H_from_z": abs((z1 - GAP0) - ap["height_mm"]) < 1e-9,
        "check_s_eq_rin": abs(s - ap["r_inner"]) < 1e-9,
    }


def mouth_geometry() -> dict:
    th_m = _deg2rad(THETA_MOUTH_DEG)
    r_m = CHANNEL_R_OUTER - 0.5 * W_MAX
    tx_m, ty_m = -math.sin(th_m), math.cos(th_m)
    nx_m, ny_m = math.cos(th_m), math.sin(th_m)
    ex = exit_tangent_pose(W_MAX, H_MAX)
    tx, ty = ex["tangent"]
    nx, ny = ex["radial_out"]
    # exit local +X after rotate(heading) = chute axis (near radial)
    h = _deg2rad(ex["heading_tangent_deg"])
    exit_dir = (math.cos(h), math.sin(h))
    dot_t = exit_dir[0] * tx + exit_dir[1] * ty
    dot_r = exit_dir[0] * nx + exit_dir[1] * ny
    ang_vs_radial_deg = abs(math.degrees(math.atan2(dot_t, dot_r)))
    return {
        "mouth_xy_mm": (round(r_m * math.cos(th_m), 3), round(r_m * math.sin(th_m), 3)),
        "tangent_flow": (round(tx_m, 5), round(ty_m, 5)),
        "radial_out": (round(nx_m, 5), round(ny_m, 5)),
        "mouth_open_vs_flow_deg": 0.0,
        "bad_perpendicular_mouth_deg": 90.0,
        "mouth_is_along_flow": True,
        "entrance_throat": {
            "width_mm": ENTRANCE_W,
            "r_inner_guide_mm": GUIDE_R1,
            "r_outer_bowl_mm": CHANNEL_R_OUTER,
            "theta_open_deg": [ENTRANCE_TH0, ENTRANCE_TH1],
            "opens_into_ccw_flow": True,
            "guide_fixed": True,
            "guide_stops_before_mouth": GUIDE_TH1 < THETA_MOUTH_DEG - 5.0,
            "force_model": "tangential_only_on_disc",
            "visible_gap_mm": round(CHANNEL_R_OUTER - GUIDE_R1, 2),
        },
        "exit_tangent": {
            "theta_exit_deg": THETA_EXIT_DEG,
            "heading_deg": ex["heading_tangent_deg"],
            "from_radial_deg": round(EXIT_FROM_RADIAL_DEG, 3),
            "mu_wall": ex["mu_wall"],
            "mu_disc": ex["mu_disc"],
            "beta_lock_deg": round(ex["beta_lock_deg"], 3),
            "drive_raw": round(ex["drive_along_chute"], 6),
            "drive_net_friction": round(ex["drive_net_friction"], 6),
            "wall_friction_unlock": bool(ex["friction_unlock"]),
            "anchor_xy": (round(ex["anchor_xy"][0], 3), round(ex["anchor_xy"][1], 3)),
            "exit_dir": (round(exit_dir[0], 5), round(exit_dir[1], 5)),
            "tangent": (round(tx, 5), round(ty, 5)),
            "dot_exit_tangent": round(dot_t, 6),
            "dot_exit_radial": round(dot_r, 6),
            "angle_vs_radial_deg": round(ang_vs_radial_deg, 3),
            "nearly_radial": (
                dot_r > 0.88
                and ang_vs_radial_deg <= EXIT_FROM_RADIAL_DEG + 0.5
            ),
            "aligned_with_tangent": False,
            "slow_omega_drive": bool(ex["friction_unlock"]) and float(ex["drive_net_friction"]) > 0.05,
            "flows_toward_front_left": exit_dir[0] < -0.82,
            "mouth_on_front_left": ex["anchor_xy"][0] < -0.5 * BOWL_OR and abs(ex["anchor_xy"][1]) < 0.35 * BOWL_OR,
            "open_bottom_until_off_disc": True,
            "view_note": (
                f"θ_exit=180°; máng lệch CCW {EXIT_FROM_RADIAL_DEG:.1f}° "
                f"(β>arctan(μ={MU_WALL:g})={ex['beta_lock_deg']:.1f}°) để thắng ma sát thành"
            ),
        },
        "rotation": "CCW",
        "ref": "SchanerDesigns shorts ju5vIg66NNk",
    }


def _to_adj_frame(shape: Part.Shape) -> Part.Shape:
    shape.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), TH_ADJ_DEG)
    return _refine(shape)


BOWL_SLOT_BEFORE_EXIT_DEG = 3.0
BOWL_SLOT_AFTER_EXIT_DEG = 50.0


BOWL_SLOT_TH0_DEG = THETA_EXIT_DEG - BOWL_SLOT_BEFORE_EXIT_DEG
BOWL_SLOT_TH1_DEG = THETA_EXIT_DEG + BOWL_SLOT_AFTER_EXIT_DEG


def make_crossbar_bridge() -> Part.Shape:
    """Thanh bắc + ray trượt W chữ T (cố định) — carriage trượt xuyên tâm."""
    half = BOWL_OR + 28.0
    bar = _box(2.0 * half, BAR_W, BAR_T, -half, -0.5 * BAR_W, BAR_Z)
    # Slot dưới cho lưỡi khóa + cổ ray H (đủ dài cho tongue tại W_MIN/W_MAX)
    tongue_half = 0.5 * (CLAMP_L - 10.0)
    slot_x0 = S_AT_WMAX - tongue_half - 3.0
    slot_len = (S_AT_WMIN + tongue_half + 3.0) - slot_x0
    bar = bar.cut(_box(slot_len, BAR_SLOT_W, BAR_T + 2.0, slot_x0, -0.5 * BAR_SLOT_W, BAR_Z - 1.0))
    # Ray chữ T trên mặt thanh (đoạn chỉnh W)
    rail_x0 = S_AT_WMAX - 6.0
    rail_len = (S_AT_WMIN + 6.0) - rail_x0
    neck = _box(rail_len, SLIDE_W_NECK, SLIDE_W_H, rail_x0, -0.5 * SLIDE_W_NECK, BAR_Z + BAR_T)
    rail_flange_t = 2.4  # FDM 6 perimeters
    top = _box(
        rail_len, SLIDE_W_TOP, rail_flange_t,
        rail_x0, -0.5 * SLIDE_W_TOP, BAR_Z + BAR_T + SLIDE_W_H - rail_flange_t,
    )
    # End-stops: chạm mặt carriage tại W_MIN / W_MAX — không xuyên sâu
    stop_t = 4.0
    stop_a = _box(
        stop_t, SLIDE_W_TOP + 4.0, SLIDE_W_H + 3.0,
        S_AT_WMAX - 0.5 * CLAMP_L - stop_t,
        -0.5 * (SLIDE_W_TOP + 4.0), BAR_Z + BAR_T,
    )
    stop_b = _box(
        stop_t, SLIDE_W_TOP + 4.0, SLIDE_W_H + 3.0,
        S_AT_WMIN + 0.5 * CLAMP_L,
        -0.5 * (SLIDE_W_TOP + 4.0), BAR_Z + BAR_T,
    )
    post_p = _box(14.0, 14.0, POST_H, half - 16.0, -7.0, 0.0)
    post_m = _box(14.0, 14.0, POST_H, -half + 2.0, -7.0, 0.0)
    body = bar.fuse(neck).fuse(top).fuse(stop_a).fuse(stop_b).fuse(post_p).fuse(post_m)
    # M3×16 into post bases (heat-set / through to a bed plate) — not full 48 mm
    post_xy = [(half - 9.0, 0.0), (-half + 9.0, 0.0)]
    body = _cut_m3_z(body, post_xy, -1.0, 8.0, cbore_top=6.0)
    return _to_adj_frame(body)


def make_scale_width() -> Part.Shape:
    """Vạch W nằm ngoài carriage (không nằm trên ray T / xuyên khối trượt)."""
    y0 = 0.5 * CLAMP_W + 1.2
    marks = []
    for dw in range(0, int(W_TRAVEL) + 1, 2):
        s = S_AT_WMAX + dw
        marks.append(_box(0.6, 5.0, 1.3, s - 0.3, y0, BAR_Z + BAR_T))
    body = marks[0]
    for m in marks[1:]:
        body = body.fuse(m)
    return _to_adj_frame(body)


def _dedupe_xy(pts_xy: list[tuple[float, float]], eps: float = 0.12) -> list[tuple[float, float]]:
    if not pts_xy:
        return []
    out = [pts_xy[0]]
    for p in pts_xy[1:]:
        if math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) >= eps:
            out.append(p)
    return out


def _path_len_mm(pts_xy: list[tuple[float, float]]) -> float:
    return sum(
        math.hypot(pts_xy[i][0] - pts_xy[i - 1][0], pts_xy[i][1] - pts_xy[i - 1][1])
        for i in range(1, len(pts_xy))
    )


def _take_path_len(
    pts_xy: list[tuple[float, float]], length: float
) -> list[tuple[float, float]]:
    if not pts_xy or length <= 1e-9:
        return list(pts_xy[:1])
    out = [pts_xy[0]]
    acc = 0.0
    for p in pts_xy[1:]:
        dx, dy = p[0] - out[-1][0], p[1] - out[-1][1]
        d = math.hypot(dx, dy)
        if d < 1e-9:
            continue
        if acc + d >= length:
            u = (length - acc) / d
            out.append((out[-1][0] + u * dx, out[-1][1] + u * dy))
            return out
        out.append(p)
        acc += d
    return out


def _downsample_xy(pts_xy: list[tuple[float, float]], n_max: int = 12) -> list[tuple[float, float]]:
    if len(pts_xy) <= n_max:
        return list(pts_xy)
    out = [pts_xy[0]]
    step = (len(pts_xy) - 1) / float(n_max - 1)
    for i in range(1, n_max - 1):
        out.append(pts_xy[int(round(i * step))])
    out.append(pts_xy[-1])
    return _dedupe_xy(out)


def _wall_from_segments(
    pts_xy: list[tuple[float, float]],
    thick: float,
    z0: float,
    h: float,
) -> Part.Shape:
    """Tường vững boolean: ít hộp theo polyline rút gọn — không Face tự cắt."""
    pts = _downsample_xy(_dedupe_xy(pts_xy), 10)
    if len(pts) < 2 or thick <= 1e-6 or h <= 1e-6:
        return _box(0.1, 0.1, 0.1, 0, 0, z0)
    body = None
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        ln = math.hypot(x1 - x0, y1 - y0)
        if ln < 0.08:
            continue
        heading = math.degrees(math.atan2(y1 - y0, x1 - x0))
        seg = _box(ln + 0.55, thick, h, -0.28, -0.5 * thick, z0)
        seg.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), heading)
        seg.translate(App.Vector(x0, y0, 0))
        body = seg if body is None else body.fuse(seg)
    for x, y in (pts[0], pts[-1]):
        cap = _cyl_z(thick, h, x, y, z0)
        body = cap if body is None else body.fuse(cap)
    return _refine(body) if body is not None else _box(0.1, 0.1, 0.1, 0, 0, z0)


def _thickened_path_wall(
    pts_xy: list[tuple[float, float]],
    thick: float,
    z0: float,
    h: float,
) -> Part.Shape:
    """Tường đứng theo polyline tâm. Face mượt nếu vững; không thì ghép đoạn."""
    pts = _dedupe_xy(pts_xy)
    if len(pts) < 2 or thick <= 1e-6 or h <= 1e-6:
        return _box(0.1, 0.1, 0.1, 0, 0, z0)
    want = _path_len_mm(pts) * thick * h * 0.45
    half = 0.5 * thick
    left, right = [], []
    n = len(pts)
    for i in range(n):
        if i == 0:
            dx, dy = pts[1][0] - pts[0][0], pts[1][1] - pts[0][1]
        elif i == n - 1:
            dx, dy = pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]
        else:
            dx = pts[i + 1][0] - pts[i - 1][0]
            dy = pts[i + 1][1] - pts[i - 1][1]
        ln = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / ln, dx / ln
        x, y = pts[i]
        left.append(App.Vector(x + half * nx, y + half * ny, z0))
        right.append(App.Vector(x - half * nx, y - half * ny, z0))
    wire = left + list(reversed(right))
    wire.append(wire[0])
    try:
        face = Part.Face(Part.makePolygon(wire))
        wall = _refine(face.extrude(App.Vector(0, 0, h)))
        vol = float(getattr(wall, "Volume", 0.0) or 0.0)
        if vol >= max(1.0, want) and _shape_ok(wall, max(1.0, want)):
            return wall
    except Exception:
        pass
    return _wall_from_segments(pts, thick, z0, h)


def _join_seal_key(width_open: float, thick: float, h: float) -> Part.Shape:
    """Khối khóa miệng: hộp trên dây tâm, lệch vào trong tường (không lấn lòng lane)."""
    geo = lane_exit_join_geo(width_open)
    pts = _take_path_len(geo["exit_inner_pts"], JOIN_SEAL_OVERLAP_MM + 12.0)
    if len(pts) < 2:
        p = geo["exit_inner_pts"][0]
        return _cyl_z(thick, h, p[0], p[1], GAP0)
    x0, y0 = pts[0]
    x1, y1 = pts[-1]
    ln = math.hypot(x1 - x0, y1 - y0) or 1.0
    heading = math.degrees(math.atan2(y1 - y0, x1 - x0))
    tw = max(2.2, thick - 0.15)
    # lệch về tâm (phía đặc tường) — hộp dây cung không cắt lòng lane.
    # 0.45 mm cũ không đủ ở W lớn (viên tại θ_exit vẫn chạm cap0/bar — xem
    # verify_single_file_multi / verify_single_file_size_sweep jam_pill_vs_L);
    # 4 mm còn kẹt sát ngay tại θ_exit khi W→26 (D→25 mm, biên <0.5 mm theo mô
    # hình capsule đơn giản — CAD 3D thật vẫn chạm). 7 mm cho biên ~2 mm dư mọi W.
    SEAL_KEY_INBOARD_MM = 7.0
    ux_in, uy_in = _unit2(-x0, -y0)
    ox, oy = x0 + SEAL_KEY_INBOARD_MM * ux_in, y0 + SEAL_KEY_INBOARD_MM * uy_in
    bar = _box(ln + 2.4, tw, h, -1.2, -0.5 * tw, GAP0)
    bar.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), heading)
    bar.translate(App.Vector(ox, oy, 0))
    cap0 = _cyl_z(tw, h, ox, oy, GAP0)
    cap1 = _cyl_z(tw, h, x1 + SEAL_KEY_INBOARD_MM * ux_in, y1 + SEAL_KEY_INBOARD_MM * uy_in, GAP0)
    return _refine(bar.fuse(cap0).fuse(cap1))


def _funnel_params(width_open: float) -> dict | None:
    """Phễu tiếp xúc: tip Guide → tường trong lane (đẩy +r khi W < ENTRANCE_W)."""
    r_i = CHANNEL_R_OUTER - _clamp(width_open, WIDTH_MIN, WIDTH_MAX)
    r_cline = r_i - 0.5 * RAIL_T
    r0 = GUIDE_R1 + 1.2
    th0 = GUIDE_TH1 + 2.5
    # Dừng trước thành đứng scraper (θ_mouth−7°) — không cắt Height_Scraper
    th1 = THETA_MOUTH_DEG - 8.5
    if r_cline <= r0 + 0.8 or th1 <= th0 + 0.5:
        return None
    return {"r0": r0, "r1": r_cline, "th0": th0, "th1": th1}


def _inner_wall_r(th_deg: float, width_open: float) -> float | None:
    """Tâm tường đẩy +r tại θ: xoắn Guide, phễu họng, rồi rail lane. None = không tường."""
    rg = _spiral_r_at_theta(GUIDE_R0, GUIDE_R1, GUIDE_TH0, GUIDE_TH1, th_deg)
    if rg is not None:
        return rg
    fun = _funnel_params(width_open)
    if fun is not None and _ang_between(th_deg, fun["th0"], fun["th1"]):
        span = fun["th1"] - fun["th0"]
        th = th_deg
        if th < fun["th0"] - 1.0:
            th += 360.0
        u = _clamp((th - fun["th0"]) / span, 0.0, 1.0)
        return fun["r0"] + u * (fun["r1"] - fun["r0"])
    r_i = CHANNEL_R_OUTER - _clamp(width_open, WIDTH_MIN, WIDTH_MAX)
    if _ang_between(th_deg, THETA_MOUTH_DEG - 0.5, THETA_EXIT_DEG):
        return r_i - 0.5 * RAIL_T
    return None


def _unit2(x: float, y: float) -> tuple[float, float]:
    n = math.hypot(x, y) or 1.0
    return (x / n, y / n)


def _ang_diff_deg(a: float, b: float) -> float:
    return (b - a + 180.0) % 360.0 - 180.0


def _path_heading_deg(p: tuple[float, float], q: tuple[float, float]) -> float:
    return math.degrees(math.atan2(q[1] - p[1], q[0] - p[0]))


def _path_max_turn_deg(pts: list[tuple[float, float]]) -> float:
    mx = 0.0
    for i in range(1, len(pts) - 1):
        a = _path_heading_deg(pts[i - 1], pts[i])
        b = _path_heading_deg(pts[i], pts[i + 1])
        mx = max(mx, abs(_ang_diff_deg(a, b)))
    return mx


def _hermite_poly(
    p0: tuple[float, float],
    t0: tuple[float, float],
    p3: tuple[float, float],
    t3: tuple[float, float],
    n: int,
    l0: float | None = None,
    l3: float | None = None,
) -> list[tuple[float, float]]:
    ux0, uy0 = _unit2(*t0)
    ux3, uy3 = _unit2(*t3)
    chord = math.hypot(p3[0] - p0[0], p3[1] - p0[1])
    h0 = float(l0 if l0 is not None else JOIN_HANDLE_FRAC * chord)
    h3 = float(l3 if l3 is not None else JOIN_HANDLE_FRAC * chord)
    p1 = (p0[0] + h0 * ux0, p0[1] + h0 * uy0)
    p2 = (p3[0] - h3 * ux3, p3[1] - h3 * uy3)
    pts: list[tuple[float, float]] = []
    for i in range(max(4, n) + 1):
        tt = i / max(4, n)
        u = 1.0 - tt
        b0, b1, b2, b3 = u ** 3, 3.0 * u * u * tt, 3.0 * u * tt * tt, tt ** 3
        pts.append(
            (
                b0 * p0[0] + b1 * p1[0] + b2 * p2[0] + b3 * p3[0],
                b0 * p0[1] + b1 * p1[1] + b2 * p2[1] + b3 * p3[1],
            )
        )
    return pts


def lane_exit_join_geo(width_open: float) -> dict:
    """Cung lane → Hermite G1 → máng ra (cùng tâm tường trong)."""
    ap = aperture_from_opens(width_open, H_MIN)
    r_i = ap["r_inner"]
    r_c = 0.5 * (ap["r_inner"] + ap["r_outer"])
    r_cline = r_i - 0.5 * RAIL_T
    pose = exit_tangent_pose(width_open, H_MIN)
    ux, uy = pose["chute_dir"]
    ax, ay = pose["anchor_xy"]
    nx_i, ny_i = -uy, ux
    if ax * nx_i + ay * ny_i > 0.0:
        nx_i, ny_i = -nx_i, -ny_i
    nx_o, ny_o = -nx_i, -ny_i
    delta = r_c - r_cline
    th_b = _deg2rad(JOIN_BLEND_TH0)
    th_e = _deg2rad(THETA_EXIT_DEG)
    p0 = (r_cline * math.cos(th_e), r_cline * math.sin(th_e))
    t0 = (-math.sin(th_e), math.cos(th_e))
    # p3 = điểm offset delta*nx_i tại s=0 (đầu đường thẳng máng ra) — KHÔNG cộng
    # thêm JOIN_BLEND_S*u trước khi offset, tránh Bezier phải vươn xa (25 mm+)
    # rồi vọt lố bán kính qua r_c (tường cắt viên tại khuỷu θ_exit, xem
    # verify_single_file_multi jam_pill_vs_L). Đường thẳng offset (song song
    # trục máng, cách đều delta) tự nó luôn đúng khoảng cách — không cần Bezier
    # vươn dài; chỉ cần Bezier NGẮN nối góc cung → điểm đầu đường thẳng.
    p3 = (ax + delta * nx_i, ay + delta * ny_i)
    # Không xoắn lõm vào tâm (túi chết). Uốn G1 tại miệng: ê_θ → û, lệch nhẹ n_in.
    t_mix = _unit2(0.55 * t0[0] + 0.45 * ux + 0.20 * nx_i, 0.55 * t0[1] + 0.45 * uy + 0.20 * ny_i)
    # Handle theo JOIN_HANDLE_FRAC * chord (chord ngắn hẳn nay p3 ở s=0) —
    # không còn hằng số tuyệt đối 10/12 mm (từng dài hơn chord mới → vọt lố).
    herm = _hermite_poly(p0, t_mix, p3, (ux, uy), JOIN_N, l0=None, l3=None)
    # Cung tới θ_exit rồi nối — không túi r↓
    pre: list[tuple[float, float]] = []
    n_pre = 8
    for i in range(n_pre):
        u = i / n_pre
        th = _deg2rad(JOIN_BLEND_TH0 + (THETA_EXIT_DEG - JOIN_BLEND_TH0) * u)
        pre.append((r_cline * math.cos(th), r_cline * math.sin(th)))
    blend = pre + herm
    # p3 nay ở s=0 (không còn "dùng hết" JOIN_BLEND_S bên trong Bezier) — đường
    # thẳng phải chạy đủ EXIT_TRACK_LEN từ p3.
    extra = max(12.0, EXIT_TRACK_LEN)
    straight: list[tuple[float, float]] = []
    for i in range(1, 17):
        s = extra * (i / 16.0)
        straight.append((p3[0] + s * ux, p3[1] + s * uy))
    arc: list[tuple[float, float]] = []
    n_arc = 40
    for i in range(n_arc + 1):
        u = i / n_arc
        th = _deg2rad(THETA_MOUTH_DEG + (JOIN_BLEND_TH0 - THETA_MOUTH_DEG) * u)
        arc.append((r_cline * math.cos(th), r_cline * math.sin(th)))
    rail_pts = arc[:-1] + blend + straight[:10]
    # Exit bắt đầu trước miệng (chồng rail ≥ JOIN_SEAL_OVERLAP)
    exit_inner = herm + straight
    wall_span = ap["width_mm"] + 0.5 * RAIL_T + 0.5 * EXIT_TRACK_WALL

    def _offset_poly(pts: list[tuple[float, float]], off: float) -> list[tuple[float, float]]:
        out: list[tuple[float, float]] = []
        n = len(pts)
        for i in range(n):
            if i == 0:
                dx, dy = pts[1][0] - pts[0][0], pts[1][1] - pts[0][1]
            elif i == n - 1:
                dx, dy = pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]
            else:
                dx = pts[i + 1][0] - pts[i - 1][0]
                dy = pts[i + 1][1] - pts[i - 1][1]
            ln = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / ln, dx / ln
            if nx * nx_o + ny * ny_o < 0.0:
                nx, ny = -nx, -ny
            out.append((pts[i][0] + off * nx, pts[i][1] + off * ny))
        return out

    exit_outer = _offset_poly(exit_inner, wall_span)
    turn = _path_max_turn_deg(arc[-4:] + blend[1:])
    h_u = math.degrees(math.atan2(uy, ux))
    t0 = (-math.sin(th_b), math.cos(th_b))
    t_pre = (-math.sin(th_b), math.cos(th_b))
    h_t = math.degrees(math.atan2(t_pre[1], t_pre[0]))
    g1_end = abs(_ang_diff_deg(_path_heading_deg(blend[-2], blend[-1]), h_u)) < 8.0
    g1_start = abs(_ang_diff_deg(_path_heading_deg(blend[0], blend[1]), h_t)) < 20.0
    r_lane_pts = []
    for x, y in blend:
        s_ch = (x - ax) * ux + (y - ay) * uy
        if s_ch < 2.0 and math.hypot(x, y) < BOWL_IR + 0.5:
            r_lane_pts.append(math.hypot(x, y))
    r_blend_max = max(r_lane_pts) if r_lane_pts else 0.0
    inboard_ok = r_blend_max <= r_cline + 5.0
    return {
        "r_cline": r_cline,
        "r_center": r_c,
        "arc_pts": arc,
        "blend_pts": blend,
        "straight_pts": straight,
        "rail_pts": rail_pts,
        "exit_inner_pts": exit_inner,
        "exit_outer_pts": exit_outer,
        "max_turn_deg": round(turn, 3),
        "g1_start": g1_start,
        "g1_end": g1_end,
        "smooth": bool(turn <= JOIN_MAX_TURN_DEG and g1_end and g1_start and inboard_ok),
        "inboard_ok": inboard_ok,
        "r_blend_max": round(r_blend_max, 3),
        "blend_s_mm": JOIN_BLEND_S,
    }


def _rail_pill_clearance_cut(width_open: float) -> Part.Shape:
    """
    Bao an toàn quanh ĐƯỜNG ĐI THẬT của viên tại khuỷu lane→Exit_Track — cắt
    trực tiếp khỏi Inner_Lane_Rail, không phụ thuộc hình Hermite của tường
    (đường cong nối G1 không giữ khoảng-cách-vuông-góc hằng số tới viên, có
    thể phình vào đúng chỗ viên đi qua ở W lớn — xem verify_single_file_*
    jam_pill_vs_L). Chỉ cắt QUANH khuỷu (θ∈[JOIN_BLEND_TH0, θ_exit] + đoạn
    đầu máng ra), KHÔNG đụng phần cung chính (mouth→JOIN_BLEND_TH0) vẫn cần
    tường để dẫn hướng viên.
      (a) cung bán kính r_c (tâm viên thật) từ JOIN_BLEND_TH0 → θ_exit
      (b) đoạn thẳng dọc trục máng (tâm viên thật khi đã vào máng) s∈[0,30] mm
    """
    ap = aperture_from_opens(width_open, H_MIN)
    r_c = 0.5 * (ap["r_inner"] + ap["r_outer"])
    D_est = max(0.5, float(width_open) - PILL_CLEAR_XY)
    clear_d = D_est + RAIL_T + 1.0
    n = 16
    arc_pts = [
        (
            r_c * math.cos(_deg2rad(JOIN_BLEND_TH0 + (THETA_EXIT_DEG - JOIN_BLEND_TH0) * (i / n))),
            r_c * math.sin(_deg2rad(JOIN_BLEND_TH0 + (THETA_EXIT_DEG - JOIN_BLEND_TH0) * (i / n))),
        )
        for i in range(n + 1)
    ]
    cut_arc = _wall_from_segments(arc_pts, clear_d, GAP0, RAIL_H)
    pose = exit_tangent_pose(width_open, H_MIN)
    ax, ay = pose["anchor_xy"]
    ux, uy = pose["chute_dir"]
    line_pts = [(ax + s * ux, ay + s * uy) for s in (0.0, 10.0, 20.0, 30.0)]
    cut_line = _wall_from_segments(line_pts, clear_d, GAP0, RAIL_H)
    return _refine(cut_arc.fuse(cut_line))


def make_scale_height(width_open: float) -> Part.Shape:
    s = width_clamp_s(width_open)
    marks = []
    for dh in range(0, int(H_TRAVEL) + 1, 2):
        z = GAP0 + H_MIN + dh
        marks.append(_box(1.2, 6.0, 0.6, s + H_RAIL_TOP + 5.0, 0.5 * CLAMP_W + 2.0, z))
    body = marks[0]
    for m in marks[1:]:
        body = body.fuse(m)
    return _to_adj_frame(body)


def make_screws(width_open: float, height_open: float) -> list:
    """Bu-lông kẹp núm vặn lớn (thay lò xo tì trước đây) — cả 2 thanh tịnh tiến
    (Width_Carriage=ngang, Height_Scraper=dọc) đều siết bằng bu-lông phương NGANG
    (trục Y), đặt ở độ cao thấp trong lòng đĩa. Vị trí bám theo carriage/slider nên
    LUÔN nằm đúng trên ray T dù trượt tới đâu trong dải W_MIN..W_MAX / H_MIN..H_MAX
    (ray liền suốt hành trình). Xem _width_bolt_sites()/_height_bolt_site()."""
    _ = height_open
    s = width_clamp_s(width_open)
    out = []
    for site in _width_bolt_sites(s):
        sh = _knob_bolt_along(site["knob_origin"], site["axis"], site["shank_len"])
        out.append((site["name"], _refine(_to_adj_frame(sh))))
    h_site = _height_bolt_site(s)
    sh = _knob_bolt_along(h_site["knob_origin"], h_site["axis"], h_site["shank_len"])
    out.append((h_site["name"], _refine(_to_adj_frame(sh))))
    return out


def make_lane_entrance_marker() -> Part.Shape:
    """
    Khung hồng — HỌNG VÀO lane nhìn từ Top.
    Không có sàn — viên luôn tiếp xúc đĩa; chỉ mép + mũi tên treo.
    """
    th0 = ENTRANCE_TH0
    th1 = ENTRANCE_TH1
    r_in = GUIDE_R1 + 0.5 * GUIDE_T + 0.3
    r_out = CHANNEL_R_OUTER - 0.3
    # Marker treo trên H_MAX — không đứng trên đĩa (trước đây môi GAP0 chặn họng)
    z_mark = GAP0 + H_MAX + 4.0
    th_lip = th0 + 3.0
    lip_in = _place_oriented_box(
        5.0, 3.5, 4.0,
        (r_in + 2.0) * math.cos(_deg2rad(th_lip)),
        (r_in + 2.0) * math.sin(_deg2rad(th_lip)),
        z_mark,
        th_lip,
    )
    lip_out = _place_oriented_box(
        5.0, 3.5, 4.0,
        (r_out - 2.0) * math.cos(_deg2rad(th_lip)),
        (r_out - 2.0) * math.sin(_deg2rad(th_lip)),
        z_mark,
        th_lip,
    )
    th_c = 0.5 * (th0 + THETA_MOUTH_DEG)
    r_c = 0.5 * (r_in + r_out)
    arrow = _place_oriented_box(
        16.0, 4.0, 2.2,
        r_c * math.cos(_deg2rad(th_c)),
        r_c * math.sin(_deg2rad(th_c)),
        z_mark + 2.0,
        th_c + 90.0,
    )
    return _refine(lip_in.fuse(lip_out).fuse(arrow))


def make_exit_track(width_open: float, height_open: float) -> Part.Shape:
    """
    Máng gần hướng tâm, đáy HỞ. Tường trong nối G1 với lane (cùng Hermite);
    miệng bo tròn — không tai vuông.
    """
    ap = aperture_from_opens(width_open, height_open)
    W = ap["width_mm"]
    H = ap["height_mm"]
    t = EXIT_TRACK_WALL
    geo = lane_exit_join_geo(width_open)
    # Hermite: luôn hộp — Face tự cắt ở W=12/16/20/22
    wall_in = _wall_from_segments(geo["exit_inner_pts"], t, GAP0, H + 6.0)
    wall_out = _wall_from_segments(geo["exit_outer_pts"], t, GAP0, H + 6.0)
    pose = exit_tangent_pose(width_open, height_open)
    roof = _box(EXIT_TRACK_LEN, W + 2 * t, t, pose["x0_along_mm"], -0.5 * W - t, GAP0 + H + 0.3)
    roof = _place_tangent_exit(roof, width_open, height_open)
    p_i = geo["exit_inner_pts"][0]
    p_o = geo["exit_outer_pts"][0]
    cap_i = _cyl_z(t, H + 6.0, p_i[0], p_i[1], GAP0)
    cap_o = _cyl_z(t, H + 6.0, p_o[0], p_o[1], GAP0)
    key = _join_seal_key(width_open, max(t, RAIL_T), H + 6.0)
    body = wall_in
    for extra in (key, wall_out, roof, cap_i, cap_o):
        try:
            fused = body.fuse(extra)
            if _shape_ok(fused, 0.75 * float(getattr(body, "Volume", 1.0) or 1.0)):
                body = fused
        except Exception:
            continue
    if _shape_ok(body, 8.0):
        return _refine(body)
    try:
        return _refine(wall_in.fuse(key))
    except Exception:
        return wall_in


def make_exit_mouth_marker(width_open: float, height_open: float) -> Part.Shape:
    """
    Khung hồng đánh dấu miệng máng — chỉ 2 trụ + xà trên cao.
    Lòng kênh (W × H) hoàn toàn trống — không chặn viên ra.
    """
    ap = aperture_from_opens(width_open, height_open)
    W = ap["width_mm"]
    H = ap["height_mm"]
    pose = exit_tangent_pose(width_open, height_open)
    x0 = pose["x0_along_mm"]
    clear_z = 2.0
    post_w = 3.0
    post_t = 3.0
    post_l = _box(
        post_t, post_w, H + 8.0,
        x0 - 0.5, -0.5 * W - post_w - 0.5, GAP0,
    )
    post_r = _box(
        post_t, post_w, H + 8.0,
        x0 - 0.5, 0.5 * W + 0.5, GAP0,
    )
    lintel = _box(
        post_t, W + 2.0 * post_w + 1.0, 2.5,
        x0 - 0.5, -0.5 * W - post_w - 0.5, GAP0 + H + clear_z,
    )
    return _place_tangent_exit(_refine(post_l.fuse(post_r).fuse(lintel)), width_open, height_open)


def _overlap_volume(a: Part.Shape, b: Part.Shape) -> float:
    try:
        return float(getattr(a.common(b), "Volume", 0.0) or 0.0)
    except Exception:
        return 0.0


def _to_mesh(shape: Part.Shape, deflection: float = 0.75):
    """Tessellate BREP → triangle mesh for surface collision."""
    import MeshPart

    return MeshPart.meshFromShape(
        Shape=shape,
        LinearDeflection=float(deflection),
        AngularDeflection=0.5,
    )


def _mesh_intersect_facets(a: Part.Shape, b: Part.Shape, deflection: float = 0.75) -> int:
    """Number of intersection facets between two tessellated surfaces (0 = clear)."""
    try:
        ma = _to_mesh(a, deflection)
        mb = _to_mesh(b, deflection)
        hit = ma.intersect(mb)
        return int(getattr(hit, "CountFacets", 0) or 0)
    except Exception:
        # Fallback: solid volume overlap counts as jam
        return 1 if _overlap_volume(a, b) > 1e-2 else 0


def _mesh_jam(
    a: Part.Shape,
    b: Part.Shape,
    deflection: float = 0.85,
    solid_thr: float = 0.05,
) -> tuple[bool, int, float]:
    """
    Mesh surface collision + solid confirm.
    Near-touch tessellation can yield a few facets with Volume≈0 — not a jam.
    """
    fac = _mesh_intersect_facets(a, b, deflection)
    if fac <= 0:
        return False, 0, 0.0
    vol = _overlap_volume(a, b)
    return (vol > solid_thr), fac, vol


def _grid(lo: float, hi: float, step: float) -> list[float]:
    vals, v = [], lo
    while v <= hi + 1e-9:
        vals.append(round(v, 6))
        v += step
    if vals[-1] < hi - 1e-9:
        vals.append(hi)
    return vals


def recommend_gap_mm(D, T, clear_xy=PILL_CLEAR_XY, clear_z=PILL_CLEAR_Z) -> dict:
    """
    Máng / khe: rộng & cao hơn vật 1 mm, kẹp trong dải chỉnh 2–26 (W) / 2–26 (H).
    Vật kích thước 2–26 mm luôn có khẩu độ khả thi (tại max: clear có thể < 1 mm).
    """
    w_want = float(D) + float(clear_xy)
    h_want = float(T) + float(clear_z)
    notes = []
    w = w_want
    h = h_want
    if w < WIDTH_MIN and WIDTH_MIN < 2.0 * D:
        w = WIDTH_MIN
        notes.append("W_bumped_to_W_MIN")
    if h < HEIGHT_MIN and HEIGHT_MIN < 2.0 * T:
        h = HEIGHT_MIN
        notes.append("H_bumped_to_H_MIN")
    if w > WIDTH_MAX:
        w = WIDTH_MAX
        notes.append("W_clamped_to_W_MAX")
    if h > HEIGHT_MAX:
        h = HEIGHT_MAX
        notes.append("H_clamped_to_H_MAX")
    obj_in = (WIDTH_MIN - 1e-9) <= float(D) <= (WIDTH_MAX + 1e-9) and (
        HEIGHT_MIN - 1e-9
    ) <= float(T) <= (HEIGHT_MAX + 1e-9)
    fit = w + 1e-9 >= float(D) and h + 1e-9 >= float(T)
    return {
        "W": round(w, 3),
        "H": round(h, 3),
        "W_want": round(w_want, 3),
        "H_want": round(h_want, 3),
        "in_adjust_range": bool(obj_in and fit),
        "notes": notes,
        "clear_xy": clear_xy,
        "clear_z": clear_z,
    }


def _pill_channel_fit(D, T, W, H) -> dict:
    pass_one_w, pass_one_h = W >= D - 1e-9, H >= T - 1e-9
    block_dw, block_dh = W < 2 * D - 1e-9, H < 2 * T - 1e-9
    r_o, r_i = CHANNEL_R_OUTER, CHANNEL_R_OUTER - W
    r_c = 0.5 * (r_i + r_o)
    sits = (r_c - 0.5 * D) >= r_i - 1e-6 and (r_c + 0.5 * D) <= r_o + 1e-6
    return {
        "pass_one_w": pass_one_w,
        "pass_one_h": pass_one_h,
        "block_double_w": block_dw,
        "block_double_h": block_dh,
        "single_file": pass_one_w and pass_one_h and block_dw and block_dh,
        "r_center_mm": round(r_c, 3),
        "sits_in_channel": sits,
        "two_abreast_would_fit": W >= 2 * D,
        "radial_clear_in_mm": round((r_c - 0.5 * D) - r_i, 3),
        "radial_clear_out_mm": round(r_o - (r_c + 0.5 * D), 3),
    }


def min_angular_pitch_deg(D: float, W: float, margin_mm: float = 1.0) -> float:
    """
    Δθ tối thiểu giữa 2 viên (thả cùng lúc, cùng cỡ) để KHÔNG va khi CẢ HAI
    cùng đi qua nút thắt cổ chai: MIỆNG MÁNG RA (Exit_Track).

    Trên đĩa (chưa vào máng): θ̇=ω chung cho mọi viên, không lực viên-viên
    ⇒ Δθ_ij = θ0_i−θ0_j giữ NGUYÊN (mod 360) suốt pha này — tưởng như cứ
    Δθ>0 là an toàn. NHƯNG khi viên trước (i) cắt θ_exit và bắt đầu vào máng,
    tốc độ dọc máng bị ma sát ghìm rất chậm lúc mới vào:
      s_dot = ω·r·drive_net,  drive_net = sinβ − μ_wall·cosβ  (β chỉ vừa đủ
      thắng khóa ma sát — drive_net ≪ 1 theo thiết kế, xem exit_wall_friction_beta).
    Viên sau (j) tới θ_exit trễ hơn Δt = Δθ_rad/ω; lúc đó viên i mới đi được
      s_i(Δt) ≈ ω·r_lane·drive_net·Δt = r_lane·drive_net·Δθ_rad
    (ω triệt tiêu — khoảng cách dọc máng lúc viên sau bắt đầu vào KHÔNG phụ
    thuộc ω, chỉ phụ thuộc Δθ và drive_net). Vì drive_net nhỏ (~0.09 với
    μ_wall=0.35, margin 5°), khoảng cách "hội tụ" tại miệng máng bị NÉN theo
    hệ số drive_net so với khoảng cách hình học Δθ·r_lane ngây thơ — đây là
    nút thắt cổ chai thật của cơ cấu (máng phải giữ β nhỏ để tự hãm khi đĩa
    dừng, nên vào máng luôn chậm). Sau khi viên sau cũng đã vào máng, khoảng
    cách hai viên KHÔNG giảm thêm (s_dot tăng theo r, viên trước luôn nhanh
    hơn hoặc bằng) ⇒ đây là khoảng cách NHỎ NHẤT suốt hành trình.
      Δθ_min = (D + margin) / (r_lane · drive_net)   [rad]
    """
    ap = aperture_from_opens(W, H_MIN)
    r_lane = 0.5 * (ap["r_inner"] + ap["r_outer"])
    drive_net = max(1e-6, float(exit_wall_friction_beta()["drive_net"]))
    return math.degrees((float(D) + float(margin_mm)) / (r_lane * drive_net))


def _place_n_pills_no_overlap(
    n: int,
    D: float,
    T: float,
    shape: str,
    seed: int,
    pitch_min: float,
    dtheta_min_deg: float = 0.0,
) -> list[tuple[float, float]]:
    """
    Rớt n viên cùng lúc, vị trí ngẫu nhiên, không chồng nhau lúc thả (rejection
    sampling). Ngoài khoảng cách Euclid ≥ pitch_min, còn ép Δθ ≥ dtheta_min_deg
    (xem min_angular_pitch_deg) — nếu không, 2 viên ở bán kính khác nhau nhưng
    θ gần nhau có thể va khi CÙNG hội tụ vào lane (khoảng cách kính không giúp
    được nữa một khi cả hai bị ép về cùng bán kính lane).
    """
    rng = random.Random(seed)
    half = 0.5 * D
    r_lo = 0.5 * HUB_D + half + 2.0
    r_hi = CHANNEL_R_OUTER - half - 1.0
    placed_xy: list[tuple[float, float]] = []
    placed_rth: list[tuple[float, float]] = []
    max_attempts = max(4000, n * 800)
    attempts = 0
    while len(placed_rth) < n and attempts < max_attempts:
        attempts += 1
        r = rng.uniform(r_lo, r_hi)
        th = rng.uniform(0.0, 360.0)
        x = r * math.cos(_deg2rad(th))
        y = r * math.sin(_deg2rad(th))
        ok = True
        for (pr, pth), (px, py) in zip(placed_rth, placed_xy):
            if math.hypot(x - px, y - py) < pitch_min:
                ok = False
                break
            if dtheta_min_deg > 0.0:
                dth = abs(((th - pth + 180.0) % 360.0) - 180.0)
                if dth < dtheta_min_deg:
                    ok = False
                    break
        if ok:
            placed_xy.append((x, y))
            placed_rth.append((r, th))
    return placed_rth


PILL_POSES = ("flat", "stand")  # stand = viên dựng (cao = D); ball bỏ qua stand


def _pill_extents(D: float, T: float, pose: str, shape: str) -> tuple[float, float]:
    """(xy_span, z_height) của viên trên đĩa."""
    if shape == "ball" or abs(D - T) < 1e-9:
        return float(D), float(D)
    if pose == "stand":
        return float(T), float(D)  # dựng trên cạnh: đáy hẹp T, cao D
    return float(D), float(T)


def _spiral_r_at_theta(r0, r1, th0_deg, th1_deg, th_deg: float) -> float | None:
    """Bán kính lưỡi xoắn tại θ (hỗ trợ θ bọc 0..360 vs th0 âm)."""
    span = th1_deg - th0_deg
    if abs(span) < 1e-9:
        return None
    u_hit = None
    for k in (-1, 0, 1):
        u = (th_deg + 360.0 * k - th0_deg) / span
        if -0.02 <= u <= 1.02:
            u_hit = _clamp(u, 0.0, 1.0)
            break
    if u_hit is None:
        return None
    return r0 + (r1 - r0) * u_hit


def _ang_between(th_deg: float, a_deg: float, b_deg: float) -> bool:
    """θ ∈ [a,b] trên vòng tròn (a→b theo +θ, có thể bọc)."""
    th = th_deg % 360.0
    a = a_deg % 360.0
    b = b_deg % 360.0
    if a <= b:
        return a - 1e-9 <= th <= b + 1e-9
    return th >= a - 1e-9 or th <= b + 1e-9


def _trace_pill_egress(
    D: float,
    T: float,
    W: float,
    H: float,
    r0: float,
    th0: float,
    pose0: str,
    shape: str = "tablet",
    steps_per_rev: int = 48,
    max_revs: float = 5.0,
) -> dict:
    """
    Quỹ đạo rời rạc trên đĩa. Guide đẩy ra; lane kẹp r; scraper hạ stand→flat;
    thoát Exit_Track. Không xuyên tường: PyBullet tube_l_egress_pybullet.py.
    """
    ap = aperture_from_opens(W, H)
    r_i, r_o = ap["r_inner"], ap["r_outer"]
    r_c = 0.5 * (r_i + r_o)
    r_hub = DIR_R0 - 2.0
    r_max = CHANNEL_R_OUTER - 0.4
    pose = "flat" if shape == "ball" else pose0
    r = float(_clamp(r0, r_hub, r_max))
    th = float(th0)
    knocked = False
    entered_lane = False
    dth = 360.0 / steps_per_rev
    n_max = int(max_revs * steps_per_rev)
    path_pts: list[tuple[float, float, str]] = []

    for step in range(n_max):
        th = (th + dth) % 360.0
        xy_span, z_h = _pill_extents(D, T, pose, shape)

        in_lane_ang = THETA_MOUTH_DEG - 2.0 <= th <= THETA_EXIT_DEG + dth + 2.0
        in_lane_r = (r + 0.5 * xy_span) >= r_i - 0.5 and (r - 0.5 * xy_span) <= r_o + 0.5
        if in_lane_ang and in_lane_r:
            entered_lane = True
            if pose == "stand" and z_h > H - 0.05:
                # scraper / nóc máng: dựng sát H cũng bị quệt → nằm
                pose = "flat"
                knocked = True
                xy_span, z_h = _pill_extents(D, T, pose, shape)
            r = 0.85 * r + 0.15 * r_c
            r = _clamp(r, r_i + 0.5 * xy_span, r_o - 0.5 * xy_span)

            # thoát khi qua θ_exit và chiều cao vừa máng (H = T+1 mm)
            if z_h <= H + 0.25 and th >= THETA_EXIT_DEG - dth:
                return {
                    "exited": True,
                    "pose_exit": "flat" if pose == "flat" or z_h <= T + PILL_CLEAR_Z else pose,
                    "knocked_down": knocked,
                    "entered_lane": True,
                    "steps": step + 1,
                    "revs": round((step + 1) / steps_per_rev, 3),
                    "r_end": round(r, 2),
                    "th_end": round(th, 2),
                    "path": path_pts,
                }
        if step % 3 == 0:
            path_pts.append((round(r, 2), round(th, 2), pose))

        rg = _spiral_r_at_theta(GUIDE_R0, GUIDE_R1, GUIDE_TH0, GUIDE_TH1, th)
        if rg is not None and r <= rg + 0.5 * GUIDE_T + 0.55 * xy_span + 1.5:
            r = max(r, min(r_max, rg + 0.5 * GUIDE_T + 0.45 * xy_span))

        # Họng → lane (W=pill+1): drift về tâm kênh
        if _ang_between(th, ENTRANCE_TH0 - 2.0, THETA_EXIT_DEG + 2.0):
            if r >= GUIDE_R1 - 4.0:
                r = 0.65 * r + 0.35 * r_c
                r = _clamp(r, GUIDE_R1 + 0.2 * xy_span, r_max - 0.05)

        if r + 0.5 * xy_span > r_max:
            r = r_max - 0.5 * xy_span
        if (
            _ang_between(th, GUIDE_TH1 - 8.0, GUIDE_TH1 + 5.0)
            and r + 0.5 * xy_span < GUIDE_R1 - 0.5
        ):
            r = max(r_hub, r - 1.2)

    return {
        "exited": False,
        "pose_exit": pose,
        "knocked_down": knocked,
        "entered_lane": entered_lane,
        "steps": n_max,
        "revs": max_revs,
        "r_end": round(r, 2),
        "th_end": round(th, 2),
        "trapped": True,
        "path": path_pts,
    }


def _egress_start_grid(D: float) -> list[tuple[float, float]]:
    """Lưới (r, θ) phủ đĩa (tránh hub / ngoài bowl)."""
    r_lo = DIR_R0 + 0.5 * D + 1.0
    r_hi = CHANNEL_R_OUTER - 0.5 * D - 1.0
    rs = [
        r_lo,
        0.35 * r_lo + 0.65 * DIR_R1,
        0.5 * (DIR_R1 + FUNNEL_R1),
        0.55 * FUNNEL_R1 + 0.45 * r_hi,
        r_hi,
    ]
    ths = [0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0]
    return [(r, th) for r in rs for th in ths]


def _pill_tunnel_hits_along_path(
    D: float,
    T: float,
    W: float,
    H: float,
    path: list,
    shape: str,
    guide,
    rail,
    bowl,
    exit_track,
) -> int:
    """Đếm mẫu tâm viên nằm sâu trong tường (xuyên component)."""
    hits = 0
    for r, th, pose in path[::3]:
        xy_span, z_h = _pill_extents(D, T, pose, shape)
        z_h = min(z_h, H + 0.2)
        cx = r * math.cos(_deg2rad(th))
        cy = r * math.sin(_deg2rad(th))
        # probe nhỏ — chỉ bắt xuyên sâu, không đếm tiếp xúc bề mặt
        rad = max(0.25, 0.15 * xy_span)
        probe = _cyl_z(rad, max(0.3, 0.35 * z_h), cx, cy, DISC_TOP_Z + 0.05)
        thr = 6.0
        if _overlap_volume(probe, guide) > thr or _overlap_volume(probe, rail) > thr:
            hits += 1
            continue
        # gần vành: tiếp xúc bowl bình thường — chỉ fail nếu tâm sâu trong tường
        if r < CHANNEL_R_OUTER - 0.55 * xy_span - 1.0:
            if _overlap_volume(probe, bowl) > thr:
                hits += 1
                continue
        if th >= THETA_EXIT_DEG + 2.0 and r >= CHANNEL_R_OUTER - 0.5 * W - 1.0:
            if _overlap_volume(probe, exit_track) > thr:
                hits += 1
    return hits


SIZE_SWEEP_MM = [2, 3, 4, 5, 6, 8, 10, 12, 15, 18, 20, 22, 24, 26]


def make_size_range_datasets() -> list[dict]:
    """Ball (D=T=s) + tablet (D=s, T=max(2, s/2)) cho mỗi s ∈ 2..26."""
    out = []
    for s in SIZE_SWEEP_MM:
        sf = float(s)
        out.append({"id": f"size_ball_{s:g}", "D": sf, "T": sf, "shape": "ball"})
        t = max(2.0, round(0.5 * sf, 2))
        if abs(t - sf) > 0.05:
            out.append(
                {"id": f"size_tab_{s:g}x{t:g}", "D": sf, "T": float(t), "shape": "tablet"}
            )
    return out


OMEGA_DISC = 2.0 * math.pi  # rad/s — 1 vòng/s (chuẩn hoá; tỉ lệ thời gian)
SANITY_SEED = 20260811
SANITY_N = 100


def _crossed_unwrapped(th0_deg: float, th1_deg: float, target_deg: float) -> bool:
    """True nếu góc bung [th0, th1] cắt target + 360k."""
    lo = min(th0_deg, th1_deg) - 360.0
    hi = max(th0_deg, th1_deg) + 360.0
    k0 = int(math.floor(lo / 360.0)) - 1
    k1 = int(math.floor(hi / 360.0)) + 2
    for k in range(k0, k1 + 1):
        t = target_deg + 360.0 * k
        if th0_deg < t <= th1_deg:
            return True
    return False


def _cad_theta_fences(W: float, H: float) -> list[dict]:
    """
    Tường gần-đứng (θ ≈ const) còn lại trên đĩa — vật ê_θ phải qua được.
    Sau khi xóa hàng rào thoát / thành 30 mm / môi họng: chỉ còn mấu scraper (z≥H)
    và reject ngắn tại tip (trượt +r vào họng, không kẹt θ).
    """
    W = _clamp(W, WIDTH_MIN, WIDTH_MAX)
    H = _clamp(H, HEIGHT_MIN, HEIGHT_MAX)
    r_i = CHANNEL_R_OUTER - W
    fences = [
        {
            "name": "scraper_entry_tab",
            "th_deg": THETA_MOUTH_DEG,
            "r_lo": r_i + 0.6,
            "r_hi": CHANNEL_R_OUTER - 0.4,
            "z_lo": GAP0 + H,
            "z_hi": GAP0 + H + SCRAPER_ENTRY_H,
            "on_hit": "knock",
        },
        {
            "name": "reject_tip",
            "th_deg": GUIDE_TH1,
            "r_lo": GUIDE_R1 - REJECT_LEN,
            "r_hi": GUIDE_R1 + 0.2,
            "z_lo": GAP0,
            "z_hi": GAP0 + GUIDE_H,
            "on_hit": "slide_out",
        },
    ]
    if EXIT_GUARD_INBOARD > 0.5:
        r_cline = r_i - 0.5 * RAIL_T
        fences.append(
            {
                "name": "exit_inboard_guard",
                "th_deg": THETA_EXIT_DEG,
                "r_lo": r_cline - EXIT_GUARD_INBOARD,
                "r_hi": r_cline + 0.5 * RAIL_T,
                "z_lo": GAP0,
                "z_hi": GAP0 + RAIL_H,
                "on_hit": "jam",
            }
        )
    return fences


def simulate_pill_mechanics(
    D: float,
    T: float,
    W: float,
    H: float,
    r0: float,
    th0: float,
    pose0: str,
    shape: str = "tablet",
    omega: float = OMEGA_DISC,
    dth_deg: float = 1.0,
    max_revs: float = 8.0,
    path_every: int = 8,
) -> dict:
    """
    Phương trình trên đĩa (cực):

      Không tiếp xúc máng (no-slip):
          ṙ = 0
          θ̇ = ω
          v = ω r ê_θ     (dính đĩa, không trượt xuyên tâm)

      Tiếp xúc tường Guide / phễu / rail / bowl (được trượt trên đĩa):
          r ← max(r, r_wall(θ) + half_t + half_pill)   # đẩy +r (inelastic)
          θ̇ = ω                                       # đĩa vẫn dẫn góc
          ṙ ≠ 0 chỉ tại bước có contact

      Scraper: nếu đứng và z > H → hạ flat (va lưỡi).
      Hàng rào θ (CAD): knock / trượt +r vào họng — không được kẹt θ.
      Thoát: cắt θ_exit khi đang trong lane và z ≤ H.

    Nhiều vòng được phép (max_revs).
    """
    W = _clamp(W, WIDTH_MIN, WIDTH_MAX)
    H = _clamp(H, HEIGHT_MIN, HEIGHT_MAX)
    xy0, _z0 = _pill_extents(D, T, "flat" if shape == "ball" else pose0, shape)
    r_hub = 0.5 * HUB_D + 0.5 * xy0 + 1.0
    r_rim = CHANNEL_R_OUTER - 0.5 * xy0 - 0.2
    pose = "flat" if shape == "ball" else pose0
    r = float(_clamp(r0, r_hub, r_rim))
    th_unw = float(th0)
    dt = math.radians(dth_deg) / max(omega, 1e-9)
    n_max = int(max_revs * 360.0 / dth_deg)
    r_i = CHANNEL_R_OUTER - W
    ep = exit_tangent_pose(W, H)
    ux, uy = ep["chute_dir"]
    ax, ay = ep["anchor_xy"]
    drive_net = float(ep["drive_net_friction"])
    in_chute = False
    s_chute = 0.0
    entered_lane = False
    blocked_by: str | None = None
    fences = _cad_theta_fences(W, H)

    knocked = False
    n_contact = n_free = illegal_slip = 0
    n_disc = n_disc_miss = 0
    max_free_dr = 0.0
    max_dth_err_deg = 0.0
    path: list[tuple] = []
    disc_miss_sample: list[dict] = []

    def _half():
        return 0.5 * _pill_extents(D, T, pose, shape)[0]

    def _zh():
        return _pill_extents(D, T, pose, shape)[1]

    def _in_lane(rr: float, half: float) -> bool:
        return (rr - half) >= (r_i - 1.2) and (rr + half) <= (CHANNEL_R_OUTER + 0.6)

    def _on_disc_face(rr: float, half: float) -> bool:
        """Tâm viên còn trên mặt vành đĩa (ngoài lỗ trục, trong Ø đĩa)."""
        r_hole = 0.5 * (SHAFT_D + 0.2) + 0.3
        return (rr - 0.45 * 2.0 * half) >= r_hole and (rr + 0.45 * 2.0 * half) <= (DISC_R + 0.5)

    for step in range(n_max):
        th_prev = th_unw
        r_prev = r
        th_unw = th_prev + dth_deg
        th = th_unw % 360.0
        dth_err = abs((th_unw - th_prev) - dth_deg)
        if dth_err > max_dth_err_deg:
            max_dth_err_deg = dth_err

        contact = False
        half = _half()
        z_h = _zh()

        if in_chute:
            # Trên máng: F_dọc = F(sinβ − μ_wall cosβ); ds = r·drive_net·dθ
            ds = r * max(0.0, drive_net) * math.radians(dth_deg)
            s_chute += max(0.0, ds)
            px = ax + s_chute * ux
            py = ay + s_chute * uy
            r = math.hypot(px, py)
            th = (math.degrees(math.atan2(py, px)) + 360.0) % 360.0
            contact = True
            half = _half()
            z_h = _zh()
        else:
            # Bowl (tường ngoài cố định) — chỉ khi chưa vào máng
            r_bowl = CHANNEL_R_OUTER - half - 0.05
            if r > r_bowl + 1e-9:
                r = r_bowl
                contact = True

            # Tường mỏng: chỉ khi overlap (không dịch xuyên khoảng không)
            rw = _inner_wall_r(th, W)
            if rw is not None:
                on_spiral = _spiral_r_at_theta(
                    GUIDE_R0, GUIDE_R1, GUIDE_TH0, GUIDE_TH1, th
                ) is not None
                wall_t = GUIDE_T if on_spiral else RAIL_T
                clear = 0.5 * wall_t + half + 0.15
                if abs(r - rw) <= clear + WALL_CAPTURE_TOL_MM:
                    r_out = rw + 0.5 * wall_t + half + 0.15
                    if r < r_out:
                        r = min(r_out, r_bowl)
                        contact = True

            # Hub
            r_min = 0.5 * HUB_D + half + 0.8
            if r < r_min - 1e-9:
                r = r_min
                contact = True

            # Tường θ CAD: vật ê_θ cắt tường nếu chồng r và z
            for fn in fences:
                if not _crossed_unwrapped(th_prev, th_unw, fn["th_deg"]):
                    continue
                r_hit = (r + half) >= fn["r_lo"] - 0.2 and (r - half) <= fn["r_hi"] + 0.2
                z_hit = z_h > fn["z_lo"] + 1e-9
                if not (r_hit and z_hit):
                    continue
                contact = True
                if fn["on_hit"] == "knock" and pose == "stand" and z_h > H - 0.05:
                    pose = "flat"
                    knocked = True
                    half = _half()
                    z_h = _zh()
                    r = _clamp(r, 0.5 * HUB_D + half + 0.8, CHANNEL_R_OUTER - half - 0.05)
                    continue
                if fn["on_hit"] == "slide_out":
                    r = min(fn["r_hi"] + half + 0.2, CHANNEL_R_OUTER - half - 0.05)
                    continue
                if fn["on_hit"] == "jam":
                    blocked_by = fn["name"]
                    th_unw = th_prev
                    th = th_unw % 360.0
                    break

            # Scraper trong lane: hạ viên đứng nếu cao hơn khe H
            if (
                pose == "stand"
                and z_h > H - 0.05
                and _ang_between(th, THETA_MOUTH_DEG - 1.0, THETA_EXIT_DEG + 1.0)
                and _in_lane(r, half)
            ):
                pose = "flat"
                knocked = True
                contact = True
                half = _half()
                z_h = _zh()
                r = _clamp(r, 0.5 * HUB_D + half + 0.8, CHANNEL_R_OUTER - half - 0.05)

        if contact:
            n_contact += 1
        else:
            n_free += 1
            dr_free = abs(r - r_prev)
            if dr_free > max_free_dr:
                max_free_dr = dr_free
            if dr_free > 1e-6:
                illegal_slip += 1

        # Trên đĩa: đáy z = DISC_TOP_Z tới khi rơi khỏi mép (r > DISC_R)
        z_bottom = DISC_TOP_Z
        off_disc = r > (DISC_R + 0.2)
        # Trên máng: tiếp xúc tới khi tâm viên qua mép đĩa (được nhô vành)
        on_face = (r <= DISC_R + 0.2) if in_chute else _on_disc_face(r, half)
        guides_lift = GAP0 <= DISC_TOP_Z + 0.2
        if on_face and not off_disc:
            n_disc += 1
            if abs(z_bottom - DISC_TOP_Z) > 1e-12 or guides_lift:
                n_disc_miss += 1
                if len(disc_miss_sample) < 8:
                    disc_miss_sample.append(
                        {
                            "step": step + 1,
                            "r": round(r, 2),
                            "th": round(th, 2),
                            "z_bottom": z_bottom,
                            "reason": "lifted" if guides_lift else "z_off_disc",
                        }
                    )
        elif not (in_chute and off_disc):
            n_disc_miss += 1
            if len(disc_miss_sample) < 8:
                disc_miss_sample.append(
                    {
                        "step": step + 1,
                        "r": round(r, 2),
                        "th": round(th, 2),
                        "z_bottom": z_bottom,
                        "reason": "xy_off_disc_before_rim",
                    }
                )

        if step % max(1, path_every) == 0:
            path.append((round(r, 2), round(th, 2), pose, int(contact), z_bottom))

        if (not entered_lane) and _in_lane(r, half) and _ang_between(th, THETA_MOUTH_DEG - 1.0, THETA_EXIT_DEG + 1.0):
            entered_lane = True

        if (not in_chute) and _crossed_unwrapped(th_prev, th_unw, THETA_EXIT_DEG) and _in_lane(r, half) and z_h <= H + 0.25:
            in_chute = True
            s_chute = 0.0

        disc_ok = n_disc_miss == 0 and n_disc > 0
        if in_chute and off_disc:
            return {
                "exited": True,
                "pose_exit": pose,
                "knocked_down": knocked,
                "steps": step + 1,
                "revs": round((step + 1) * dth_deg / 360.0, 3),
                "t_s": round((step + 1) * dt, 4),
                "r_end": round(r, 2),
                "th_end": round(th, 2),
                "n_contact": n_contact,
                "n_free": n_free,
                "illegal_slip": illegal_slip,
                "max_free_dr_mm": round(max_free_dr, 6),
                "max_dth_err_deg": round(max_dth_err_deg, 9),
                "omega_rad_s": omega,
                "n_disc_steps": n_disc,
                "n_disc_miss": n_disc_miss,
                "disc_contact_every_step": disc_ok,
                "z_bottom_mm": DISC_TOP_Z,
                "off_disc": True,
                "s_chute_mm": round(s_chute, 2),
                "entered_lane": True,
                "blocked_by": blocked_by,
                "disc_miss_sample": disc_miss_sample,
                "eq": "chute: s_dot=(omega*r)*(sin(beta)-mu_wall*cos(beta)); z=0 until r>DISC_R",
                "path": path,
            }

    return {
        "exited": False,
        "pose_exit": pose,
        "knocked_down": knocked,
        "steps": n_max,
        "revs": max_revs,
        "t_s": round(n_max * dt, 4),
        "r_end": round(r, 2),
        "th_end": round(th_unw % 360.0, 2),
        "n_contact": n_contact,
        "n_free": n_free,
        "illegal_slip": illegal_slip,
        "max_free_dr_mm": round(max_free_dr, 6),
        "max_dth_err_deg": round(max_dth_err_deg, 9),
        "omega_rad_s": omega,
        "n_disc_steps": n_disc,
        "n_disc_miss": n_disc_miss,
        "disc_contact_every_step": n_disc_miss == 0 and n_disc > 0,
        "z_bottom_mm": DISC_TOP_Z,
        "disc_miss_sample": disc_miss_sample,
        "eq": "free: r_dot=0, th_dot=omega, z=DISC_TOP_Z; contact: r:=r_wall+clear",
        "entered_lane": entered_lane,
        "blocked_by": blocked_by,
        "trapped": True,
        "path": path,
    }


def _sanity_case_wh(D: float, T: float) -> tuple[float, float]:
    """W,H vận hành: từ 2 mm đến (kích thước vật + 1 mm), kẹp [2, 26]."""
    w = _clamp(float(D) + PILL_CLEAR_XY, W_MIN, W_MAX)
    h = _clamp(float(T) + PILL_CLEAR_Z, H_MIN, H_MAX)
    return round(w, 3), round(h, 3)


def make_sanity_100_cases(n: int = SANITY_N, seed: int = SANITY_SEED) -> list[dict]:
    rng = random.Random(seed)
    cases: list[dict] = []
    sizes = [
        (2.0, 2.0, "ball"),
        (3.0, 2.0, "tablet"),
        (4.0, 4.0, "ball"),
        (5.0, 2.5, "tablet"),
        (6.0, 3.0, "tablet"),
        (8.0, 4.0, "tablet"),
        (9.0, 9.0, "ball"),
        (10.0, 5.0, "tablet"),
        (12.0, 6.0, "tablet"),
        (15.0, 7.0, "tablet"),
        (18.0, 8.0, "tablet"),
        (20.0, 10.0, "tablet"),
        (22.0, 12.0, "tablet"),
        (24.0, 8.0, "tablet"),
        (25.0, 25.0, "ball"),
    ]

    def _add(D, T, shape, r, th, pose, tag):
        W, H = _sanity_case_wh(D, T)
        half = 0.5 * (T if pose == "stand" and shape != "ball" else D)
        r_lo = 0.5 * HUB_D + half + 2.0
        r_hi = CHANNEL_R_OUTER - half - 1.0
        rr = float(_clamp(r, r_lo, r_hi))
        cases.append(
            {
                "id": f"s{len(cases):03d}_{tag}",
                "D": round(float(D), 3),
                "T": round(float(T), 3),
                "shape": shape,
                "W": W,
                "H": H,
                "W_range": [W_MIN, round(float(D) + PILL_CLEAR_XY, 3)],
                "H_range": [H_MIN, round(float(T) + PILL_CLEAR_Z, 3)],
                "r0": round(rr, 3),
                "th0": round(float(th) % 360.0, 3),
                "pose0": "flat" if shape == "ball" else pose,
            }
        )

    # 30: lưới r × θ, size xoay vòng — phủ đĩa + nhiều vòng
    for i in range(30):
        D, T, shape = sizes[i % len(sizes)]
        pose = "stand" if shape == "tablet" and (i % 3 == 1) else "flat"
        half = 0.5 * (T if pose == "stand" else D)
        r_lo = 0.5 * HUB_D + half + 2.0
        r_hi = CHANNEL_R_OUTER - half - 1.0
        u = (i % 5) / 4.0
        r = r_lo + u * (r_hi - r_lo)
        th = (i * 37.0) % 360.0
        _add(D, T, shape, r, th, pose, "grid")

    # 20: sát hub — phải đi nhiều vòng theo xoắn
    for i in range(20):
        D, T, shape = sizes[(i + 3) % len(sizes)]
        pose = "flat" if shape == "ball" or i % 2 == 0 else "stand"
        half = 0.5 * (T if pose == "stand" and shape != "ball" else D)
        r = 0.5 * HUB_D + half + 3.0 + (i % 4)
        th = (i * 18.0 + 11.0) % 360.0
        _add(D, T, shape, r, th, pose, "hub")

    # 50: ngẫu nhiên (seed cố định)
    while len(cases) < n:
        if rng.random() < 0.35:
            s = rng.uniform(2.0, 25.0)
            D = T = s
            shape = "ball"
        else:
            D = rng.uniform(2.0, 25.0)
            T = rng.uniform(2.0, max(2.0, D))
            shape = "tablet"
        pose = "flat" if shape == "ball" or rng.random() < 0.55 else "stand"
        half = 0.5 * (T if pose == "stand" and shape != "ball" else D)
        r_lo = 0.5 * HUB_D + half + 2.0
        r_hi = CHANNEL_R_OUTER - half - 1.0
        r = rng.uniform(r_lo, r_hi)
        th = rng.uniform(0.0, 360.0)
        _add(D, T, shape, r, th, pose, "rnd")
    return cases[:n]


def simulate_rest_in_lane(
    D: float,
    T: float,
    W: float,
    H: float,
    th0: float,
    r0: float | None = None,
    omega: float = OMEGA_DISC,
    dt: float = 0.002,
    t_max: float | None = None,
) -> dict:
    """
    Vật đứng yên trong máng xếp hàng (v=0 thế giới). Đĩa quay → ma sát μ_disc*mg
    tăng v_θ tới no-slip; cửa ra F_dọc = μ_disc*mg*(sinβ − μ_wall cosβ) > 0.
    """
    W = _clamp(W, WIDTH_MIN, WIDTH_MAX)
    H = _clamp(H, HEIGHT_MIN, HEIGHT_MAX)
    r_i = CHANNEL_R_OUTER - W
    r = float(r0 if r0 is not None else 0.5 * (r_i + CHANNEL_R_OUTER))
    half = 0.5 * D
    r = _clamp(r, r_i + half + 0.2, CHANNEL_R_OUTER - half - 0.2)
    th_unw = float(th0)
    v = 0.0
    g_mm = 9810.0
    ep = exit_tangent_pose(W, H)
    ux, uy = ep["chute_dir"]
    ax, ay = ep["anchor_xy"]
    drive_net = float(ep["drive_net_friction"])
    in_chute = th_unw >= THETA_EXIT_DEG - 0.2
    s_chute = 0.0
    t = 0.0
    n_slip = n_stick = 0
    r_end = r
    th_end = th_unw % 360.0
    span = max(15.0, THETA_EXIT_DEG - th_unw + 25.0)
    if t_max is None:
        t_max = math.radians(span) / max(omega, 1e-6) + 3.0
    while t < t_max:
        if in_chute:
            a = MU_DISC * g_mm * max(0.0, drive_net)
            v += a * dt
            s_chute += max(0.0, v) * dt
            px = ax + s_chute * ux
            py = ay + s_chute * uy
            r_end = math.hypot(px, py)
            th_end = (math.degrees(math.atan2(py, px)) + 360.0) % 360.0
            if r_end > DISC_R + 0.2:
                t_stick = (omega * r) / max(MU_DISC * g_mm, 1e-9)
                return {
                    "exited": True,
                    "t_s": round(t + dt, 4),
                    "s_chute_mm": round(s_chute, 2),
                    "r_end": round(r_end, 2),
                    "th_end": round(th_end, 2),
                    "n_slip_steps": n_slip,
                    "n_stick_steps": n_stick,
                    "v_exit_mm_s": round(v, 2),
                    "drive_net": drive_net,
                    "t_stick_s": round(t_stick, 4),
                    "omega": omega,
                    "started_at_rest": True,
                    "th0": th0,
                    "r0": round(r, 2),
                    "eq": "rest: a=mu_disc*g; chute a=mu_disc*g*(sinβ-mu_wall*cosβ)",
                }
        else:
            v_disc = omega * r
            slip = v_disc - v
            if abs(slip) > 2.0:
                v += math.copysign(MU_DISC * g_mm * dt, slip)
                if (v - v_disc) * slip < 0.0:
                    v = v_disc
                n_slip += 1
            else:
                v = v_disc
                n_stick += 1
            th_unw += math.degrees((v / max(r, 1.0)) * dt)
            th_end = th_unw % 360.0
            r_end = r
            if th_unw >= THETA_EXIT_DEG:
                in_chute = True
                th_e = _deg2rad(THETA_EXIT_DEG)
                etx, ety = -math.sin(th_e), math.cos(th_e)
                v = max(0.0, v * (etx * ux + ety * uy))
                s_chute = 0.0
        t += dt
    return {
        "exited": False,
        "t_s": round(t_max, 4),
        "s_chute_mm": round(s_chute, 2),
        "r_end": round(r_end, 2),
        "th_end": round(th_end, 2),
        "n_slip_steps": n_slip,
        "n_stick_steps": n_stick,
        "drive_net": drive_net,
        "started_at_rest": True,
        "th0": th0,
        "r0": round(r, 2),
        "trapped": True,
    }


def _shape_min_dist_mm(a: Part.Shape, b: Part.Shape) -> float:
    if not _shape_ok(a, 0.05) or not _shape_ok(b, 0.05):
        return 99.0
    try:
        d, _p, _i = a.distToShape(b)
        return float(d)
    except Exception:
        ov = _overlap_volume(a, b)
        return 0.0 if ov > 1e-4 else 99.0


def make_exit_arc_outer():
    return _box(0.1, 0.1, 0.1, 0, 0, 0)


def width_carriage_x_local(w):
    return W_MAX - _clamp(w, W_MIN, W_MAX)


def height_carriage_z(h):
    return height_scraper_z(h)


# `from mech_common import *` mac dinh BO QUA moi ten bat dau bang "_" (quy uoc
# private cua Python) — nhieu helper hinh hoc dung chung o day (_box, _cyl_z,
# _refine, _cyl_axis, _deg2rad, _clamp, ...) can duoc cac module part_*.py va
# tube_l_exit_gate.py wildcard-import duoc, nen export TAT CA ten module-level
# (ke ca "_"), tru cac dunder (__name__, __file__, ...).
__all__ = [_n for _n in dir() if not _n.startswith("__")]


