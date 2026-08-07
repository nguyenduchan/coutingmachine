"""
L-Flap Divert — parallel grooves + aperture slider + Scotch-yoke flap.

Grooves: Small 5.5 mm | Large 12.0 mm, flow -Y.

Slider travel (open_mm):
  1) SMALL band  → L_Flap keeps LARGE blocked; Aperture meters 5.5 mm inlet
  2) past threshold → closes SMALL, opens LARGE; Aperture meters 12 mm inlet

Actuation: Drive_Pin in Gap_Slider yoke (contact). No spring.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import FreeCAD as App
    import Part

_App = None
_Part = None


def _fc():
    global _App, _Part
    if _App is None:
        import FreeCAD as App  # noqa: PLC0415
        import Part  # noqa: PLC0415

        _App = App
        _Part = Part
    return _App, _Part


# ---- lane / threshold ----
THRESHOLD_MM = 5.0
LUG_A_TRIP = 5.1
LUG_B_TRIP = 4.9
FLAP_ANGLE_SMALL = 5.0
FLAP_ANGLE_LARGE = 85.0

# ---- grooves ----
SMALL_GROOVE_W = 5.5
LARGE_GROOVE_W = 12.0
DIVIDER_T = 2.0
GROOVE_LEN = 45.0
INLET_L = 22.0
CLEAR = 0.4

# ---- frame / pivot ----
WALL_T = 2.5
WALL_H = 22.0
FLOOR_T = 2.0
PIVOT_D = 3.0
PIVOT_BORE = 3.3
PIVOT_BOSS_OD = 8.0
PIVOT_BOSS_H = 3.5
PIVOT_AXIAL_GAP = 0.5

L_THICK = 2.0
L_Z0 = FLOOR_T + PIVOT_BOSS_H + PIVOT_AXIAL_GAP
L_H = 12.0
ARM_ROOT = DIVIDER_T / 2.0 + CLEAR
# Gate bars: length = full groove width
ARM_LARGE_L = LARGE_GROOVE_W
ARM_SMALL_L = SMALL_GROOVE_W

# Actuator cross: Arm_A (+X) ↔ large groove, Arm_B (+Y) ↔ small groove
ACT_ARM_A_L = LARGE_GROOVE_W   # 12.0
ACT_ARM_B_L = SMALL_GROOVE_W   # 5.5
ACT_ARM_W = 2.4
ACT_ARM_H = 3.5
ACT_Z0 = L_Z0 + L_H + 1.0
# legacy alias (longer arm) for docs / reach
ACT_ARM_L = ACT_ARM_A_L

SLIDER_Y = 0.0
SLIDER_T = 4.0
SLIDER_H = 4.0
SLIDER_LEN = 70.0
SLIDER_Z0 = ACT_Z0 + ACT_ARM_H + 4.0
PILL_CLEAR_H = ACT_Z0 - FLOOR_T - 0.5
SLIDER_X0_AT_OPEN0 = -20.0

# Drive pin on −Y (Scotch-yoke); radius set to push both bars as one rigid cross
DRIVE_PIN_R = max(ACT_ARM_A_L, ACT_ARM_B_L) * 0.55  # ~6.6 mm
DRIVE_PIN_D = 2.6
LUG_DRIVE_W = 2.5
LUG_DRIVE_T = 3.2
YOKE_H_Z0 = ACT_Z0 + ACT_ARM_H + 0.3
YOKE_Y0 = -DRIVE_PIN_R - LUG_DRIVE_T / 2
YOKE_Y1 = -DRIVE_PIN_R + LUG_DRIVE_T / 2
YOKE_CLEAR = 0.8
YOKE_SLOT_W = LUG_DRIVE_W
YOKE_JAW_T = LUG_DRIVE_W

OPEN_SMALL_LO = 1.0
OPEN_SMALL_HI = THRESHOLD_MM
OPEN_TRANSIT_LO = THRESHOLD_MM
_PIN_SMALL_X = DRIVE_PIN_R * math.sin(math.radians(FLAP_ANGLE_SMALL))
_PIN_LARGE_X = DRIVE_PIN_R * math.sin(math.radians(FLAP_ANGLE_LARGE))
_PIN_HALF = DRIVE_PIN_D / 2.0
OPEN_TRANSIT_HI = (
    OPEN_TRANSIT_LO
    + (_PIN_LARGE_X - _PIN_SMALL_X)
    + LUG_DRIVE_W
    + DRIVE_PIN_D
    + 0.6
)
OPEN_LARGE_LO = OPEN_TRANSIT_HI
OPEN_LARGE_HI = OPEN_LARGE_LO + LARGE_GROOVE_W
OPEN_DRIVE_LO = OPEN_SMALL_LO
OPEN_DRIVE_HI = OPEN_LARGE_HI

LUG_DRIVE_REL = (
    _PIN_SMALL_X - _PIN_HALF - 0.35 - LUG_DRIVE_W - SLIDER_X0_AT_OPEN0 - OPEN_TRANSIT_LO
)
YOKE_CX_REL = LUG_DRIVE_REL + LUG_DRIVE_W / 2.0
LUG_RETURN_REL = LUG_DRIVE_REL

# Continuous U-rail under Gap_Slider bar (bar pose fixed: SLIDER_Y / SLIDER_Z0)
RAIL_MARGIN = 8.0
RAIL_X0 = SLIDER_X0_AT_OPEN0 + OPEN_SMALL_LO - RAIL_MARGIN
RAIL_X1 = SLIDER_X0_AT_OPEN0 + OPEN_LARGE_HI + SLIDER_LEN + RAIL_MARGIN
RAIL_BASE_T = 1.5
RAIL_SLOT_CLEAR = 0.35
RAIL_SLOT_DY = SLIDER_T + 2.0 * RAIL_SLOT_CLEAR
RAIL_WALL = 2.0
RAIL_OUTER_DY = RAIL_SLOT_DY + 2.0 * RAIL_WALL
RAIL_H = SLIDER_H + 2.5  # wall height above base top
RAIL_Z0 = SLIDER_Z0 - RAIL_BASE_T  # base top == bar bottom

APERTURE_MIN = 1.2
# Beyond L_Flap arm reach (~12 mm) so LARGE pose does not hit the plate
APERTURE_Y0 = 14.0
APERTURE_Y1 = 20.0
APERTURE_Z0 = FLOOR_T + 0.4
APERTURE_Z1 = L_Z0 + L_H * 0.55

_g_half = DIVIDER_T / 2.0
_SMALL_X0 = -_g_half - SMALL_GROOVE_W
_SMALL_X1 = -_g_half
_LARGE_X0 = _g_half
_LARGE_X1 = _g_half + LARGE_GROOVE_W
WIN_SMALL_W = SMALL_GROOVE_W
WIN_SMALL_REL = _SMALL_X0 - SLIDER_X0_AT_OPEN0 - OPEN_SMALL_HI
WIN_LARGE_W = LARGE_GROOVE_W
WIN_LARGE_REL = _LARGE_X0 - SLIDER_X0_AT_OPEN0 - OPEN_LARGE_HI

LUG_W = 2.8
LUG_Y0 = 3.8
LUG_Y1 = ACT_ARM_A_L + 1.5
LUG_T = LUG_Y1 - LUG_Y0
LUG_REACH_Y = DRIVE_PIN_R
TIP_X_AT_STOPS = _PIN_SMALL_X
LUG_GAP_EPS = 0.35


def _box(dx, dy, dz, x0, y0, z0):
    App, Part = _fc()
    b = Part.makeBox(max(dx, 0.05), max(dy, 0.05), max(dz, 0.05))
    b.translate(App.Vector(x0, y0, z0))
    return b


def _cyl(d, h, x, y, z):
    App, Part = _fc()
    c = Part.makeCylinder(d / 2.0, max(h, 0.05))
    c.translate(App.Vector(x, y, z))
    return c


def _clean(shape):
    if shape is None:
        return shape
    return shape.removeSplitter() if hasattr(shape, "removeSplitter") else shape


def _keep(shape, *, dust_vol: float = 0.05, single: bool = False):
    """
    Drop boolean dust. By default keep ALL significant solids as a compound
    (Gap_Slider bar + aperture must not be discarded).
    single=True → legacy largest-solid-only (frame cleanup).
    """
    App, Part = _fc()
    if shape is None or not getattr(shape, "Solids", None):
        return shape
    sols = [s for s in shape.Solids if abs(float(s.Volume)) >= dust_vol]
    if not sols:
        return _clean(shape)
    if single:
        sols.sort(key=lambda s: abs(float(s.Volume)), reverse=True)
        return _clean(sols[0])
    if len(sols) == 1:
        return _clean(sols[0])
    return _clean(Part.makeCompound(sols))


def _fuse(a, b, *, single: bool = False):
    return _keep(a.fuse(b), single=single)


def groove_x_bounds() -> dict:
    half_d = DIVIDER_T / 2.0
    return {
        "small_x0": -half_d - SMALL_GROOVE_W,
        "small_x1": -half_d,
        "large_x0": half_d,
        "large_x1": half_d + LARGE_GROOVE_W,
        "outer_x0": -half_d - SMALL_GROOVE_W - WALL_T,
        "outer_x1": half_d + LARGE_GROOVE_W + WALL_T,
    }


def flap_state_for_open(slider_open_mm: float, prev: str | None = None) -> str:
    if slider_open_mm >= LUG_A_TRIP:
        return "LARGE"
    if slider_open_mm <= LUG_B_TRIP:
        return "SMALL"
    return prev if prev in ("SMALL", "LARGE") else "SMALL"


def flap_angle_deg(state: str) -> float:
    return FLAP_ANGLE_LARGE if state == "LARGE" else FLAP_ANGLE_SMALL


def slider_x_left(open_mm: float) -> float:
    return SLIDER_X0_AT_OPEN0 + float(open_mm)


def flap_angle_for_open(slider_open_mm: float) -> float:
    if slider_open_mm <= OPEN_TRANSIT_LO:
        return FLAP_ANGLE_SMALL
    if slider_open_mm >= OPEN_TRANSIT_HI:
        return FLAP_ANGLE_LARGE
    t = (slider_open_mm - OPEN_TRANSIT_LO) / max(1e-6, OPEN_TRANSIT_HI - OPEN_TRANSIT_LO)
    return FLAP_ANGLE_SMALL + t * (FLAP_ANGLE_LARGE - FLAP_ANGLE_SMALL)


def yoke_slot_center_x(open_mm: float) -> float:
    return slider_x_left(open_mm) + YOKE_CX_REL


def lug_world_x(open_mm: float) -> tuple[float, float]:
    """(unused_return_left, drive_lug_left). Single drive lug — both faces used."""
    drive_left = slider_x_left(open_mm) + LUG_DRIVE_REL
    return (drive_left + LUG_DRIVE_W + 50.0, drive_left)  # park fake return far away


def _overlap_1d(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def aperture_windows(open_mm: float) -> dict:
    x_left = slider_x_left(open_mm)
    s0 = x_left + WIN_SMALL_REL
    l0 = x_left + WIN_LARGE_REL
    return {
        "small": (s0, s0 + WIN_SMALL_W),
        "large": (l0, l0 + WIN_LARGE_W),
    }


def aperture_widths(open_mm: float) -> dict:
    g = groove_x_bounds()
    wins = aperture_windows(open_mm)
    w_s = _overlap_1d(wins["small"][0], wins["small"][1], g["small_x0"], g["small_x1"])
    w_l = _overlap_1d(wins["large"][0], wins["large"][1], g["large_x0"], g["large_x1"])
    state = flap_state_for_open(open_mm)
    return {
        "small_mm": round(w_s, 3),
        "large_mm": round(w_l, 3),
        "active": state,
        "active_width_mm": round(w_s if state == "SMALL" else w_l, 3),
    }


def make_aperture_plate(open_mm: float):
    g = groove_x_bounds()
    x_left = slider_x_left(open_mm)
    # Keep plate between inner faces of side walls
    plate_x0 = g["outer_x0"] + WALL_T + CLEAR
    plate_x1 = g["outer_x1"] - WALL_T - CLEAR
    z0, z1 = APERTURE_Z0, APERTURE_Z1
    y0, y1 = APERTURE_Y0, APERTURE_Y1
    plate = _box(plate_x1 - plate_x0, y1 - y0, z1 - z0, plate_x0, y0, z0)

    wins = aperture_windows(open_mm)
    for a0, a1 in (wins["small"], wins["large"]):
        # Clip window cut to plate span
        c0 = max(a0, plate_x0)
        c1 = min(a1, plate_x1)
        if c1 - c0 < 0.2:
            continue
        cutter = _box(
            c1 - c0, (y1 - y0) + 1.0, (z1 - z0) + 1.0, c0, y0 - 0.5, z0 - 0.5
        )
        try:
            plate = plate.cut(cutter)
        except Exception:
            pass

    # Stem up + bridge −Y to Gap_Slider bar (fixed at SLIDER_Y) — one connected solid
    stem_x0 = min(max(x_left + SLIDER_LEN * 0.35, plate_x0 + 1), plate_x1 - 15)
    stem_z0 = z1 - 0.3
    stem_h = (SLIDER_Z0 + 0.6) - stem_z0
    post = _box(14.0, 2.5, stem_h, stem_x0, y0 + 0.5, stem_z0)
    bar_y0 = SLIDER_Y - SLIDER_T / 2.0
    bridge_dy = (y0 + 0.5) - bar_y0 + 0.5
    bridge = _box(14.0, bridge_dy, 2.8, stem_x0, bar_y0 - 0.2, SLIDER_Z0 - 0.3)
    return _keep(plate.fuse(post).fuse(bridge))


def _pivot_xy():
    return (0.0, 0.0)


def make_divert_frame():
    g = groove_x_bounds()
    y_out = -GROOVE_LEN

    floor = _box(
        g["outer_x1"] - g["outer_x0"] + 20.0,
        GROOVE_LEN + INLET_L + 16.0,
        FLOOR_T,
        g["outer_x0"] - 10.0,
        y_out - 8.0,
        0.0,
    )
    wall_l = _box(WALL_T, GROOVE_LEN + INLET_L, WALL_H, g["outer_x0"], y_out, FLOOR_T)
    wall_r = _box(WALL_T, GROOVE_LEN + INLET_L, WALL_H, g["outer_x1"] - WALL_T, y_out, FLOOR_T)

    # Travel windows through side walls for Gap_Slider bar + drive lug/stem (−Y)
    win_y0 = min(SLIDER_Y - SLIDER_T / 2 - 1.0, -DRIVE_PIN_R - LUG_DRIVE_T / 2 - 1.5)
    win_y1 = max(SLIDER_Y + SLIDER_T / 2 + 1.5, 2.5)
    win_dy = win_y1 - win_y0
    win_z0 = min(YOKE_H_Z0 - 1.5, SLIDER_Z0 - 2.0)
    win_z1 = SLIDER_Z0 + SLIDER_H + 2.0
    win_dz = win_z1 - win_z0
    for wx0, wx1 in (
        (g["outer_x0"] - 8.0, g["outer_x0"] + WALL_T + 1.0),
        (g["outer_x1"] - WALL_T - 1.0, g["outer_x1"] + 8.0),
    ):
        cutter = _box(wx1 - wx0, win_dy, win_dz, wx0, win_y0, win_z0)
        wall_l = wall_l.cut(cutter)
        wall_r = wall_r.cut(cutter)

    # Aperture slot through side walls at inlet (full wall thickness)
    ap_cut = _box(
        g["outer_x1"] - g["outer_x0"] + 20.0,
        (APERTURE_Y1 - APERTURE_Y0) + 4.0,
        (APERTURE_Z1 - APERTURE_Z0) + 3.0,
        g["outer_x0"] - 10.0,
        APERTURE_Y0 - 2.0,
        APERTURE_Z0 - 1.0,
    )
    try:
        wall_l = wall_l.cut(ap_cut)
        wall_r = wall_r.cut(ap_cut)
    except Exception:
        pass

    # Also notch divider at inlet aperture height so plate can cross x=0
    div_y1 = -PIVOT_BOSS_OD / 2.0 - CLEAR
    div_h = min(WALL_H, ACT_Z0 - FLOOR_T - CLEAR)
    divider = _box(DIVIDER_T, abs(y_out - div_y1), div_h, -DIVIDER_T / 2.0, y_out, FLOOR_T)
    try:
        divider = divider.cut(
            _box(
                DIVIDER_T + 2.0,
                (APERTURE_Y1 - APERTURE_Y0) + 3.0,
                (APERTURE_Z1 - APERTURE_Z0) + 2.0,
                -DIVIDER_T / 2.0 - 1.0,
                APERTURE_Y0 - 1.5,
                APERTURE_Z0 - 1.0,
            )
        )
    except Exception:
        pass

    dir_h = max(1.0, min(L_Z0 - FLOOR_T - CLEAR, PILL_CLEAR_H - 1.0))
    # Stop inlet divider before aperture Y
    inlet_div = _box(DIVIDER_T, max(1.0, APERTURE_Y0 - 3.0), dir_h, -DIVIDER_T / 2.0, 1.0, FLOOR_T)

    end_wall = _box(
        g["outer_x1"] - g["outer_x0"], WALL_T, WALL_H * 0.4,
        g["outer_x0"], y_out, FLOOR_T,
    )
    end_wall = end_wall.cut(
        _box(SMALL_GROOVE_W - 0.4, WALL_T + 2, WALL_H, g["small_x0"] + 0.2, y_out - 1, FLOOR_T + 0.5)
    )
    end_wall = end_wall.cut(
        _box(LARGE_GROOVE_W - 0.4, WALL_T + 2, WALL_H, g["large_x0"] + 0.2, y_out - 1, FLOOR_T + 0.5)
    )

    px, py = _pivot_xy()
    post_s = _cyl(PIVOT_BOSS_OD, PIVOT_BOSS_H, px, py, FLOOR_T)
    post_s = post_s.cut(_cyl(PIVOT_BORE, PIVOT_BOSS_H + 1, px, py, FLOOR_T - 0.5))

    # Angle stops — keep clear of aperture (+Y) and drive pin (−Y)
    stop_h = L_H * 0.45
    stop_z = L_Z0 + 2.0
    stop_small = _box(1.8, 1.8, stop_h, ARM_ROOT + ARM_LARGE_L - 0.8, -L_THICK - 2.0, stop_z)
    stop_large = _box(1.8, 1.8, stop_h, -L_THICK - 2.0, ARM_ROOT + ARM_SMALL_L - 0.8, stop_z)

    body = floor
    for p in (wall_l, wall_r, divider, inlet_div, end_wall, post_s, stop_small, stop_large):
        body = _fuse(body, p, single=True)

    pocket = _cyl(PIVOT_BOSS_OD + 1.0, L_H + 1.0, px, py, L_Z0 - 0.3)
    try:
        body = body.cut(pocket)
    except Exception:
        pass
    body = _fuse(body, post_s, single=True)

    # Tunnel for continuous Slider_Rail + Gap_Slider bar
    tunnel = _box(
        RAIL_X1 - RAIL_X0 + 4.0,
        RAIL_OUTER_DY + 2.0,
        RAIL_BASE_T + RAIL_H + 2.0,
        RAIL_X0 - 2.0,
        -RAIL_OUTER_DY / 2.0 - 1.0,
        RAIL_Z0 - 1.0,
    )
    try:
        body = body.cut(tunnel)
    except Exception:
        pass
    return _keep(body, single=True)


def make_slider_rail_parts():
    """
    Continuous U-rail along +X spanning full Gap_Slider travel.
    Base top at SLIDER_Z0 — Gap_Slider bar (unchanged pose) rides in the slot.
    """
    x0, x1 = RAIL_X0, RAIL_X1
    dx = x1 - x0
    y_out0 = -RAIL_OUTER_DY / 2.0
    z0 = RAIL_Z0
    z_slot = z0 + RAIL_BASE_T  # == SLIDER_Z0
    base = _box(dx, RAIL_OUTER_DY, RAIL_BASE_T, x0, y_out0, z0)
    wall_n = _box(dx, RAIL_WALL, RAIL_H, x0, y_out0, z_slot)
    wall_p = _box(dx, RAIL_WALL, RAIL_H, x0, RAIL_OUTER_DY / 2.0 - RAIL_WALL, z_slot)
    end_l = _box(RAIL_WALL, RAIL_OUTER_DY, RAIL_BASE_T + RAIL_H, x0, y_out0, z0)
    end_r = _box(RAIL_WALL, RAIL_OUTER_DY, RAIL_BASE_T + RAIL_H, x1 - RAIL_WALL, y_out0, z0)
    # Slot through ends for bar travel (stops only on outer Y walls)
    end_l = end_l.cut(
        _box(RAIL_WALL + 1, RAIL_SLOT_DY, RAIL_H + 0.5, x0 - 0.5, -RAIL_SLOT_DY / 2, z_slot - 0.1)
    )
    end_r = end_r.cut(
        _box(
            RAIL_WALL + 1, RAIL_SLOT_DY, RAIL_H + 0.5,
            x1 - RAIL_WALL - 0.5, -RAIL_SLOT_DY / 2, z_slot - 0.1,
        )
    )
    c = (0.40, 0.48, 0.55)
    return [
        ("Slider_Rail_Base", _keep(base, single=True), c),
        ("Slider_Rail_Wall_NegY", _keep(wall_n, single=True), (0.32, 0.58, 0.68)),
        ("Slider_Rail_Wall_PosY", _keep(wall_p, single=True), (0.32, 0.58, 0.68)),
        ("Slider_Rail_Stop_L", _keep(end_l, single=True), (0.55, 0.35, 0.25)),
        ("Slider_Rail_Stop_R", _keep(end_r, single=True), (0.55, 0.35, 0.25)),
    ]


def make_l_flap(angle_deg: float):
    App, _Part = _fc()
    px, py = _pivot_xy()
    z0 = L_Z0
    arm_large = _box(ARM_LARGE_L, L_THICK, L_H, ARM_ROOT, -L_THICK / 2, z0)
    arm_small = _box(L_THICK, ARM_SMALL_L, L_H, -L_THICK / 2, ARM_ROOT, z0)
    hub = _cyl(PIVOT_BOSS_OD - 1.2, L_H, 0, 0, z0)
    hub = hub.cut(_cyl(PIVOT_BORE, L_H + 2, 0, 0, z0 - 1))
    stub_h = ACT_Z0 - (z0 + L_H) - 0.3
    if stub_h > 0.2:
        stub = _cyl(PIVOT_D + 1.2, stub_h, 0, 0, z0 + L_H)
        stub = stub.cut(_cyl(PIVOT_BORE, stub_h + 1, 0, 0, z0 + L_H - 0.5))
        flap = arm_large.fuse(arm_small).fuse(hub).fuse(stub)
    else:
        flap = arm_large.fuse(arm_small).fuse(hub)
    flap.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), angle_deg)
    flap.translate(App.Vector(px, py, 0))
    return _keep(flap)


def make_actuator_arms(angle_deg: float):
    """
    Two perpendicular bars on the shaft:
      Arm_A (+X) length = LARGE_GROOVE_W (12)
      Arm_B (+Y) length = SMALL_GROOVE_W (5.5)
    Drive_Pin on −Y — Gap_Slider lug pushes pin → rotates both bars.
    """
    App, _Part = _fc()
    px, py = _pivot_xy()
    z0 = ACT_Z0
    disc = _cyl(5.5, 1.0, 0, 0, z0 - 0.15)
    disc = disc.cut(_cyl(PIVOT_BORE, 3, 0, 0, z0 - 1))
    arm_a = _box(ACT_ARM_A_L, ACT_ARM_W, ACT_ARM_H, 0.5, -ACT_ARM_W / 2, z0)
    arm_b = _box(ACT_ARM_W, ACT_ARM_B_L, ACT_ARM_H, -ACT_ARM_W / 2, 0.5, z0)
    pad_a = _box(2.2, ACT_ARM_W + 1.2, ACT_ARM_H, ACT_ARM_A_L - 1.8, -(ACT_ARM_W + 1.2) / 2, z0)
    pad_b = _box(ACT_ARM_W + 1.2, 2.0, ACT_ARM_H, -(ACT_ARM_W + 1.2) / 2, ACT_ARM_B_L - 1.5, z0)
    # Drive stub + pin (−Y) so Gap_Slider can push the whole cross
    stub = _box(ACT_ARM_W, max(1.0, DRIVE_PIN_R - 0.5), ACT_ARM_H, -ACT_ARM_W / 2, -DRIVE_PIN_R + 0.5, z0)
    pin = _cyl(DRIVE_PIN_D, 3.2, 0.0, -DRIVE_PIN_R, ACT_Z0 + ACT_ARM_H - 0.2)
    # Tip pins on both bars (visible push targets / secondary contact)
    tip_a = _cyl(DRIVE_PIN_D * 0.85, 2.8, ACT_ARM_A_L - 1.0, 0.0, ACT_Z0 + ACT_ARM_H - 0.15)
    tip_b = _cyl(DRIVE_PIN_D * 0.85, 2.8, 0.0, ACT_ARM_B_L - 0.8, ACT_Z0 + ACT_ARM_H - 0.15)
    cross = (
        disc.fuse(arm_a).fuse(arm_b).fuse(pad_a).fuse(pad_b)
        .fuse(stub).fuse(pin).fuse(tip_a).fuse(tip_b)
    )
    cross.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), angle_deg)
    cross.translate(App.Vector(px, py, 0))
    return [("Actuator_Cross", _keep(cross), (0.95, 0.50, 0.12))]


def make_gap_slider(open_mm: float):
    open_mm = max(OPEN_SMALL_LO, min(float(open_mm), OPEN_LARGE_HI + 1.0))
    x_left = slider_x_left(open_mm)
    y0 = SLIDER_Y - SLIDER_T / 2
    z0 = SLIDER_Z0  # fixed — rides on Slider_Rail base top

    bar = _box(SLIDER_LEN, SLIDER_T, SLIDER_H, x_left, y0, z0)
    grip = _box(12.0, SLIDER_T + 1.5, 2.0, x_left + SLIDER_LEN - 14.0, y0 - 0.75, z0 + SLIDER_H - 0.3)

    # Shoes slightly narrower than slot — guide inside Slider_Rail walls
    shoe_dy = SLIDER_T - 2.0 * RAIL_SLOT_CLEAR + 0.1
    shoe_h = SLIDER_H - 0.2
    shoe_l = _box(6.0, shoe_dy, shoe_h, x_left + 2.0, -shoe_dy / 2, z0)
    shoe_r = _box(6.0, shoe_dy, shoe_h, x_left + SLIDER_LEN - 8.0, -shoe_dy / 2, z0)

    xa, xb = lug_world_x(open_mm)
    jaw_z = YOKE_H_Z0
    jaw_h = (z0 + 0.3) - jaw_z
    ly = -DRIVE_PIN_R - LUG_DRIVE_T / 2
    jaw_drive = _box(LUG_DRIVE_W, LUG_DRIVE_T, jaw_h, xb, ly, jaw_z)
    # Bridge +Y from jaw to bar so drive lug stays attached (not dropped by boolean)
    stem_d = _box(
        LUG_DRIVE_W - 0.4,
        (y0 + SLIDER_T) - ly,
        max(2.0, z0 - (ACT_Z0 + ACT_ARM_H) + 0.5),
        xb + 0.2,
        ly,
        ACT_Z0 + ACT_ARM_H,
    )
    _ = xa

    aperture = make_aperture_plate(open_mm)

    fused = (
        bar.fuse(grip).fuse(shoe_l).fuse(shoe_r).fuse(jaw_drive).fuse(stem_d).fuse(aperture)
    )
    # Keep bar+aperture+lug — never discard disconnected solids
    return _keep(fused)


def make_pivot_pin():
    px, py = _pivot_xy()
    z0 = FLOOR_T - 1.0
    h = SLIDER_Z0 - z0 - 0.5
    pin = _cyl(PIVOT_D, h, px, py, z0)
    head = _cyl(5.0, 1.2, px, py, z0)
    return _keep(pin.fuse(head))


def make_lane_labels_proxy():
    g = groove_x_bounds()
    z0 = FLOOR_T + 0.4
    small = _box(SMALL_GROOVE_W - 0.5, GROOVE_LEN - 4, 1.5, g["small_x0"] + 0.25, -GROOVE_LEN + 1, z0)
    large = _box(LARGE_GROOVE_W - 0.5, GROOVE_LEN - 4, 1.5, g["large_x0"] + 0.25, -GROOVE_LEN + 1, z0)
    inlet = _box(
        g["large_x1"] - g["small_x0"] - 0.6,
        6.0,
        min(PILL_CLEAR_H - 1.0, L_Z0 - FLOOR_T - 0.5),
        g["small_x0"] + 0.3,
        2.0,
        FLOOR_T + 0.3,
    )
    return [
        ("Lane_Fill_Small_5p5", small, (0.30, 0.75, 0.95)),
        ("Lane_Fill_Large_12", large, (0.95, 0.55, 0.22)),
        ("Inlet_Pill_Passage", inlet, (0.45, 0.90, 0.55)),
    ]


def common_volume(a, b) -> float:
    try:
        inter = a.common(b)
        if inter is None or not getattr(inter, "Solids", None):
            return 0.0
        return float(sum(abs(s.Volume) for s in inter.Solids))
    except Exception:
        return 0.0


def _rail_walls_union():
    """Side walls + end stops only (base seating contact is allowed)."""
    parts = make_slider_rail_parts()
    by = {n: s for n, s, _c in parts}
    walls = by["Slider_Rail_Wall_NegY"].fuse(by["Slider_Rail_Wall_PosY"])
    walls = walls.fuse(by["Slider_Rail_Stop_L"]).fuse(by["Slider_Rail_Stop_R"])
    return _keep(walls)


def _slider_bar_probe(open_mm: float):
    """Bar+shoes only — the part that must stay in the rail slot."""
    x_left = slider_x_left(open_mm)
    y0 = SLIDER_Y - SLIDER_T / 2
    z0 = SLIDER_Z0
    bar = _box(SLIDER_LEN, SLIDER_T, SLIDER_H, x_left, y0, z0)
    shoe_dy = SLIDER_T - 2.0 * RAIL_SLOT_CLEAR + 0.1
    shoe_h = SLIDER_H - 0.2
    shoe_l = _box(6.0, shoe_dy, shoe_h, x_left + 2.0, -shoe_dy / 2, z0)
    shoe_r = _box(6.0, shoe_dy, shoe_h, x_left + SLIDER_LEN - 8.0, -shoe_dy / 2, z0)
    return _keep(bar.fuse(shoe_l).fuse(shoe_r))


def verify_mechanism(opens: list[float] | None = None) -> dict:
    """Kinematic + solid clearance checks while Gap_Slider travels (freecadcmd)."""
    if opens is None:
        # Dense travel sweep: small → transit → large
        n = 13
        opens = [
            OPEN_SMALL_LO + (OPEN_LARGE_HI - OPEN_SMALL_LO) * i / (n - 1)
            for i in range(n)
        ]
    rows = []
    max_overlap = 0.0
    max_illegal = 0.0
    aperture_ok = True
    state_ok = True
    rail_seat_ok = True
    jam_hits = 0

    frame = make_divert_frame()
    rail_walls = _rail_walls_union()
    rail_base = make_slider_rail_parts()[0][1]
    base_zmax = float(rail_base.BoundBox.ZMax)

    for op in opens:
        state = flap_state_for_open(op)
        ang = flap_angle_for_open(op)
        aw = aperture_widths(op)
        flap = make_l_flap(ang)
        cross = make_actuator_arms(ang)[0][1]
        slider = make_gap_slider(op)
        bar = _slider_bar_probe(op)
        aperture = make_aperture_plate(op)
        x_left = slider_x_left(op)
        xb = x_left + LUG_DRIVE_REL
        lug = _box(
            LUG_DRIVE_W, LUG_DRIVE_T, SLIDER_Z0 - YOKE_H_Z0 + 0.5,
            xb, -DRIVE_PIN_R - LUG_DRIVE_T / 2, YOKE_H_Z0,
        )

        ov_af = common_volume(aperture, frame)
        ov_afl = common_volume(aperture, flap)
        ov_lf = common_volume(lug, frame)
        ov_lfl = common_volume(lug, flap)
        ov_lc = common_volume(lug, cross)
        ov_sf = common_volume(slider, frame)
        ov_sfl = common_volume(slider, flap)
        ov_sc = common_volume(slider, cross)
        ov_sw = common_volume(bar, rail_walls)

        in_transit = OPEN_TRANSIT_LO - 0.5 <= op <= OPEN_TRANSIT_HI + 0.5
        # Intentional drive contact in transit — not a jam
        ov_lc_ill = 0.0 if in_transit else ov_lc
        ov_sc_ill = 0.0 if in_transit else ov_sc

        illegal = max(ov_af, ov_afl, ov_lf, ov_lfl, ov_lc_ill, ov_sf, ov_sfl, ov_sc_ill, ov_sw)
        max_illegal = max(max_illegal, illegal)
        max_overlap = max(max_overlap, illegal, ov_lc, ov_sc)
        if illegal >= 5.0:
            jam_hits += 1

        # Bar must sit on rail base and stay inside slot Y
        bb = bar.BoundBox
        seat_gap = abs(float(bb.ZMin) - base_zmax)
        slot_y0 = -RAIL_SLOT_DY / 2.0
        slot_y1 = RAIL_SLOT_DY / 2.0
        in_slot_y = bb.YMin >= slot_y0 - 0.05 and bb.YMax <= slot_y1 + 0.05
        on_rail_x = bb.XMin >= RAIL_X0 - 0.5 and bb.XMax <= RAIL_X1 + 0.5
        if seat_gap > 0.25 or not in_slot_y or not on_rail_x:
            rail_seat_ok = False

        if state == "SMALL":
            if aw["small_mm"] < 0.5 and op >= OPEN_SMALL_LO + 0.2:
                aperture_ok = False
            if abs(ang - FLAP_ANGLE_SMALL) > 1.0 and op <= OPEN_TRANSIT_LO:
                state_ok = False
        else:
            if op >= OPEN_LARGE_LO and aw["large_mm"] < 0.5 and op > OPEN_LARGE_LO + 0.5:
                aperture_ok = False
            if abs(ang - FLAP_ANGLE_LARGE) > 1.0 and op >= OPEN_TRANSIT_HI:
                state_ok = False

        rows.append({
            "open_mm": round(op, 3),
            "state": state,
            "flap_deg": round(ang, 2),
            "aperture": aw,
            "overlap_aperture_frame": round(ov_af, 3),
            "overlap_aperture_flap": round(ov_afl, 3),
            "overlap_lug_frame": round(ov_lf, 3),
            "overlap_lug_flap": round(ov_lfl, 3),
            "overlap_lug_cross": round(ov_lc, 3),
            "overlap_slider_frame": round(ov_sf, 3),
            "overlap_slider_flap": round(ov_sfl, 3),
            "overlap_slider_cross": round(ov_sc, 3),
            "overlap_bar_rail_walls": round(ov_sw, 3),
            "illegal_mm3": round(illegal, 3),
            "bar_zmin": round(float(bb.ZMin), 3),
            "rail_base_zmax": round(base_zmax, 3),
            "in_slot_y": in_slot_y,
            "on_rail_x": on_rail_x,
        })

    # Width progression checks
    w1 = aperture_widths(OPEN_SMALL_LO)["small_mm"]
    w5 = aperture_widths(OPEN_SMALL_HI)["small_mm"]
    wl0 = aperture_widths(OPEN_LARGE_LO)["large_mm"]
    wl1 = aperture_widths(OPEN_LARGE_HI)["large_mm"]
    width_progress = (
        w1 < w5 - 0.5
        and abs(w5 - SMALL_GROOVE_W) < 0.35
        and wl1 > wl0 + 2.0
        and abs(wl1 - LARGE_GROOVE_W) < 0.35
    )

    passed = bool(
        aperture_ok
        and state_ok
        and width_progress
        and max_illegal < 5.0
        and jam_hits == 0
        and rail_seat_ok
    )
    return {
        "pass": passed,
        "max_overlap_mm3": round(max_overlap, 3),
        "max_illegal_mm3": round(max_illegal, 3),
        "jam_hits": jam_hits,
        "rail_seat_ok": rail_seat_ok,
        "width_progress": width_progress,
        "small_widths": [w1, w5],
        "large_widths": [wl0, wl1],
        "open_bands": {
            "small": [OPEN_SMALL_LO, OPEN_SMALL_HI],
            "transit": [OPEN_TRANSIT_LO, OPEN_TRANSIT_HI],
            "large": [OPEN_LARGE_LO, OPEN_LARGE_HI],
        },
        "samples": rows,
    }


def build_l_flap_divert_parts(
    slider_open_mm: float = 3.0,
    prev_state: str | None = None,
):
    state = flap_state_for_open(slider_open_mm, prev_state)
    ang = flap_angle_for_open(slider_open_mm)
    aw = aperture_widths(slider_open_mm)

    parts = [
        ("Divert_Frame", make_divert_frame(), (0.55, 0.58, 0.62)),
        ("L_Flap", make_l_flap(ang), (0.20, 0.55, 0.85)),
    ]
    parts.extend(make_actuator_arms(ang))
    parts.extend(make_slider_rail_parts())
    parts.extend(
        [
            ("Gap_Slider", make_gap_slider(slider_open_mm), (0.55, 0.25, 0.70)),
            ("Pivot_Pin", make_pivot_pin(), (0.40, 0.40, 0.45)),
        ]
    )
    parts.extend(make_lane_labels_proxy())

    print(
        "Grooves: small=%.1f large=%.1f | arms A=%.1f B=%.1f | rail [%.1f..%.1f] | "
        "bands S[%.1f..%.1f] T[%.1f..%.1f] L[%.1f..%.1f]"
        % (
            SMALL_GROOVE_W, LARGE_GROOVE_W,
            ACT_ARM_A_L, ACT_ARM_B_L,
            RAIL_X0, RAIL_X1,
            OPEN_SMALL_LO, OPEN_SMALL_HI,
            OPEN_TRANSIT_LO, OPEN_TRANSIT_HI,
            OPEN_LARGE_LO, OPEN_LARGE_HI,
        )
    )
    print(
        "L_Flap_Divert: open=%.2f mm | state=%s | flap=%.1f deg | "
        "aperture small=%.2f large=%.2f active=%.2f | travel=%.1f mm"
        % (
            slider_open_mm, state, ang,
            aw["small_mm"], aw["large_mm"], aw["active_width_mm"],
            OPEN_LARGE_HI - OPEN_SMALL_LO,
        )
    )
    return parts
