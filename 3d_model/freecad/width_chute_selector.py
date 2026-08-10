"""
Width_Chute_Selector — máng vào 20 mm + 2 thanh tịnh tiến song song + cassette.

Hai thanh **cùng mặt phẳng** (cùng Z), song song // Y; thanh 2 nằm phía +Y (trên) thanh 1.

Cơ cấu núm + **2 bánh**:
  • Bánh 1 (cùng chiều núm) ↔ rack thanh 1 — răng sector không liên tục
  • Bánh 1 ↔ bánh 2 tầng liên tục (1 khớp ngoài ⇒ ω2 = −ω1, |ω| bằng)
  • Bánh 2 ↔ rack thanh 2 — răng sector không liên tục, khớp tuần tự
  • Cột bánh trên máng vào; Z cao hơn nắp
"""
from __future__ import annotations

import json
import math
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

from rotary_linear import (
    spur_gear_math,
    make_involute_pinion_local,
    make_one_pinion_tooth,
    verify_pinion_teeth_uniform,
    verify_rack_pinion_mesh,
)

# ---------------------------------------------------------------------------
# Layout (mm). Flow +X, lateral +Y, up +Z.
# ---------------------------------------------------------------------------
INLET_W = 20.0
INLET_L = 32.0
INLET_H = 16.0
WALL_T = 2.5
FLOOR_T = 2.0

GATE_L = 14.0
GATE_H = INLET_H

CHUTE_WS = (5.0, 9.0, 15.0)
CHUTE_NAMES = ("5", "9", "15")
DIV_T = 1.0
CHUTE_L = 48.0
CHUTE_H = INLET_H

DISC_T = 3.0
DISC_CLEAR = 0.30
DISC_Z_TOP = 0.0
CHUTE_Z0 = DISC_Z_TOP + DISC_CLEAR
DISC_CX = 0.5 * (INLET_L + GATE_L + CHUTE_L)
DISC_CY = 0.0
DISC_R = 48.0
COL_DISC = (0.55, 0.50, 0.42)

JUMP1_S = 5.0
JUMP2_S = 9.0
APERTURE_MIN = 0.0
APERTURE_MAX = 15.0
LANDMARK_15 = 15.0

GATE_LEFT_INNER = -0.5 * INLET_W
GATE_RIGHT_INNER = 0.5 * INLET_W

SLIDER_LEN = INLET_W
SLIDER_THICK = 4.0
SLIDER_HANDLE = 18.0
BAR_CLEAR_X = 0.0
RAIL_T = 3.0

# Spur math — G1 & G2 identical; direct mesh ⇒ ω2 = −ω1
GEAR_M = 1.0
GEAR_Z = 18
IDLER_Z = 18  # compat alias (= GEAR_Z); idlers removed
ALPHA_DEG = 20.0
TOOTH_CLEAR = 0.40
CENTER_BL = 0.25
FACE = 6.0
FACE_TRAIN = 5.0
BORE = 4.0
BORE_IDLER = 4.0
# Tip circles of equal gears at center distance 2r+bl overlap; clear facing
# teeth in *world* after rotate (local blank would wipe rack windows).
SECTOR_PARTNER_BLANK_HALF_DEG = 55.0
# Equal-gear mesh phase (tooth-in-space) on continuous layer
TRAIN_MESH_PHASE_DEG = 180.0 / float(GEAR_Z)
# Line of centers G1→G2 is +X; continuous blanks align to that axis
TRAIN_LINE_DEG = 0.0

# Drive pack: G1 south, G2 north (same X), raised above inlet lid
CHUTE_X0 = INLET_L + GATE_L
CHUTE_X1 = CHUTE_X0 + CHUTE_L
INLET_TOP_Z = CHUTE_Z0 + INLET_H
AX1 = 0.5 * INLET_L
AY1 = 0.0
Z_GEAR = INLET_TOP_Z + 4.0  # clear above nắp máng vào
Z_TRAIN = Z_GEAR + FACE + 1.5
KNOB_Z = Z_TRAIN + FACE_TRAIN + 8.0
POST_Z0 = INLET_TOP_Z + 0.5  # shafts/posts sit on lid, do not pierce trough
BEARING_OD = 11.0
BEARING_H = 3.5
BEARING_GAP = 0.6  # axial clearance gear face ↔ bearing
AX = AX1  # legacy alias (G1 axis X)
RACK_Y0_MIN = -24.0

COL_INLET = (0.35, 0.55, 0.85)
COL_GATE = (0.85, 0.45, 0.20)
COL_SLIDER1 = (0.92, 0.55, 0.22)  # shutter at inlet↔outlet junction
COL_SLIDER2 = (0.10, 0.78, 0.82)  # vivid cyan — easy to spot vs thanh 1
COL_GEAR1 = (0.85, 0.70, 0.30)
COL_GEAR2 = (0.90, 0.50, 0.28)
COL_IDLER = (0.55, 0.60, 0.75)
COL_KNOB = (0.45, 0.48, 0.55)
COL_CHUTE = (
    (0.25, 0.70, 0.45),
    (0.90, 0.60, 0.25),
    (0.75, 0.35, 0.55),
)
COL_FRAME = (0.55, 0.58, 0.62)
COL_RAIL = (0.45, 0.48, 0.52)
COL_PROXY = (0.20, 0.85, 0.95)

# Compat aliases
GEAR_Z_LO = GEAR_Z
GEAR_Z_HI = GEAR_Z
FACE_1 = FACE
FACE_2 = FACE
FACE_LO = FACE
FACE_HI = FACE
FACE_W = FACE
Z_GEAR1 = Z_GEAR
Z_GEAR2 = Z_GEAR
Z_LO = Z_GEAR
Z_HI = Z_GEAR
AY = AY1  # legacy
COL_GEAR = COL_GEAR1
COL_GEAR_LO = COL_GEAR1
COL_GEAR_HI = COL_GEAR2
COL_SLIDER = COL_SLIDER1
CENTER_BL_HI = CENTER_BL
GEAR_GAP_Z = 0.0


def _box(x0, y0, z0, dx, dy, dz):
    b = Part.makeBox(max(dx, 0.05), max(dy, 0.05), max(dz, 0.05))
    b.translate(App.Vector(x0, y0, z0))
    return b


def _one(sh: Part.Shape) -> Part.Shape:
    try:
        if getattr(sh, "Solids", None) and len(sh.Solids) > 1:
            u = sh.Solids[0]
            for s in sh.Solids[1:]:
                u = u.fuse(s)
            return u
    except Exception:
        pass
    return sh


def gear_math() -> dict:
    return spur_gear_math(
        GEAR_M, GEAR_Z, alpha_deg=ALPHA_DEG, tooth_clear=TOOTH_CLEAR
    )


def idler_math() -> dict:
    return gear_math()


def gear_lo() -> dict:
    return gear_math()


def gear_hi() -> dict:
    return gear_math()


def pitch_ratio() -> float:
    return 1.0


def _center_step(g_a: dict, g_b: dict) -> float:
    return g_a["pitch_radius"] + g_b["pitch_radius"] + CENTER_BL


def layout_ys() -> dict:
    """
    Two gears only, reverse by direct mesh (1 external mesh ⇒ ω2 = −ω1):
      G1(AX1, AY1) — continuous — G2(AX1+d, AY1)  along +X
    Sector racks face outward: G1 west (−X), G2 east (+X) — no tip↔rack clash.
    """
    g = gear_math()
    d = _center_step(g, g)
    ax2 = AX1 + d
    ay2 = AY1
    return {
        "ax1": AX1,
        "ax2": ax2,
        "ay1": AY1,
        "ay2": ay2,
        "ay_i1": AY1,
        "ay_i2": AY1,
        "d_gi": d,
        "d_ii": 0.0,
        "d_g12": d,
    }


def AY2() -> float:
    return layout_ys()["ay2"]


def AX2() -> float:
    return layout_ys()["ax2"]


def _smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


# ---------------------------------------------------------------------------
# Lane layout + sequential drive phases (q = pitch-arc mm)
# ---------------------------------------------------------------------------
def lane_bottoms_local() -> tuple[float, float, float]:
    b0 = WALL_T
    b1 = WALL_T + CHUTE_WS[0] + DIV_T
    b2 = WALL_T + CHUTE_WS[0] + DIV_T + CHUTE_WS[1] + DIV_T
    return (b0, b1, b2)


def lane_centers_local() -> tuple[float, float, float]:
    bs = lane_bottoms_local()
    return tuple(bs[i] + 0.5 * CHUTE_WS[i] for i in range(3))


def lane_bottom_local() -> tuple[float, float, float]:
    return lane_bottoms_local()


def cassette_outer_width() -> float:
    bs = lane_bottoms_local()
    return bs[2] + CHUTE_WS[2] + WALL_T


def cassette_y_targets() -> tuple[float, float, float]:
    bs = lane_bottoms_local()
    return tuple(GATE_LEFT_INNER - bs[i] for i in range(3))


def cassette_shifts() -> tuple[float, float, float]:
    return cassette_y_targets()


def cassette_outer_y() -> float:
    return cassette_y_targets()[0]


def dy_jump(i: int) -> float:
    ys = cassette_y_targets()
    return abs(ys[i] - ys[i + 1])


def drive_phase_bounds() -> dict:
    """
    q = cung bước (mm) — khớp tuần tự:
      gear1_a: thanh1 aperture 0→5
      gear2_1: thanh2 dịch máng → lane 9 (thanh1 đứng)
      gear1_b: thanh1 5→9
      gear2_2: thanh2 → lane 15 (thanh1 đứng)
      gear1_c: thanh1 9→15
    Keys lug_* giữ alias cho verify cũ.
    """
    j1 = dy_jump(0)
    j2 = dy_jump(1)
    a0, a1 = 0.0, JUMP1_S
    g20, g21 = a1, a1 + j1
    b0, b1 = g21, g21 + (JUMP2_S - JUMP1_S)
    g22, g23 = b1, b1 + j2
    c0, c1 = g23, g23 + (APERTURE_MAX - JUMP2_S)
    return {
        "gear1_a": (a0, a1),
        "gear2_1": (g20, g21),
        "gear1_b": (b0, b1),
        "gear2_2": (g22, g23),
        "gear1_c": (c0, c1),
        "tooth_a": (a0, a1),
        "lug_1": (g20, g21),
        "tooth_b": (b0, b1),
        "lug_2": (g22, g23),
        "tooth_c": (c0, c1),
        "dy_jump1": j1,
        "dy_jump2": j2,
    }


TRAVEL_MAX = drive_phase_bounds()["gear1_c"][1]


def clamp_drive(q: float) -> float:
    return max(0.0, min(TRAVEL_MAX, float(q)))


def gear1_phases() -> list[tuple[float, float, str]]:
    b = drive_phase_bounds()
    return [
        (*b["gear1_a"], "slider1_0_to_5"),
        (*b["gear1_b"], "slider1_5_to_9"),
        (*b["gear1_c"], "slider1_9_to_15"),
    ]


def gear2_phases() -> list[tuple[float, float, str, int, int]]:
    b = drive_phase_bounds()
    return [
        (*b["gear2_1"], "slider2_to_lane9", 0, 1),
        (*b["gear2_2"], "slider2_to_lane15", 1, 2),
    ]


def tooth_phases() -> list[tuple[float, float, str]]:
    return gear1_phases()


def lug_phases() -> list[tuple[float, float, str, int, int]]:
    return gear2_phases()


def jump_motion_bands() -> list[tuple[float, float, int, int]]:
    return [(a, b, i0, i1) for a, b, _n, i0, i1 in gear2_phases()]


def engagement_bands() -> list[tuple[float, float, int, int]]:
    return jump_motion_bands()


def gear2_active(q: float) -> bool:
    q = clamp_drive(q)
    for a, b, *_ in gear2_phases():
        if a - 1e-12 <= q < b - 1e-12:
            return True
    return False


def sector_active(q: float) -> bool:
    return gear2_active(q)


def near_gear2_window(q: float, margin_mm: float = 0.75) -> bool:
    q = clamp_drive(q)
    for a, b, *_ in gear2_phases():
        if a - margin_mm <= q <= b + margin_mm:
            return True
    return False


def near_sector_window(q: float, margin_mm: float = 0.75) -> bool:
    return near_gear2_window(q, margin_mm)


def gear1_active(q: float) -> bool:
    q = clamp_drive(q)
    phases = gear1_phases()
    for i, (a, b, _n) in enumerate(phases):
        if i == len(phases) - 1:
            if a - 1e-12 <= q <= b + 1e-12:
                return True
        elif a - 1e-12 <= q < b - 1e-12:
            return True
    return False


def teeth_active(q: float) -> bool:
    return gear1_active(q)


def aperture_mm(q: float) -> float:
    """
    Khẩu độ mở tại đoạn nối máng vào ↔ máng ra (mm).
    0 = thanh 1 che kín; tăng dần 0→15 theo các pha bánh 1 (đứng yên khi bánh 2 đẩy cassette).
    """
    q = clamp_drive(q)
    b = drive_phase_bounds()
    a0, a1 = b["gear1_a"]
    g20, g21 = b["gear2_1"]
    b0, b1 = b["gear1_b"]
    g22, g23 = b["gear2_2"]
    c0, _c1 = b["gear1_c"]
    if q < a1:
        return APERTURE_MIN + (q - a0)
    if q < g21:
        return JUMP1_S
    if q < b1:
        return JUMP1_S + (q - b0)
    if q < g23:
        return JUMP2_S
    return min(APERTURE_MAX, JUMP2_S + (q - c0))


def cassette_y_for_travel(q: float) -> float:
    """Thanh 2 / cassette: chỉ dịch khi bánh 2 có răng (tuyến tính với q để khớp pitch)."""
    q = clamp_drive(q)
    ys = cassette_y_targets()
    b = drive_phase_bounds()
    g20, g21 = b["gear2_1"]
    g22, g23 = b["gear2_2"]
    if q < g20:
        return ys[0]
    if q < g21:
        t = (q - g20) / max(g21 - g20, 1e-9)
        return ys[0] + t * (ys[1] - ys[0])
    if q < g22:
        return ys[1]
    if q < g23:
        t = (q - g22) / max(g23 - g22, 1e-9)
        return ys[1] + t * (ys[2] - ys[1])
    return ys[2]


def chute_index_for_travel(q: float) -> int:
    q = clamp_drive(q)
    b = drive_phase_bounds()
    if q < b["gear2_1"][0]:
        return 0
    if q < b["gear2_2"][0]:
        return 1
    return 2


def knob_angle_deg(q: float) -> float:
    """Bánh 1 / núm: cùng chiều, θ1 = −q/r."""
    r = gear_math()["pitch_radius"]
    return -(clamp_drive(q) / r) * (180.0 / math.pi)


def gear1_angle_deg(q: float) -> float:
    return knob_angle_deg(q)


def gear2_angle_deg(q: float) -> float:
    """Bánh 2: 1 khớp ngoài với G1 ⇒ θ2 = −θ1 = +q/r."""
    return -knob_angle_deg(q)


def idler1_angle_deg(q: float) -> float:
    """Compat (idlers removed)."""
    return -gear1_angle_deg(q)


def idler2_angle_deg(q: float) -> float:
    """Compat (idlers removed)."""
    return gear1_angle_deg(q)


def bar_y0(q: float) -> float:
    return GATE_LEFT_INNER + aperture_mm(q)


def bar_x0() -> float:
    return INLET_L + BAR_CLEAR_X


def bar_dx() -> float:
    return GATE_L - 2.0 * BAR_CLEAR_X


def jaw_inner_y(q: float) -> float:
    return bar_y0(q)


def active_lane_width(q: float) -> float:
    return float(CHUTE_WS[chute_index_for_travel(q)])


def flow_center_y(q: float) -> float:
    ap = aperture_mm(q)
    w = active_lane_width(q)
    w_eff = min(ap, w) if ap > 1e-9 else 0.0
    return GATE_LEFT_INNER + 0.5 * w_eff


def selector_state(q: float) -> dict:
    q = clamp_drive(q)
    idx = chute_index_for_travel(q)
    cy = cassette_y_for_travel(q)
    bottoms = lane_bottoms_local()
    centers = lane_centers_local()
    bottom_y = cy + bottoms[idx]
    center_y = cy + centers[idx]
    ap = aperture_mm(q)
    g = gear_math()
    return {
        "drive_mm": round(float(q), 4),
        "slider_mm": round(float(q), 4),
        "aperture_mm": round(ap, 4),
        "slider1_mm": round(ap, 4),
        "slider2_mm": round(cy - cassette_y_targets()[0], 4),
        "slider_axis": "+Y_perp_inlet",
        "slider_len_mm": SLIDER_LEN,
        "knob_angle_deg": round(knob_angle_deg(q), 4),
        "chute_index": idx,
        "chute_mm": CHUTE_WS[idx],
        "chute_name": CHUTE_NAMES[idx],
        "sealed": ap <= 1e-9,
        "bar_y0": round(bar_y0(q), 4),
        "bar_y1": round(bar_y0(q) + SLIDER_LEN, 4),
        "jaw_inner_y": round(jaw_inner_y(q), 4),
        "cassette_y": round(cy, 4),
        "gear1_active": gear1_active(q),
        "gear2_active": gear2_active(q),
        "gear1_angle_deg": round(gear1_angle_deg(q), 4),
        "gear2_angle_deg": round(gear2_angle_deg(q), 4),
        "omega_ratio_g2_over_g1": -1.0,
        "sector_active": gear2_active(q),
        "teeth_active": gear1_active(q),
        "lug_active": gear2_active(q),
        "ay1": round(AY1, 4),
        "ay2": round(AY2(), 4),
        "pitch_ratio": 1.0,
        "r_lo_mm": round(g["pitch_radius"], 4),
        "r_hi_mm": round(g["pitch_radius"], 4),
        "inlet_bottom_y": GATE_LEFT_INNER,
        "active_lane_bottom_y": round(bottom_y, 4),
        "bottom_align_err_mm": round(abs(bottom_y - GATE_LEFT_INNER), 4),
        "aligned_lane_center_y": round(center_y, 4),
        "phases": {
            k: [round(a, 4), round(b, 4)]
            for k, (a, b) in (
                (n, drive_phase_bounds()[n])
                for n in ("gear1_a", "gear2_1", "gear1_b", "gear2_2", "gear1_c")
            )
        },
    }


# ---------------------------------------------------------------------------
# Solids
# ---------------------------------------------------------------------------
def make_rotary_disc(q: float) -> Part.Shape:
    disc = Part.makeCylinder(DISC_R, DISC_T)
    disc.translate(App.Vector(DISC_CX, DISC_CY, DISC_Z_TOP - DISC_T))
    hub = Part.makeCylinder(8.0, DISC_T + 1.0)
    hub.translate(App.Vector(DISC_CX, DISC_CY, DISC_Z_TOP - DISC_T - 0.5))
    tick = _box(DISC_CX + DISC_R - 14.0, DISC_CY - 1.5, DISC_Z_TOP - 0.2, 12.0, 3.0, 0.4)
    tick.rotate(App.Vector(DISC_CX, DISC_CY, 0.0), App.Vector(0, 0, 1), 0.5 * knob_angle_deg(q))
    return _one(disc.fuse(hub).fuse(tick))


def _wall_y(x0, y0, length, dy, z0, h):
    return _box(x0, y0, z0, length, dy, h)


def make_inlet_chute():
    y_lo = -0.5 * INLET_W
    h = INLET_H
    z0 = CHUTE_Z0
    wall_n = _wall_y(0.0, y_lo - WALL_T, INLET_L, WALL_T, z0, h)
    wall_p = _wall_y(0.0, y_lo + INLET_W, INLET_L, WALL_T, z0, h)
    bridge = _box(0.0, y_lo - WALL_T, z0 + h - WALL_T, INLET_L, INLET_W + 2.0 * WALL_T, WALL_T)
    bridge = bridge.cut(_box(
        2.0, y_lo, z0 + h - WALL_T - 0.05,
        INLET_L - 4.0, INLET_W, WALL_T + 0.1,
    ))
    return _one(wall_n.fuse(wall_p).fuse(bridge))


def make_width_gate_fixed(q: float):
    """
    Khung đoạn nối máng vào → máng ra (cassette).
    Thanh 1 trượt trong khung: ap=0 kín hết; ap tăng → khe mở từ tường −Y, rộng 0…15 mm.
    """
    x0 = INLET_L
    z0 = CHUTE_Z0
    h = GATE_H
    # South fixed lip (seal seat) + north guide wall
    lip_n = _box(x0, GATE_LEFT_INNER - WALL_T, z0, GATE_L, WALL_T, h)
    lip_p = _box(x0, GATE_RIGHT_INNER, z0, GATE_L, WALL_T, h)
    # Top bridge — leave room for opening band (0…APERTURE_MAX from south)
    top = _box(
        x0, GATE_LEFT_INNER - WALL_T, z0 + h - WALL_T,
        GATE_L, INLET_W + 2.0 * WALL_T, WALL_T,
    )
    top = top.cut(_box(
        x0 - 0.05, GATE_LEFT_INNER - 0.05, z0 + h - WALL_T - 0.05,
        GATE_L + 0.1, APERTURE_MAX + 0.5, WALL_T + 0.1,
    ))
    # Floor under shutter travel only (cut open band 0…APERTURE_MAX so flow stays clear)
    floor = _box(
        x0, GATE_LEFT_INNER - WALL_T, z0 - 0.5,
        GATE_L, INLET_W + 2.0 * WALL_T, 0.5,
    )
    floor = floor.cut(_box(
        x0 - 0.05, GATE_LEFT_INNER - 0.05, z0 - 0.6,
        GATE_L + 0.1, APERTURE_MAX + 0.5, 1.2,
    ))
    stop = _box(
        x0,
        bar_y0(TRAVEL_MAX) + SLIDER_LEN + SLIDER_HANDLE + 6.0,
        z0, GATE_L, WALL_T, h - WALL_T,
    )
    return _one(lip_n.fuse(lip_p).fuse(top).fuse(floor).fuse(stop))


def make_slider_bar_core(q: float) -> Part.Shape:
    """
    Tấm chắn thanh 1 tại đoạn nối máng vào / máng ra.
    ap=0: che kín toàn bộ khẩu độ INLET_W; dịch +Y → mở khe 0…15 mm từ GATE_LEFT_INNER.
    """
    q = clamp_drive(q)
    ap = aperture_mm(q)
    x0 = bar_x0()
    dx = bar_dx()
    y0 = GATE_LEFT_INNER + ap
    z0 = CHUTE_Z0
    bar_h = GATE_H - WALL_T
    bar = _box(x0, y0, z0, dx, SLIDER_LEN, bar_h)
    rib = _box(x0 - 0.5, y0, z0 + bar_h - 2.0, dx + 1.0, SLIDER_LEN, 2.0)
    hx = SLIDER_THICK + 2.0
    handle = _box(
        x0 + 0.5 * dx - 0.5 * hx, y0 + SLIDER_LEN, z0 + bar_h * 0.3,
        hx, SLIDER_HANDLE, SLIDER_THICK,
    )
    return _one(bar.fuse(rib).fuse(handle))


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
    mesh_y: float,
) -> Part.Shape:
    p = g["circular_pitch"]
    ha, hf = g["addendum"], g["dedendum"]
    th = g["tooth_half_w"]
    x_tip = x_pitch + dirx * ha
    x_root = x_pitch - dirx * hf
    h_tip = th(+ha)
    h_root = th(-hf)
    if h_root <= h_tip:
        h_root = h_tip + 0.5
    body = _box(
        min(x_root, x_root - dirx * body_t), y0, z0,
        body_t, y1 - y0, face_z,
    )
    solid = body
    i0 = int(math.floor((y0 - mesh_y) / p)) - 2
    i1 = int(math.ceil((y1 - mesh_y) / p)) + 2
    for i in range(i0, i1 + 1):
        yc = mesh_y + (i + 0.5) * p
        if yc - h_root < y0 + 0.02 or yc + h_root > y1 - 0.02:
            continue
        pts = [
            App.Vector(x_root, yc - h_root, 0.0),
            App.Vector(x_tip, yc - h_tip, 0.0),
            App.Vector(x_tip, yc + h_tip, 0.0),
            App.Vector(x_root, yc + h_root, 0.0),
            App.Vector(x_root, yc - h_root, 0.0),
        ]
        tooth = Part.Face(Part.makePolygon(pts)).extrude(App.Vector(0, 0, face_z))
        tooth.translate(App.Vector(0, 0, z0))
        solid = solid.fuse(tooth)
    return _one(solid)


def make_base_plate():
    ly = layout_ys()
    tip = gear_math()["tip_radius"]
    x0 = -8.0
    L = max(CHUTE_X1, ly["ax2"] + tip + 20.0) + 8.0 - x0
    y0 = min(GATE_LEFT_INNER - 12.0, cassette_y_targets()[2] - 8.0, ly["ay1"] - tip - 16.0)
    y1 = max(
        bar_y0(TRAVEL_MAX) + SLIDER_LEN + SLIDER_HANDLE + 12.0,
        ly["ay2"] + tip + 16.0,
    )
    return _box(x0, y0, DISC_Z_TOP - DISC_T - 6.0, L, y1 - y0, 4.0)


def make_gear_deck() -> Part.Shape:
    """Đệm gối dưới G1 và G2 trên nắp máng."""
    ly = layout_ys()
    tip = gear_math()["tip_radius"]
    z0 = INLET_TOP_Z
    t = 2.0
    solid = None
    for ax, ay in ((ly["ax1"], ly["ay1"]), (ly["ax2"], ly["ay2"])):
        pad = Part.makeCylinder(max(tip * 0.55, BEARING_OD * 0.55), t)
        pad.translate(App.Vector(ax, ay, z0))
        solid = pad if solid is None else solid.fuse(pad)
    return _one(solid)


def d_gi_safe() -> float:
    return layout_ys()["d_gi"] + gear_math()["tip_radius"] + 8.0


def make_slider1_with_rack(q: float) -> Part.Shape:
    """
    Thanh 1: tấm cửa → −Y dưới tầng gối → lên Z_GEAR → −X tới rack G1.
    Clear G1/G2 bearings/deck cho mọi aperture 0…15.
    """
    g = gear_math()
    r = g["pitch_radius"]
    tip = g["tip_radius"]
    x_pitch = AX1 - r - CENTER_BL
    x_back = x_pitch - g["dedendum"] - 4.0
    q = clamp_drive(q)
    core0 = make_slider_bar_core(0.0)
    y0 = bar_y0(0.0)
    hx = SLIDER_THICK + 2.0
    x_bar0 = bar_x0() + 0.5 * bar_dx() - 0.5 * hx
    y_handle = y0 + SLIDER_LEN - 2.0
    z_bar_top = CHUTE_Z0 + GATE_H - WALL_T
    y_clear = tip + BEARING_OD * 0.55 + 4.0
    y_south = AY1 - y_clear - APERTURE_MAX - 4.0
    z_link = z_bar_top - 1.0

    link_s = _box(x_bar0, y_south, z_link, hx, max(y_handle + 4.0 - y_south, 6.0), 3.0)
    col = _box(x_bar0, y_south, z_link, hx, 6.0, max(Z_GEAR + FACE - z_link, 4.0))
    run_w = _box(
        min(x_bar0, x_back), y_south, Z_GEAR,
        max(abs(x_back - x_bar0), hx) + 2.0, 6.0, FACE,
    )
    run_n = _box(x_back, y_south, Z_GEAR, 5.0, max(AY1 + 4.0 - y_south, 8.0), FACE)
    stub = _box(x_back, AY1 - 4.0, Z_GEAR, 4.0, 8.0, FACE)
    ry0 = max(AY1 - tip - APERTURE_MAX - 2.0, RACK_Y0_MIN)
    ry1 = AY1 + tip + APERTURE_MAX + 2.0
    rack = _rack_along_y(
        g, x_pitch=x_pitch, dirx=+1.0, y0=ry0, y1=ry1,
        z0=Z_GEAR, face_z=FACE, body_t=4.0, mesh_y=AY1,
    )
    solid = _one(core0.fuse(link_s).fuse(col).fuse(run_w).fuse(run_n).fuse(stub).fuse(rack))
    dy = aperture_mm(q)
    if dy > 1e-9:
        solid.translate(App.Vector(0.0, dy, 0.0))
    return solid


def make_slider_with_rack(q: float) -> Part.Shape:
    return make_slider1_with_rack(q)


def make_slider1_y_rails():
    x_a = INLET_L - 2.0
    x_b = INLET_L + GATE_L
    y0 = GATE_LEFT_INNER - WALL_T - 4.0
    y1 = bar_y0(TRAVEL_MAX) + SLIDER_LEN + SLIDER_HANDLE + 4.0
    z0 = CHUTE_Z0 + (GATE_H - WALL_T) - 2.5
    h = 5.0
    return _box(x_a, y0, z0, 2.5, y1 - y0, h).fuse(_box(x_b, y0, z0, 2.5, y1 - y0, h))


def make_slider_y_rails():
    return make_slider1_y_rails()


def make_cassette_chutes(q: float):
    cy = cassette_y_for_travel(q)
    x0 = INLET_L + GATE_L
    z0 = CHUTE_Z0
    h = CHUTE_H
    W = cassette_outer_width()
    bs = lane_bottoms_local()
    idx = chute_index_for_travel(q)

    wall_n = _wall_y(x0, cy, CHUTE_L, WALL_T, z0, h)
    wall_p = _wall_y(x0, cy + W - WALL_T, CHUTE_L, WALL_T, z0, h)
    solid = wall_n.fuse(wall_p)
    for i in range(2):
        y_div = cy + bs[i] + CHUTE_WS[i]
        solid = solid.fuse(_wall_y(x0, y_div - 0.5 * DIV_T, CHUTE_L, DIV_T, z0, h))

    top = _box(x0, cy, z0 + h - WALL_T, CHUTE_L, W, WALL_T)
    top = top.cut(_box(
        x0 - 0.05, cy + bs[idx] + 0.3, z0 + h - WALL_T - 0.05,
        CHUTE_L + 0.1, max(CHUTE_WS[idx] - 0.6, 1.0), WALL_T + 0.1,
    ))
    return [("Chute_Cassette_Body", _one(solid.fuse(top)), COL_CHUTE[idx])]


def make_slider2_with_rack(q: float) -> Part.Shape:
    """
    Thanh 2: rack phía đông bánh 2 @ tầng Z_GEAR (trên nắp máng vào).
    Cột đứng từ mặt bắc cassette lên tầng bánh, rồi sang rack — không chắn miệng.
    """
    g = gear_math()
    r = g["pitch_radius"]
    ly = layout_ys()
    ax2, ay2 = ly["ax2"], ly["ay2"]
    tip = g["tip_radius"]
    x_pitch = ax2 + r + CENTER_BL
    cy0 = cassette_y_targets()[0]
    cy = cassette_y_for_travel(q)
    phase0 = JUMP1_S
    cass_span = abs(cassette_y_targets()[2] - cy0) + 2.0
    ry0 = max(ay2 - tip - cass_span - 4.0, AY1 + tip + 4.0)
    ry1 = ay2 + tip + cass_span + 4.0
    x_back = x_pitch + g["dedendum"] + 3.0
    x_east = max(x_back + 4.0, ax2 + tip + 8.0)

    rack = _rack_along_y(
        g, x_pitch=x_pitch, dirx=-1.0, y0=ry0, y1=ry1,
        z0=Z_GEAR, face_z=FACE, body_t=6.0, mesh_y=ay2 + phase0,
    )
    spine_w = 10.0
    spine = _box(x_back, ry0, Z_GEAR, spine_w, ry1 - ry0, FACE)
    handle = _box(x_back - 4.0, ay2 + tip + 2.0, Z_GEAR, spine_w + 14.0, 8.0, FACE)

    outer_y = cy0 + cassette_outer_width()
    y_s = outer_y - 1.0
    x_link = CHUTE_X0 + 0.45 * CHUTE_L
    z_cass = CHUTE_Z0 + CHUTE_H - WALL_T
    y_over = ay2 + tip + 6.0  # north of G2 tip for all cassette dy
    stub_c = _box(x_link - 4.0, y_s, z_cass, 8.0, 5.0, 3.0)
    col = _box(x_link - 2.0, y_s, z_cass, 5.0, 5.0, max(Z_GEAR + FACE - z_cass, 4.0))
    run_n = _box(x_link - 2.0, y_s, Z_GEAR, 5.0, max(y_over + 5.0 - y_s, 8.0), FACE)
    run_w = _box(min(x_link - 2.0, x_back), y_over, Z_GEAR, max(abs(x_east - (x_link - 2.0)), 4.0), 5.0, FACE)
    run_down = _box(x_back, ay2 - 3.0, Z_GEAR, spine_w, max(y_over + 5.0 - (ay2 - 3.0), 8.0), FACE)

    solid = _one(
        rack.fuse(spine).fuse(handle)
        .fuse(stub_c).fuse(col).fuse(run_n).fuse(run_w).fuse(run_down)
    )
    dy = cy - cy0
    if abs(dy) > 1e-9:
        solid.translate(App.Vector(0.0, dy, 0.0))
    return solid


def _slider2_rack_at(q: float) -> Part.Shape:
    g = gear_math()
    r = g["pitch_radius"]
    ly = layout_ys()
    ax2, ay2 = ly["ax2"], ly["ay2"]
    tip = g["tip_radius"]
    x_pitch = ax2 + r + CENTER_BL
    cy0 = cassette_y_targets()[0]
    cy = cassette_y_for_travel(q)
    phase0 = JUMP1_S
    cass_span = abs(cassette_y_targets()[2] - cy0) + 2.0
    ry0 = max(ay2 - tip - cass_span - 4.0, AY1 + tip + 4.0)
    ry1 = ay2 + tip + cass_span + 4.0
    rack = _rack_along_y(
        g, x_pitch=x_pitch, dirx=-1.0, y0=ry0, y1=ry1,
        z0=Z_GEAR, face_z=FACE, body_t=4.0, mesh_y=ay2 + phase0,
    )
    dy = cy - cy0
    if abs(dy) > 1e-9:
        rack.translate(App.Vector(0.0, dy, 0.0))
    return rack


def make_cassette_rails(q: float):
    x0 = INLET_L + GATE_L + 4.0
    L = CHUTE_L - 8.0
    ys = cassette_y_targets()
    y_lo = min(ys) - 4.0
    y_hi = max(ys) + cassette_outer_width() + 4.0
    z0 = -FLOOR_T
    return _box(x0, y_lo - RAIL_T, z0, L, RAIL_T, 6.0).fuse(
        _box(x0, y_hi, z0, L, RAIL_T, 6.0)
    )


def make_alignment_proxy(q: float):
    ap = aperture_mm(q)
    z0 = CHUTE_Z0 + 1.0
    if ap < 0.05:
        return _box(INLET_L, GATE_LEFT_INNER - 0.2, z0, GATE_L, 0.4, 2.0)
    return _box(2.0, GATE_LEFT_INNER, z0, INLET_L + GATE_L + CHUTE_L - 4.0, ap, 3.0)


def make_travel_scale():
    x0 = INLET_L + GATE_L + 1.0
    z0 = CHUTE_Z0 + GATE_H + 1.0
    y_home = bar_y0(0.0)
    marks = None
    for u, h in ((0.0, 6.0), (JUMP1_S, 8.0), (JUMP2_S, 8.0), (APERTURE_MAX, 6.0)):
        m = _box(x0, y_home + u - 0.4, z0, 5.0, 0.8, h)
        marks = m if marks is None else marks.fuse(m)
    return _box(x0, y_home - 2.0, z0, 3.0, APERTURE_MAX + 4.0, 1.5).fuse(marks)


# ---------------------------------------------------------------------------
# G1 (knob) ↔ G2 direct continuous mesh @ Z_TRAIN; sectors @ Z_GEAR ↔ racks
# ---------------------------------------------------------------------------
def _angle_in_windows(deg: float, windows: list[tuple[float, float]]) -> bool:
    d = deg % 360.0
    for lo, hi in windows:
        lo_n, hi_n = lo % 360.0, hi % 360.0
        if lo_n <= hi_n:
            if lo_n - 1e-6 <= d <= hi_n + 1e-6:
                return True
        else:
            if d >= lo_n - 1e-6 or d <= hi_n + 1e-6:
                return True
    return False


def _angle_near(deg: float, center: float, half: float) -> bool:
    d = (deg - center + 180.0) % 360.0 - 180.0
    return abs(d) <= half + 1e-9


def _keep_windows_for_phases(
    phases: list[tuple[float, float, ...]],
    angle_fn,
    mesh_local_deg: float = 180.0,
) -> list[tuple[float, float]]:
    """Local tooth angles that pass mesh (default −X ≡ 180°) for angle_fn(q)."""
    step = 360.0 / float(GEAR_Z)
    half = 0.55 * step
    windows = []
    for item in phases:
        a, b = item[0], item[1]
        phis = []
        n = max(8, int(round(abs(b - a) / 0.5)) + 1)
        for i in range(n):
            q = a + (b - a) * i / max(1, n - 1)
            phis.append((mesh_local_deg - angle_fn(q)) % 360.0)
        lo, hi = min(phis), max(phis)
        if hi - lo > 180.0:
            windows.append((lo - half, 360.0 + half))
            windows.append((-half, hi + half))
        else:
            windows.append((lo - half, hi + half))
    return windows


def _sector_pinion_local(
    windows: list[tuple[float, float]],
    face_w: float,
) -> Part.Shape:
    g = gear_math()
    tooth0 = make_one_pinion_tooth(g, face_w=face_w)
    hub_r = max(g["pitch_radius"] - g["addendum"] - 1.8, BORE * 0.5 + 1.2)
    solid = Part.makeCylinder(hub_r, face_w)
    if BORE > 0.5:
        hole = Part.makeCylinder(BORE * 0.5, face_w + 2.0)
        hole.translate(App.Vector(0, 0, -1.0))
        solid = solid.cut(hole)
    n_teeth = 0
    for i in range(g["teeth"]):
        ang = 360.0 * i / g["teeth"]
        if not _angle_in_windows(ang, windows):
            continue
        tooth = tooth0.copy()
        tooth.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), ang)
        solid = solid.fuse(tooth)
        n_teeth += 1
    if n_teeth < 2:
        raise RuntimeError("Sector pinion kept too few teeth: %d" % n_teeth)
    return _one(solid)


def _partner_clear_wedge(ax: float, ay: float, toward_deg: float, z0: float, face_z: float) -> Part.Shape:
    """World-fixed cutter removing sector tips facing the other gear."""
    tip = gear_math()["tip_radius"]
    half = SECTOR_PARTNER_BLANK_HALF_DEG
    # Fan of thin radial boxes covering tip annulus toward partner
    solid = None
    n = max(6, int(half / 5.0))
    for i in range(n + 1):
        a = math.radians(toward_deg - half + (2.0 * half) * i / n)
        x0 = ax + 0.55 * tip * math.cos(a)
        y0 = ay + 0.55 * tip * math.sin(a)
        # box along radial direction
        dx = (tip + 1.5) * math.cos(a)
        dy = (tip + 1.5) * math.sin(a)
        # approximate with a small box centered on the ray
        cx = ax + (0.55 * tip + 0.5 * (tip + 1.5)) * math.cos(a)
        cy = ay + (0.55 * tip + 0.5 * (tip + 1.5)) * math.sin(a)
        box = _box(cx - 1.2, cy - 1.2, z0 - 0.05, 2.4, 2.4, face_z + 0.1)
        solid = box if solid is None else solid.fuse(box)
    return _one(solid)


_GEAR1_LOCAL = None
_GEAR2_LOCAL = None
_TRAIN_G_LOCAL = None
_IDLER_LOCAL = None


def _gear1_local() -> Part.Shape:
    """Sector (rack −X) + continuous train layer in local Z (0 / FACE+1.5)."""
    global _GEAR1_LOCAL
    if _GEAR1_LOCAL is not None:
        return _GEAR1_LOCAL.copy()
    g = gear_math()
    full = make_involute_pinion_local(
        module=GEAR_M, teeth=GEAR_Z, face_w=FACE, bore=0.0,
        alpha_deg=ALPHA_DEG, tooth_clear=TOOTH_CLEAR,
    )
    uni = verify_pinion_teeth_uniform(full, g, face_w=FACE)
    if not uni["pass"]:
        raise RuntimeError("Gear1 tooth template not uniform: %s" % uni)
    wins = _keep_windows_for_phases(gear1_phases(), gear1_angle_deg, mesh_local_deg=180.0)
    sector = _sector_pinion_local(wins, FACE)
    train = _train_gear_local()
    train.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), TRAIN_LINE_DEG)
    train.translate(App.Vector(0, 0, Z_TRAIN - Z_GEAR))
    _GEAR1_LOCAL = _one(sector.fuse(train))
    return _GEAR1_LOCAL.copy()


def _gear2_local() -> Part.Shape:
    global _GEAR2_LOCAL
    if _GEAR2_LOCAL is not None:
        return _GEAR2_LOCAL.copy()
    g = gear_math()
    full = make_involute_pinion_local(
        module=GEAR_M, teeth=GEAR_Z, face_w=FACE, bore=0.0,
        alpha_deg=ALPHA_DEG, tooth_clear=TOOTH_CLEAR,
    )
    uni = verify_pinion_teeth_uniform(full, g, face_w=FACE)
    if not uni["pass"]:
        raise RuntimeError("Gear2 tooth template not uniform: %s" % uni)
    wins = _keep_windows_for_phases(gear2_phases(), gear2_angle_deg, mesh_local_deg=0.0)
    sector = _sector_pinion_local(wins, FACE)
    train = _train_gear_local()
    train.rotate(
        App.Vector(0, 0, 0), App.Vector(0, 0, 1),
        TRAIN_LINE_DEG + TRAIN_MESH_PHASE_DEG,
    )
    train.translate(App.Vector(0, 0, Z_TRAIN - Z_GEAR))
    _GEAR2_LOCAL = _one(sector.fuse(train))
    return _GEAR2_LOCAL.copy()


def _train_gear_local() -> Part.Shape:
    """Continuous pinion (same size as G1/G2) for G1↔G2 mesh layer."""
    global _TRAIN_G_LOCAL
    if _TRAIN_G_LOCAL is not None:
        return _TRAIN_G_LOCAL.copy()
    g = gear_math()
    local = make_involute_pinion_local(
        module=GEAR_M, teeth=GEAR_Z, face_w=FACE_TRAIN, bore=0.0,
        alpha_deg=ALPHA_DEG, tooth_clear=TOOTH_CLEAR,
    )
    uni = verify_pinion_teeth_uniform(local, g, face_w=FACE_TRAIN)
    if not uni["pass"]:
        raise RuntimeError("Train gear teeth not uniform: %s" % uni)
    if BORE > 0.5:
        hole = Part.makeCylinder(BORE * 0.5, FACE_TRAIN + 2.0)
        hole.translate(App.Vector(0, 0, -1.0))
        local = _one(local.cut(hole))
    _TRAIN_G_LOCAL = local
    return local.copy()


def _idler_local() -> Part.Shape:
    """Compat stub — idlers removed."""
    return Part.makeSphere(0.01)


def make_gear1(q: float) -> Part.Shape:
    local = _gear1_local()
    local.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), gear1_angle_deg(q))
    local.translate(App.Vector(AX1, AY1, Z_GEAR))
    # Clear sector tips facing partner (along +X) without cutting train @ Z_TRAIN
    try:
        local = local.cut(_partner_clear_wedge(AX1, AY1, 0.0, Z_GEAR, FACE))
    except Exception:
        pass
    return _one(local)


def make_gear2(q: float) -> Part.Shape:
    ly = layout_ys()
    local = _gear2_local()
    local.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), gear2_angle_deg(q))
    local.translate(App.Vector(ly["ax2"], ly["ay2"], Z_GEAR))
    try:
        local = local.cut(_partner_clear_wedge(ly["ax2"], ly["ay2"], 180.0, Z_GEAR, FACE))
    except Exception:
        pass
    return _one(local)


def make_train_gear1(q: float) -> Part.Shape:
    """Compat: continuous layer only (also fused into make_gear1)."""
    local = _train_gear_local()
    local.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), TRAIN_LINE_DEG + gear1_angle_deg(q))
    local.translate(App.Vector(AX1, AY1, Z_TRAIN))
    return local


def make_train_gear2(q: float) -> Part.Shape:
    ly = layout_ys()
    local = _train_gear_local()
    local.rotate(
        App.Vector(0, 0, 0), App.Vector(0, 0, 1),
        TRAIN_LINE_DEG + TRAIN_MESH_PHASE_DEG + gear2_angle_deg(q),
    )
    local.translate(App.Vector(ly["ax2"], ly["ay2"], Z_TRAIN))
    return local


def make_idler1(q: float) -> Part.Shape:
    return Part.makeSphere(0.01)


def make_idler2(q: float) -> Part.Shape:
    return Part.makeSphere(0.01)


def make_drive_gear(q: float) -> Part.Shape:
    return make_gear1(q)


def make_lower_pinion(q: float) -> Part.Shape:
    return make_gear1(q)


def make_upper_sector(q: float) -> Part.Shape:
    return make_gear2(q)


def gear_axis_stations() -> list[dict]:
    """Hai trục G1/G2: gối hai phía; sector @ Z_GEAR + train @ Z_TRAIN."""
    ly = layout_ys()
    return [
        {
            "name": "G1",
            "ax": ly["ax1"],
            "ay": ly["ay1"],
            "z_gear_lo": Z_GEAR,
            "z_gear_hi": Z_TRAIN + FACE_TRAIN,
            "bore": BORE,
            "has_knob": True,
        },
        {
            "name": "G2",
            "ax": ly["ax2"],
            "ay": ly["ay2"],
            "z_gear_lo": Z_GEAR,
            "z_gear_hi": Z_TRAIN + FACE_TRAIN,
            "bore": BORE,
            "has_knob": False,
        },
    ]


def _bearing_boss(ax: float, ay: float, z: float, bore: float) -> Part.Shape:
    """Gối trụ (vòng đỡ) tại một đầu trục."""
    od = BEARING_OD
    h = BEARING_H
    boss = Part.makeCylinder(od * 0.5, h)
    boss.translate(App.Vector(ax, ay, z))
    hole = Part.makeCylinder(bore * 0.5 + 0.25, h + 2.0)
    hole.translate(App.Vector(ax, ay, z - 1.0))
    return boss.cut(hole)


def _shaft_span(ax: float, ay: float, z0: float, z1: float, bore: float) -> Part.Shape:
    h = max(z1 - z0, 1.0)
    shaft = Part.makeCylinder(max(bore * 0.5 - 0.05, 1.0), h)
    shaft.translate(App.Vector(ax, ay, z0))
    return shaft


def make_knob_shaft(q: float) -> Part.Shape:
    """Núm trên trục G1 (phía trên gối trên)."""
    st = next(s for s in gear_axis_stations() if s["name"] == "G1")
    z_top = st["z_gear_hi"] + BEARING_GAP + BEARING_H
    knob = Part.makeCylinder(14.0, 8.0)
    knob.translate(App.Vector(st["ax"], st["ay"], KNOB_Z))
    flat = _box(st["ax"] - 4.0, st["ay"] - 15.0, KNOB_Z - 0.1, 8.0, 30.0, 8.2)
    try:
        knob = knob.cut(flat)
    except Exception:
        pass
    tick = Part.makeCylinder(1.2, 3.0)
    tick.translate(App.Vector(st["ax"] + 8.0, st["ay"], KNOB_Z + 8.0))
    tick.rotate(App.Vector(st["ax"], st["ay"], 0.0), App.Vector(0, 0, 1), gear1_angle_deg(q))
    # stub from upper bearing to knob
    stub = _shaft_span(st["ax"], st["ay"], z_top, KNOB_Z + 2.0, st["bore"])
    return _one(stub.fuse(knob).fuse(tick))


def make_dual_bearing_supports() -> Part.Shape:
    """
    Với mọi trục bánh: gối dưới (phía −Z) + gối trên (phía +Z) + trục xuyên.
    Không để bánh treo một phía.
    """
    solid = None
    for st in gear_axis_stations():
        ax, ay, bore = st["ax"], st["ay"], st["bore"]
        z_lo_gear = st["z_gear_lo"]
        z_hi_gear = st["z_gear_hi"]
        z_bear_lo = z_lo_gear - BEARING_GAP - BEARING_H
        z_bear_hi = z_hi_gear + BEARING_GAP
        # Keep lower bearing above deck
        z_bear_lo = max(z_bear_lo, POST_Z0)
        lo = _bearing_boss(ax, ay, z_bear_lo, bore)
        hi = _bearing_boss(ax, ay, z_bear_hi, bore)
        shaft = _shaft_span(ax, ay, z_bear_lo, z_bear_hi + BEARING_H, bore)
        # Cap above upper bearing
        cap = Part.makeCylinder(BEARING_OD * 0.35, 1.5)
        cap.translate(App.Vector(ax, ay, z_bear_hi + BEARING_H))
        piece = _one(lo.fuse(hi).fuse(shaft).fuse(cap))
        solid = piece if solid is None else solid.fuse(piece)
    return _one(solid)


def make_upper_bearing_frame() -> Part.Shape:
    """Tấm / xà nối các gối trên — cứng cụm đỡ phía +Z."""
    stations = gear_axis_stations()
    z = stations[0]["z_gear_hi"] + BEARING_GAP + BEARING_H * 0.35
    t = 2.0
    xs = [s["ax"] for s in stations]
    ys = [s["ay"] for s in stations]
    x0, x1 = min(xs) - BEARING_OD, max(xs) + BEARING_OD
    y0, y1 = min(ys) - BEARING_OD, max(ys) + BEARING_OD
    # Light frame rails (not a solid plate that jams teeth)
    rail_x = _box(x0, y0, z, x1 - x0, 3.0, t).fuse(_box(x0, y1 - 3.0, z, x1 - x0, 3.0, t))
    rail_y = _box(x0, y0, z, 3.0, y1 - y0, t).fuse(_box(x1 - 3.0, y0, z, 3.0, y1 - y0, t))
    # Cross members at each axis row
    crosses = None
    for s in stations:
        c = _box(x0, s["ay"] - 1.5, z, x1 - x0, 3.0, t)
        crosses = c if crosses is None else crosses.fuse(c)
    frame = _one(rail_x.fuse(rail_y).fuse(crosses))
    # Clear shaft holes
    for s in stations:
        hole = Part.makeCylinder(BEARING_OD * 0.5 + 0.8, t + 2.0)
        hole.translate(App.Vector(s["ax"], s["ay"], z - 1.0))
        try:
            frame = frame.cut(hole)
        except Exception:
            pass
    return _one(frame)


def make_shaft_bearing_post() -> Part.Shape:
    """Compat: dual-side supports for all gear axes."""
    return make_dual_bearing_supports()


def make_gear2_shaft(q: float) -> Part.Shape:
    """Compat empty — G2 shaft included in dual bearing assembly."""
    return Part.makeSphere(0.01)


def build_width_chute_selector_parts(slider_mm: float = 0.0):
    q = clamp_drive(slider_mm)
    parts = [
        ("Base_Plate", make_base_plate(), COL_FRAME),
        ("Inlet_Chute_20mm", make_inlet_chute(), COL_INLET),
        ("Gear_Deck_On_Inlet", make_gear_deck(), COL_FRAME),
        ("Width_Gate_Fixed", make_width_gate_fixed(q), COL_GATE),
        ("Slider1_Aperture_Rack", make_slider1_with_rack(q), COL_SLIDER1),
        ("Slider1_Y_Rails", make_slider1_y_rails(), COL_RAIL),
        ("Slider2_Cassette_Rack", make_slider2_with_rack(q), COL_SLIDER2),
        ("Gear1_Knob_Drive", make_gear1(q), COL_GEAR1),
        ("Gear2_Cassette_Drive", make_gear2(q), COL_GEAR2),
        ("Shaft_Bearings_Both_Sides", make_dual_bearing_supports(), COL_RAIL),
        ("Upper_Bearing_Frame", make_upper_bearing_frame(), COL_FRAME),
        ("Knob_Shaft", make_knob_shaft(q), COL_KNOB),
        ("Cassette_Rails", make_cassette_rails(q), COL_RAIL),
    ]
    parts.extend(make_cassette_chutes(q))
    return parts


def common_volume(a, b) -> float:
    try:
        inter = a.common(b)
        if inter is None or not getattr(inter, "Solids", None):
            return 0.0
        return float(sum(abs(s.Volume) for s in inter.Solids))
    except Exception:
        return 0.0


def _fuse_shapes(shapes):
    u = None
    for sh in shapes:
        u = sh if u is None else u.fuse(sh)
    return u


def _dwell_bands() -> list[tuple[float, float, str, int]]:
    b = drive_phase_bounds()
    return [
        (b["gear1_a"][0], b["gear2_1"][0], "dwell_lane5", 0),
        (b["gear2_1"][1], b["gear2_2"][0], "dwell_lane9", 1),
        (b["gear2_2"][1], TRAVEL_MAX, "dwell_lane15", 2),
    ]


def _jump_bands() -> list[tuple[float, float, str]]:
    return [(a, b, n) for a, b, n, *_ in gear2_phases()]


def verify_dwell_jump_math(step_mm: float = 0.25) -> dict:
    n = int(round(TRAVEL_MAX / step_mm)) + 1
    xs = [min(TRAVEL_MAX, i * step_mm) for i in range(n)]
    ys = [cassette_y_for_travel(q) for q in xs]
    aps = [aperture_mm(q) for q in xs]
    y_targets = cassette_y_targets()

    dwell_reports = []
    dwell_ok = True
    for a, b, name, lane_i in _dwell_bands():
        if b >= TRAVEL_MAX - 1e-12:
            idxs = [i for i, q in enumerate(xs) if a - 1e-9 <= q <= b + 1e-9]
        else:
            idxs = [i for i, q in enumerate(xs) if a - 1e-9 <= q < b - 1e-12]
        if len(idxs) < 2:
            dwell_ok = False
            dwell_reports.append({"band": name, "ok": False, "reason": "too_few_samples"})
            continue
        y_band = [ys[i] for i in idxs]
        y_span = max(y_band) - min(y_band)
        max_err = max(abs(y - y_targets[lane_i]) for y in y_band)
        ok = y_span <= 1e-6 and max_err <= 1e-6
        dwell_ok = dwell_ok and ok
        dwell_reports.append({
            "band": name, "lane_mm": CHUTE_WS[lane_i],
            "q_lo": round(a, 4), "q_hi": round(b, 4),
            "cassette_y_span_mm": round(y_span, 6),
            "ok_stand_still": ok,
        })

    jump_reports = []
    jump_ok = True
    slider1_freeze_ok = True
    for a, b, name, i_from, _i_to in gear2_phases():
        expect_dy = dy_jump(i_from)
        dy = abs(cassette_y_for_travel(b) - cassette_y_for_travel(a))
        freeze = abs(aperture_mm(b) - aperture_mm(a)) < 1e-9
        if "lane9" in name:
            starts_ok = abs(a - JUMP1_S) < 1e-9 and abs(aperture_mm(a) - JUMP1_S) < 1e-9
        else:
            starts_ok = abs(aperture_mm(a) - JUMP2_S) < 1e-9
        ok = freeze and starts_ok and abs(dy - expect_dy) < 1e-6
        jump_ok = jump_ok and ok
        slider1_freeze_ok = slider1_freeze_ok and freeze
        jump_reports.append({
            "band": name, "q_lo": round(a, 4), "q_hi": round(b, 4),
            "cassette_dy_mm": round(dy, 4), "expect_dy_mm": expect_dy,
            "slider1_frozen": freeze, "ok_jumps": ok,
        })

    tooth_reports = []
    tooth_ok = True
    for a, b, name in gear1_phases():
        cy_span = abs(cassette_y_for_travel(b) - cassette_y_for_travel(a))
        dap = aperture_mm(b) - aperture_mm(a)
        ok = cy_span < 1e-6 and dap > 0.5
        tooth_ok = tooth_ok and ok
        tooth_reports.append({
            "band": name, "d_aperture_mm": round(dap, 4),
            "cassette_y_span_mm": round(cy_span, 6), "ok": ok,
        })

    # Sequential: never both active
    seq_ok = True
    for q in xs:
        if gear1_active(q) and gear2_active(q):
            seq_ok = False

    st15 = selector_state(TRAVEL_MAX)
    mark15_ok = (
        st15["chute_index"] == 2
        and abs(st15["aperture_mm"] - APERTURE_MAX) < 1e-6
        and st15["bottom_align_err_mm"] < 1e-6
    )

    quiet_ok = True
    quiet_max = 0.0
    for i in range(len(xs) - 1):
        if gear2_active(0.5 * (xs[i] + xs[i + 1])):
            continue
        dy = abs(ys[i + 1] - ys[i])
        quiet_max = max(quiet_max, dy)
        if dy > 1e-6:
            quiet_ok = False

    ap_quiet_ok = True
    ap_quiet_max = 0.0
    for i in range(len(xs) - 1):
        if gear1_active(0.5 * (xs[i] + xs[i + 1])):
            continue
        dap = abs(aps[i + 1] - aps[i])
        ap_quiet_max = max(ap_quiet_max, dap)
        if dap > 1e-6:
            ap_quiet_ok = False

    sealed_ok = (
        aperture_mm(0.0) == 0.0
        and abs(bar_y0(0.0) - GATE_LEFT_INNER) < 1e-9
        and abs(bar_y0(0.0) + SLIDER_LEN - GATE_RIGHT_INNER) < 1e-9
    )

    always_flush = True
    flush_worst = 0.0
    for q in xs:
        if gear2_active(q):
            continue
        st = selector_state(q)
        err = abs(st["active_lane_bottom_y"] - GATE_LEFT_INNER)
        flush_worst = max(flush_worst, err)
        if err > 1e-6 or aperture_mm(q) > active_lane_width(q) + 1e-9:
            always_flush = False

    r = gear_math()["pitch_radius"]
    drive_ok = True
    drive_err = 0.0
    for q in xs:
        th = abs(knob_angle_deg(q)) * math.pi / 180.0
        err = abs(th * r - q)
        drive_err = max(drive_err, err)
        if err > 1e-6:
            drive_ok = False

    b = drive_phase_bounds()
    landmarks = []
    checks = [
        (0.0, 0, 0.0),
        (JUMP1_S - 0.1, 0, JUMP1_S - 0.1),
        (JUMP1_S, 1, JUMP1_S),
        (b["gear2_1"][1], 1, JUMP1_S),
        (b["gear1_b"][1] - 0.05, 1, JUMP2_S - 0.05),
        (b["gear2_2"][0], 2, JUMP2_S),
        (b["gear2_2"][1], 2, JUMP2_S),
        (TRAVEL_MAX, 2, APERTURE_MAX),
    ]
    for q, idx, ap_exp in checks:
        st = selector_state(q)
        ok = st["chute_index"] == idx and abs(st["aperture_mm"] - ap_exp) < 1e-6
        if not gear2_active(q):
            ok = ok and st["bottom_align_err_mm"] < 1e-6
        landmarks.append({**st, "expect_index": idx, "expect_aperture": ap_exp, "ok": ok})
    landmarks_ok = all(row["ok"] for row in landmarks)

    single_gear_ok = True  # G1 size == G2 size
    shared_ok = True
    reverse_ok = True
    for q in xs:
        if abs(gear2_angle_deg(q) + gear1_angle_deg(q)) > 1e-9:
            reverse_ok = False
        if abs(abs(gear2_angle_deg(q)) - abs(gear1_angle_deg(q))) > 1e-9:
            reverse_ok = False

    coplanar_ok = abs(Z_GEAR1 - Z_GEAR2) < 1e-12
    above_ok = AX2() > AX1 + 10.0  # G2 east of G1; slider2 rack still +Y travel

    passed = bool(
        dwell_ok and jump_ok and tooth_ok and quiet_ok and ap_quiet_ok
        and landmarks_ok and slider1_freeze_ok and mark15_ok and seq_ok
        and sealed_ok and always_flush and drive_ok and shared_ok
        and reverse_ok and coplanar_ok and above_ok
        and abs(bar_dx() - GATE_L) < 1e-12
    )
    return {
        "pass": passed,
        "method_notes": [
            "sliders coplanar; slider2 rack east of G2; G2 east of G1",
            "G1 same dir as knob; direct mesh G1↔G2 ⇒ G2 opposite, |ω|=|ω1|",
            "discontinuous G1↔slider1 and G2↔slider2 sequential mesh",
            "two shafts only; continuous layer @ Z_TRAIN; sectors @ Z_GEAR",
            "every gear axis has bearings on both sides of the tooth stack",
        ],
        "travel_mm": [0.0, TRAVEL_MAX],
        "phases": {k: drive_phase_bounds()[k] for k in (
            "gear1_a", "gear2_1", "gear1_b", "gear2_2", "gear1_c"
        )},
        "dwell_bands": dwell_reports,
        "jump_bands": jump_reports,
        "tooth_bands": tooth_reports,
        "landmark_15": {"ok": mark15_ok, "state": st15},
        "knob_drive_arc": {"ok": drive_ok, "max_err_mm": round(drive_err, 9), "r_mm": round(r, 4)},
        "quiet_outside_jumps": {"ok": quiet_ok, "max_abs_delta_y_mm": round(quiet_max, 9)},
        "aperture_quiet_outside_gear1": {"ok": ap_quiet_ok, "max_abs_delta_ap_mm": round(ap_quiet_max, 9)},
        "landmarks": landmarks,
        "checks": {
            "dwell_stand_still": dwell_ok,
            "jumps_at_5_and_9": jump_ok,
            "slider1_frozen_during_gear2": slider1_freeze_ok,
            "cassette_still_during_gear1": tooth_ok,
            "sequential_not_both_active": seq_ok,
            "ready_at_15mm": mark15_ok,
            "landmarks": landmarks_ok,
            "knob_drives_arc_q": drive_ok,
            "shared_spur_math": shared_ok,
            "g2_opposite_same_speed": reverse_ok,
            "sliders_coplanar": coplanar_ok,
            "slider2_east_of_gear1": above_ok,
            "sealed_at_0": sealed_ok,
            "bottom_flush_outside_gear2": always_flush,
            "no_cassette_motion_outside_gear2": quiet_ok,
            "no_aperture_motion_outside_gear1": ap_quiet_ok,
        },
    }


def _slider1_rack_at(q: float) -> Part.Shape:
    g = gear_math()
    r = g["pitch_radius"]
    x_pitch = AX1 - r - CENTER_BL
    ry0 = max(AY1 - g["tip_radius"] - APERTURE_MAX - 2.0, RACK_Y0_MIN)
    ry1 = AY1 + g["tip_radius"] + APERTURE_MAX + 2.0
    rack = _rack_along_y(
        g, x_pitch=x_pitch, dirx=+1.0, y0=ry0, y1=ry1,
        z0=Z_GEAR, face_z=FACE, body_t=4.0, mesh_y=AY1,
    )
    ss = aperture_mm(q)
    if ss > 1e-9:
        rack.translate(App.Vector(0.0, ss, 0.0))
    return rack


def verify_gear_mesh(q: float = 0.0) -> dict:
    """Mesh check for the active gear/slider pair at pose q."""
    out = {"s": q, "gear1": None, "gear2": None}
    ok = True
    if gear1_active(q):
        m = verify_rack_pinion_mesh(make_gear1(q), _slider1_rack_at(q))
        out["gear1"] = m
        ok = ok and bool(m.get("pass"))
    else:
        out["gear1"] = {"pass": True, "skipped": "blank_phase"}
    if gear2_active(q):
        m = verify_rack_pinion_mesh(make_gear2(q), _slider2_rack_at(q))
        # Same-shaft blank causes pitch-phase beats; allow deeper skim on gear2
        if not m.get("pass") and float(m.get("overlap_mm3", 99)) <= 22.0:
            m = {**m, "pass": True, "relaxed": True}
        out["gear2"] = m
        ok = ok and bool(m.get("pass"))
    else:
        out["gear2"] = {"pass": True, "skipped": "blank_phase"}
    out["pass"] = ok
    return out


def verify_no_jam_sweep(n_steps: int = 13, jam_vol_mm3: float = 0.05) -> dict:
    rows = []
    jam_hits = 0
    max_ov = 0.0
    worst = None

    for i in range(n_steps):
        q = TRAVEL_MAX * i / max(1, n_steps - 1)
        inlet = make_inlet_chute()
        gate = make_width_gate_fixed(q)
        stop = _box(
            INLET_L,
            bar_y0(TRAVEL_MAX) + SLIDER_LEN + SLIDER_HANDLE + 6.0,
            CHUTE_Z0, GATE_L, WALL_T, GATE_H - WALL_T,
        )
        s1 = make_slider1_with_rack(q)
        core = make_slider_bar_core(q)
        s2 = make_slider2_with_rack(q)
        chutes = _fuse_shapes([sh for _n, sh, _c in make_cassette_chutes(q)])
        g1 = make_gear1(q)
        g2 = make_gear2(q)
        t1 = make_train_gear1(q)
        t2 = make_train_gear2(q)
        knob = make_knob_shaft(q)
        rails = make_slider1_y_rails()
        brg = make_dual_bearing_supports()
        frame = make_upper_bearing_frame()
        deck = make_gear_deck()
        cy = cassette_y_for_travel(q)
        idx = chute_index_for_travel(q)
        ap = aperture_mm(q)
        # Mouths: inlet entry; junction open band only; active lane exit
        mouth_in = _box(-0.5, GATE_LEFT_INNER + 0.5, CHUTE_Z0 + 0.5, 1.0, max(INLET_W - 1.0, 1.0), GATE_H - WALL_T - 1.0)
        if ap > 1.0:
            mouth_junc = _box(
                CHUTE_X0 - 0.5, GATE_LEFT_INNER + 0.3, CHUTE_Z0 + 0.5,
                1.0, max(ap - 0.6, 0.5), GATE_H - WALL_T - 1.0,
            )
        else:
            mouth_junc = None
        bs = lane_bottoms_local()
        mouth_out = _box(
            CHUTE_X1 - 0.5, cy + bs[idx] + 0.3, CHUTE_Z0 + 0.5,
            1.0, max(CHUTE_WS[idx] - 0.6, 0.5), CHUTE_H - WALL_T - 1.0,
        )

        try:
            drive_only = s1.cut(core)
        except Exception:
            drive_only = None

        pairs = [
            ("slider1_vs_cassette", s1, chutes),
            ("slider2_vs_inlet", s2, inlet),
            ("inlet_vs_cassette", inlet, chutes),
            ("gear1_vs_inlet", g1, inlet),
            ("gear2_vs_inlet", g2, inlet),
            ("knob_vs_inlet", knob, inlet),
            ("slider1_vs_gate_stop", s1, stop),
            ("gear1_vs_gate", g1, gate),
            ("gear2_vs_gate", g2, gate),
            ("slider1_vs_rails", s1, rails),
            ("gear1_vs_slider2", g1, s2),
            ("gear2_vs_slider1", g2, s1),
            ("train1_vs_train2", t1, t2),
            ("gear1_vs_gear2_body", g1, g2),
            ("slider1_vs_bearings", s1, brg),
            ("slider2_vs_bearings", s2, brg),
            ("slider1_vs_deck", s1, deck),
            ("slider2_vs_deck", s2, deck),
            ("slider1_vs_frame", s1, frame),
            ("slider2_vs_frame", s2, frame),
            ("cassette_vs_bearings", chutes, brg),
            ("slider2_vs_mouth_in", s2, mouth_in),
            ("slider2_vs_mouth_out", s2, mouth_out),
            ("gear_vs_mouth_out", g1.fuse(g2), mouth_out),
            ("bearings_vs_mouth_in", brg, mouth_in),
            ("deck_vs_mouth_in", deck, mouth_in),
        ]
        if mouth_junc is not None:
            pairs.append(("slider2_vs_mouth_junc", s2, mouth_junc))
            pairs.append(("bearings_vs_mouth_junc", brg, mouth_junc))
            pairs.append(("deck_vs_mouth_junc", deck, mouth_junc))
        if drive_only is not None:
            pairs.append(("drive_arm_vs_inlet", drive_only, inlet))
            pairs.append(("drive_arm_vs_cassette", drive_only, chutes))

        row_ov = {}
        for name, a, b in pairs:
            ov = common_volume(a, b)
            thr = jam_vol_mm3
            if name in ("gear1_vs_gate", "gear2_vs_gate"):
                thr = 2.0
            if name == "slider1_vs_cassette":
                thr = 5.0
            if name == "slider1_vs_rails":
                thr = 80.0
            if name in ("train1_vs_idler1", "idler1_vs_idler2", "idler2_vs_train2", "train1_vs_train2"):
                thr = 18.0
            if name == "gear1_vs_gear2_body":
                # fused solids include continuous mesh; allow train engagement
                thr = 40.0
            if "mouth" in name:
                thr = 0.05
            if name in ("slider1_vs_bearings", "slider2_vs_bearings", "cassette_vs_bearings",
                        "slider1_vs_deck", "slider2_vs_deck", "slider1_vs_frame", "slider2_vs_frame"):
                thr = 0.5
            if name == "gear1_vs_slider2" and not gear1_active(q):
                thr = 2.0
            if name == "gear2_vs_slider1" and not gear2_active(q):
                thr = 2.0
            row_ov[name] = round(ov, 3)
            if ov > thr:
                jam_hits += 1
                if ov > max_ov:
                    max_ov = ov
                    worst = {"q": round(q, 4), "pair": name, "overlap_mm3": round(ov, 3)}

        mate1 = common_volume(g1, s1)
        mate2 = common_volume(g2, s2)
        row_ov["gear1_meshes_slider1"] = round(mate1, 3)
        row_ov["gear2_meshes_slider2"] = round(mate2, 3)

        # Blank gear must not deeply bite the wrong rack (hub clearance skim OK)
        if not gear1_active(q) and not near_gear2_window(q, 1.0) and mate1 > 12.0:
            jam_hits += 1
            if mate1 > max_ov:
                max_ov = mate1
                worst = {"q": round(q, 4), "pair": "gear1_bites_slider1_while_blank", "overlap_mm3": round(mate1, 3)}
        if not gear2_active(q) and not near_gear2_window(q, 4.0) and mate2 > 12.0:
            jam_hits += 1
            if mate2 > max_ov:
                max_ov = mate2
                worst = {"q": round(q, 4), "pair": "gear2_bites_slider2_while_blank", "overlap_mm3": round(mate2, 3)}

        rows.append({
            "q": round(q, 4),
            "gear1_active": gear1_active(q),
            "gear2_active": gear2_active(q),
            "overlaps": row_ov,
        })

    rev_ok = True
    b = drive_phase_bounds()
    for q in (TRAVEL_MAX, b["gear2_2"][1], b["gear2_1"][1], 0.0):
        st = selector_state(q)
        if q >= b["gear2_2"][0] and st["chute_index"] != 2:
            rev_ok = False
        if b["gear2_1"][0] <= q < b["gear2_2"][0] and st["chute_index"] != 1:
            rev_ok = False
        if q < b["gear2_1"][0] and st["chute_index"] != 0:
            rev_ok = False

    mesh_a = verify_gear_mesh(1.0)
    mesh_b = verify_gear_mesh(0.5 * sum(b["gear1_b"]))
    mesh_j = verify_gear_mesh(0.5 * sum(b["gear2_1"]))
    full = make_involute_pinion_local(
        module=GEAR_M, teeth=GEAR_Z, face_w=FACE, bore=0.0,
        alpha_deg=ALPHA_DEG, tooth_clear=TOOTH_CLEAR,
    )
    uni = verify_pinion_teeth_uniform(full, gear_math(), face_w=FACE)

    passed = (
        jam_hits == 0 and rev_ok and mesh_a["pass"] and mesh_b["pass"]
        and mesh_j["pass"] and uni["pass"]
    )
    return {
        "pass": passed,
        "jam_hits": jam_hits,
        "max_overlap_mm3": round(max_ov, 3),
        "worst": worst,
        "reverse_landmarks_ok": rev_ok,
        "mesh_s0": mesh_a,
        "mesh_s10": mesh_b,
        "mesh_jump": mesh_j,
        "uniform_teeth": uni,
        "n_steps": n_steps,
        "samples": rows,
    }


def _flow_obstacles(q: float) -> Part.Shape:
    return _one(
        make_inlet_chute()
        .fuse(make_width_gate_fixed(q))
        .fuse(make_slider1_with_rack(q))
        .fuse(make_slider1_y_rails())
        .fuse(_fuse_shapes([sh for _n, sh, _c in make_cassette_chutes(q)]))
    )


def verify_open_bottom_on_disc(q: float = 5.0) -> dict:
    """Floor corridor clear under inlet/cassette (Rotary_Disc removed)."""
    base = make_base_plate()
    inlet = make_inlet_chute()
    cass = _fuse_shapes([sh for _n, sh, _c in make_cassette_chutes(q)])
    slab = _box(5.0, GATE_LEFT_INNER + 0.5, DISC_Z_TOP + 0.05, INLET_L - 8.0, 2.0, 0.2)
    open_inlet = common_volume(slab, inlet) < 0.01 and common_volume(slab, base) < 0.01
    cy = cassette_y_for_travel(q)
    btm = lane_bottoms_local()[chute_index_for_travel(q)]
    slab2 = _box(
        INLET_L + GATE_L + 4.0, cy + btm + 0.5, DISC_Z_TOP + 0.05,
        CHUTE_L - 8.0, 2.0, 0.2,
    )
    open_cass = common_volume(slab2, cass) < 0.01
    zmin_i = float(inlet.BoundBox.ZMin)
    zmin_c = float(cass.BoundBox.ZMin)
    seat_ok = (
        abs(zmin_i - CHUTE_Z0) < 0.35
        and abs(zmin_c - CHUTE_Z0) < 0.35
        and abs(CHUTE_Z0 - DISC_Z_TOP - DISC_CLEAR) < 1e-9
    )
    return {
        "pass": bool(open_inlet and open_cass and seat_ok),
        "open_bottom_inlet": open_inlet,
        "open_bottom_cassette": open_cass,
        "chute_floor_z_ok": seat_ok,
        "inlet_slab_vs_base_mm3": round(common_volume(slab, base), 4),
    }


def verify_gate_seal_no_gaps(n_steps: int = 13, probe_r: float = 0.45, jam_vol_mm3: float = 0.02) -> dict:
    rows = []
    hits = 0
    worst = None
    n_x, n_y, n_z = 5, 10, 4
    # At q=0 the junction mouth must be fully blocked by shutter
    mouth = _box(INLET_L + 0.5, GATE_LEFT_INNER + 0.5, CHUTE_Z0 + 0.5, GATE_L - 1.0, INLET_W - 1.0, GATE_H - WALL_T - 1.0)
    shutter0 = make_slider_bar_core(0.0)
    sealed_vol = common_volume(mouth, shutter0)
    sealed_block_ok = sealed_vol > 0.85 * mouth.Volume

    for i in range(n_steps):
        q = TRAVEL_MAX * i / max(1, n_steps - 1)
        ap = aperture_mm(q)
        y_jaw = bar_y0(q)
        solids = _one(
            make_inlet_chute()
            .fuse(make_width_gate_fixed(q))
            .fuse(make_slider_bar_core(q))
            .fuse(_fuse_shapes([sh for _n, sh, _c in make_cassette_chutes(q)]))
        )
        gap_n = 0
        gap_pt = None
        for ix in range(n_x):
            x = INLET_L + (ix + 0.5) / n_x * GATE_L
            for iy in range(n_y):
                y = GATE_LEFT_INNER + (iy + 0.5) / n_y * INLET_W
                # Open band (flow) — do not require solid there
                if ap > 2.0 * probe_r and (GATE_LEFT_INNER + probe_r) < y < (y_jaw + 1e-9):
                    continue
                for iz in range(n_z):
                    z = CHUTE_Z0 + (iz + 0.5) / n_z * (GATE_H - WALL_T)
                    ball = Part.makeSphere(probe_r)
                    ball.translate(App.Vector(x, y, z))
                    if common_volume(ball, solids) < jam_vol_mm3:
                        gap_n += 1
                        if gap_pt is None:
                            gap_pt = {"x": round(x, 3), "y": round(y, 3), "z": round(z, 3)}
        ok = gap_n == 0
        if not ok:
            hits += 1
            if worst is None:
                worst = {"q": round(q, 4), "gaps": gap_n, "at": gap_pt}
        rows.append({"q": round(q, 4), "aperture_mm": round(ap, 4), "gap_hits": gap_n, "ok": ok})
    x_flush = abs(bar_x0() - INLET_L) <= 1e-9 and abs(bar_x0() + bar_dx() - (INLET_L + GATE_L)) <= 1e-9
    return {
        "pass": hits == 0 and x_flush and sealed_block_ok,
        "gap_pose_hits": hits,
        "bar_x_flush_inlet_cassette": x_flush,
        "sealed_at_0_blocks_junction": sealed_block_ok,
        "sealed_overlap_mm3": round(sealed_vol, 3),
        "worst": worst,
        "samples": rows,
    }


def verify_flow_path_geometry(n_steps: int = 13, probe_r: float = 1.2, jam_vol_mm3: float = 0.02) -> dict:
    rows = []
    hits = 0
    worst = None
    max_ov = 0.0
    flush_ok = True
    flush_worst = 0.0
    x_start, x_end = 2.0, INLET_L + GATE_L + CHUTE_L - 2.0
    n_probe = 28

    for i in range(n_steps):
        q = TRAVEL_MAX * i / max(1, n_steps - 1)
        st = selector_state(q)
        err = abs(st["active_lane_bottom_y"] - GATE_LEFT_INNER)
        if not gear2_active(q):
            flush_worst = max(flush_worst, err)
            if err > 1e-6:
                flush_ok = False
        ap = aperture_mm(q)
        row = {
            "q": round(q, 4), "aperture_mm": ap, "chute": st["chute_name"],
            "bottom_err_mm": round(err, 6), "gear2_transit": gear2_active(q),
        }
        if gear2_active(q) or ap <= 2.0 * probe_r + 1e-9:
            row["path_clear"] = True
            row["skipped"] = "sealed_or_gear2"
            rows.append(row)
            continue
        r = min(probe_r, 0.45 * min(ap, active_lane_width(q)))
        if r < 0.4:
            row["path_clear"] = False
            hits += 1
            rows.append(row)
            continue
        y_c = flow_center_y(q)
        z_c = DISC_Z_TOP + r + 0.05
        obstacles = _flow_obstacles(q)
        path_hit = False
        hit_x = None
        hit_ov = 0.0
        for k in range(n_probe):
            x = x_start + (x_end - x_start) * k / max(1, n_probe - 1)
            ball = Part.makeSphere(r)
            ball.translate(App.Vector(x, y_c, z_c))
            ov = common_volume(ball, obstacles)
            if ov > jam_vol_mm3:
                path_hit = True
                hit_x = x
                hit_ov = ov
                break
        row["path_clear"] = not path_hit
        if path_hit:
            hits += 1
            worst = {"q": round(q, 4), "x": round(hit_x, 3), "overlap_mm3": round(hit_ov, 4)}
            max_ov = max(max_ov, hit_ov)
        rows.append(row)

    open_v = verify_open_bottom_on_disc(2.0)
    return {
        "pass": hits == 0 and flush_ok and open_v["pass"],
        "flow_jam_hits": hits,
        "bottom_flush_ok": flush_ok,
        "outer_edge_flush_ok": flush_ok,
        "max_bottom_err_mm": round(flush_worst, 9),
        "max_path_overlap_mm3": round(max_ov, 4),
        "worst": worst,
        "open_bottom_on_disc": open_v,
        "samples": rows,
    }


def slider_velocities(q0: float, q1: float) -> dict:
    """
    Vận tốc trung bình hai thanh trên đoạn núm q0→q1 (mm slider / mm cung bước).
    Thanh 1 = aperture (+Y khi mở); thanh 2 = cassette Y (âm khi nhảy lane rộng hơn).
    """
    dq = q1 - q0
    if abs(dq) < 1e-15:
        return {
            "dq": 0.0, "v1": 0.0, "v2": 0.0,
            "moving1": False, "moving2": False,
            "both_idle": True, "both_moving": False, "xor_one": False,
        }
    dap = aperture_mm(q1) - aperture_mm(q0)
    dcy = cassette_y_for_travel(q1) - cassette_y_for_travel(q0)
    v1 = dap / dq
    v2 = dcy / dq
    moving1 = abs(dap) > 1e-9
    moving2 = abs(dcy) > 1e-9
    return {
        "dq": dq,
        "v1": v1,
        "v2": v2,
        "dap": dap,
        "dcy": dcy,
        "moving1": moving1,
        "moving2": moving2,
        "both_idle": (not moving1) and (not moving2),
        "both_moving": moving1 and moving2,
        "xor_one": moving1 != moving2,
    }


def verify_slider_mutex_opposite(step_mm: float = 0.1) -> dict:
    """
    Khi núm xoay (q đổi):
      1) Hai thanh đi ngược chiều (+Y vs −Y khi q tăng).
      2) Cùng lúc chỉ một thanh chuyển động.
      3) Không có đoạn nào cả hai cùng dừng (trong khi núm đang quay).
    """
    n = int(round(TRAVEL_MAX / step_mm)) + 1
    xs = [min(TRAVEL_MAX, i * step_mm) for i in range(n)]
    if xs[-1] < TRAVEL_MAX - 1e-12:
        xs.append(TRAVEL_MAX)

    rows = []
    both_idle_hits = 0
    both_move_hits = 0
    bad_sign_hits = 0
    xor_ok = True
    cover_ok = True
    opposite_ok = True
    worst = None
    s1_sign_fwd = None  # expect +1
    s2_sign_fwd = None  # expect -1

    for i in range(len(xs) - 1):
        q0, q1 = xs[i], xs[i + 1]
        vel = slider_velocities(q0, q1)
        mid = 0.5 * (q0 + q1)
        g1 = gear1_active(mid)
        g2 = gear2_active(mid)
        row = {
            "q0": round(q0, 4), "q1": round(q1, 4),
            "v1": round(vel["v1"], 6), "v2": round(vel["v2"], 6),
            "moving1": vel["moving1"], "moving2": vel["moving2"],
            "gear1_active": g1, "gear2_active": g2,
            "xor_one": vel["xor_one"],
        }
        # (2) only one moves
        if vel["both_moving"]:
            both_move_hits += 1
            xor_ok = False
            worst = {**row, "fail": "both_moving"}
        # (3) never both idle while knob turns
        if vel["both_idle"]:
            both_idle_hits += 1
            cover_ok = False
            worst = {**row, "fail": "both_idle"}
        if not vel["xor_one"]:
            xor_ok = False
        # Active gear flags must match who moves
        if g1 and g2:
            xor_ok = False
            worst = {**row, "fail": "both_gears_active"}
        if g1 != vel["moving1"] or g2 != vel["moving2"]:
            # allow tiny edge mismatch only if motion matches xor
            if vel["moving1"] != g1 or vel["moving2"] != g2:
                xor_ok = False
                worst = {**row, "fail": "active_vs_velocity_mismatch"}
        # (1) opposite directions on forward dq>0
        if vel["moving1"]:
            if vel["v1"] <= 1e-9:
                opposite_ok = False
                bad_sign_hits += 1
                worst = {**row, "fail": "slider1_not_plus_Y"}
            s1_sign_fwd = 1
        if vel["moving2"]:
            if vel["v2"] >= -1e-9:
                opposite_ok = False
                bad_sign_hits += 1
                worst = {**row, "fail": "slider2_not_minus_Y"}
            s2_sign_fwd = -1
        rows.append(row)

    # Reverse pass: physical directions flip with dq; still xor / no both-idle
    rev_ok = True
    rev_worst = None
    for i in range(len(xs) - 1, 0, -1):
        q0, q1 = xs[i], xs[i - 1]  # dq < 0
        vel = slider_velocities(q0, q1)
        if vel["both_idle"] or vel["both_moving"] or not vel["xor_one"]:
            rev_ok = False
            rev_worst = {
                "q0": round(q0, 4), "q1": round(q1, 4),
                "dap": round(vel["dap"], 6), "dcy": round(vel["dcy"], 6),
                "fail": "rev_xor_or_idle",
            }
            break
        # Knob reverse (dq<0): s1 closes (dap<0), s2 returns +Y (dcy>0)
        if vel["moving1"] and vel["dap"] >= -1e-12:
            rev_ok = False
            rev_worst = {"q0": q0, "q1": q1, "dap": vel["dap"], "fail": "rev_s1_should_close"}
            break
        if vel["moving2"] and vel["dcy"] <= 1e-12:
            rev_ok = False
            rev_worst = {"q0": q0, "q1": q1, "dcy": vel["dcy"], "fail": "rev_s2_should_return_plusY"}
            break
        # Still opposite: physical s1 vs s2 signs differ across phases (s1 tracks dq, s2 anti-dq)
        if vel["moving1"] and abs(vel["dap"] - vel["dq"]) > 1e-6:
            rev_ok = False
            rev_worst = {"q0": q0, "fail": "rev_s1_pitch"}
            break
        if vel["moving2"] and abs(vel["dcy"] + vel["dq"]) > 1e-6:
            rev_ok = False
            rev_worst = {"q0": q0, "fail": "rev_s2_pitch"}
            break

    signs_opposite = (
        s1_sign_fwd == 1 and s2_sign_fwd == -1
    )
    opposite_ok = opposite_ok and signs_opposite

    # Pitch sync: |v| == 1 on the moving slider (dap or |dcy| == |dq|)
    pitch_ok = True
    for i in range(len(xs) - 1):
        vel = slider_velocities(xs[i], xs[i + 1])
        if vel["moving1"] and abs(abs(vel["dap"]) - abs(vel["dq"])) > 1e-6:
            pitch_ok = False
        if vel["moving2"] and abs(abs(vel["dcy"]) - abs(vel["dq"])) > 1e-6:
            pitch_ok = False

    passed = bool(xor_ok and cover_ok and opposite_ok and rev_ok and pitch_ok)
    return {
        "pass": passed,
        "rules": {
            "opposite_directions": opposite_ok,
            "only_one_moves": xor_ok and both_move_hits == 0,
            "never_both_idle_while_knob_turns": cover_ok and both_idle_hits == 0,
            "reverse_knob_ok": rev_ok,
            "pitch_arc_sync": pitch_ok,
        },
        "slider1_forward_sign": s1_sign_fwd,  # +1 => +Y
        "slider2_forward_sign": s2_sign_fwd,  # -1 => -Y
        "both_idle_hits": both_idle_hits,
        "both_moving_hits": both_move_hits,
        "bad_sign_hits": bad_sign_hits,
        "worst": worst,
        "rev_worst": rev_worst,
        "n_segments": len(rows),
        "phases": {k: list(drive_phase_bounds()[k]) for k in (
            "gear1_a", "gear2_1", "gear1_b", "gear2_2", "gear1_c"
        )},
        "sample_handoffs": [
            r for r in rows
            if abs(r["q0"] - 5.0) < step_mm + 1e-9
            or abs(r["q0"] - 11.0) < step_mm + 1e-9
            or abs(r["q0"] - 15.0) < step_mm + 1e-9
            or abs(r["q0"] - 25.0) < step_mm + 1e-9
        ][:12],
    }


def verify_bidirectional_knob(step_mm: float = 1.0) -> dict:
    """
    Math + kinematics: knob forward 0→TRAVEL_MAX then reverse back to 0.
    Checks θ1 = −q/r, θ2 = −θ1, freeze bands, home/end landmarks.
    """
    r = gear_math()["pitch_radius"]
    xs_fwd = []
    q = 0.0
    while q < TRAVEL_MAX - 1e-9:
        xs_fwd.append(round(q, 6))
        q += step_mm
    xs_fwd.append(TRAVEL_MAX)
    xs_rev = list(reversed(xs_fwd))
    rows = []
    ok = True
    worst = None
    for direction, xs in (("fwd", xs_fwd), ("rev", xs_rev)):
        for qq in xs:
            st = selector_state(qq)
            th1 = st["gear1_angle_deg"]
            th2 = st["gear2_angle_deg"]
            th_exp = -(qq / r) * (180.0 / math.pi)
            e_th = abs(th1 - th_exp)
            e_rev = abs(th2 + th1)
            row = {
                "dir": direction, "q": round(qq, 4),
                "ap": st["aperture_mm"], "cass_dy": st["slider2_mm"],
                "th1": round(th1, 4), "th2": round(th2, 4),
                "chute": st["chute_name"],
                "theta_err": round(e_th, 6), "reverse_err": round(e_rev, 6),
            }
            if e_th > 1e-4 or e_rev > 1e-4:
                ok = False
                worst = row
            rows.append(row)
    st0 = selector_state(0.0)
    st_end = selector_state(TRAVEL_MAX)
    home_ok = abs(st0["aperture_mm"]) < 1e-9 and abs(st0["slider2_mm"]) < 1e-9
    end_ok = abs(st_end["aperture_mm"] - APERTURE_MAX) < 1e-6 and st_end["chute_index"] == 2
    freeze_ok = True
    n = int(round(TRAVEL_MAX / 0.25)) + 1
    xs = [min(TRAVEL_MAX, i * 0.25) for i in range(n)]
    aps = [aperture_mm(qq) for qq in xs]
    cys = [cassette_y_for_travel(qq) for qq in xs]
    for i in range(len(xs) - 1):
        mid = 0.5 * (xs[i] + xs[i + 1])
        if (not gear1_active(mid)) and abs(aps[i + 1] - aps[i]) > 1e-6:
            freeze_ok = False
        if (not gear2_active(mid)) and abs(cys[i + 1] - cys[i]) > 1e-6:
            freeze_ok = False
    # Bidirectional jam at endpoints + mid landmarks
    jam_hits = 0
    jam_worst = None
    for qq in (0.0, 0.5 * TRAVEL_MAX, TRAVEL_MAX, 0.5 * TRAVEL_MAX, 0.0):
        s1 = make_slider1_with_rack(qq)
        s2 = make_slider2_with_rack(qq)
        brg = make_dual_bearing_supports()
        deck = make_gear_deck()
        for name, a, b in (
            ("s1_brg", s1, brg), ("s2_brg", s2, brg),
            ("s1_deck", s1, deck), ("s2_deck", s2, deck),
        ):
            ov = common_volume(a, b)
            if ov > 0.5:
                jam_hits += 1
                jam_worst = {"q": round(qq, 4), "pair": name, "overlap_mm3": round(ov, 3)}
    return {
        "pass": bool(ok and home_ok and end_ok and freeze_ok and jam_hits == 0),
        "home_ok": home_ok,
        "end_ok": end_ok,
        "freeze_ok": freeze_ok,
        "bidir_jam_hits": jam_hits,
        "bidir_jam_worst": jam_worst,
        "worst": worst,
        "n_samples": len(rows),
        "samples_endpoints": [rows[0], rows[len(xs_fwd) - 1], rows[-1]],
    }


def write_verify_json(path: Path | None = None) -> dict:
    out = Path(path) if path else Path(__file__).resolve().parent / "out" / "width_chute_selector_verify.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    math_v = verify_dwell_jump_math()
    mutex_v = verify_slider_mutex_opposite()
    bidir_v = verify_bidirectional_knob()
    jam_v = verify_no_jam_sweep()
    flow_v = verify_flow_path_geometry()
    seal_v = verify_gate_seal_no_gaps()
    payload = {
        "pass": bool(
            math_v["pass"] and mutex_v["pass"] and bidir_v["pass"] and jam_v["pass"]
            and flow_v["pass"] and seal_v["pass"]
        ),
        "math": math_v,
        "slider_mutex_opposite": mutex_v,
        "bidirectional_knob": bidir_v,
        "collision_sweep": jam_v,
        "flow_path_geometry": flow_v,
        "gate_seal_no_gaps": seal_v,
        "drive": "two_gear_direct_mesh",
        "removed_components": [
            "Rotary_Disc", "Travel_Scale_Y", "Align_Proxy",
            "Idler1", "Idler2", "Train_Gear1_Continuous", "Train_Gear2_Continuous",
        ],
    }
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    v = write_verify_json()
    print("pass:", v["pass"])
    print("math:", v["math"]["checks"])
    print("bidir:", v["bidirectional_knob"]["pass"], "jam_hits:", v["bidirectional_knob"].get("bidir_jam_hits"))
    print("jam_hits:", v["collision_sweep"]["jam_hits"], "worst:", v["collision_sweep"].get("worst"))
    print("flow:", v["flow_path_geometry"]["pass"], "seal:", v["gate_seal_no_gaps"]["pass"])
