"""
L-Flap Divert — parallel grooves + aperture + Maltese (Geneva) gate + rack/pinion.

Grooves: Small 5.5 mm | Large 12.0 mm, flow -Y.

Drive:
  Round knob (Z) carries an involute pinion (same spur_gear_math as Rotary_Linear)
  that meshes a rack on Gap_Slider → linear open_mm.

Gate:
  Two arms at 90° (lengths = groove widths).
  Closed = arm across groove; open = swings INWARD and nests in divider pocket
  (sát thành máng). 1-slot Geneva indexes 90° once/dir; knob turns 90° (α=45°).
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
THRESHOLD_MM = 5.5
LUG_A_TRIP = 5.55
LUG_B_TRIP = 5.45
# Arms at 90°: park0 large-arm blocks large (+X); park1 large-arm nests on +Y divider
MALTA_ARM_ANGLE_DEG = 90.0
MALTA_ANGLE_SMALL = 0.0   # large arm across large groove (closed large)
MALTA_ANGLE_LARGE = 90.0  # large arm along +Y into divider (open large, inward)

# ---- grooves ----
SMALL_GROOVE_W = 5.5
LARGE_GROOVE_W = 12.0
DIVIDER_T = 2.0
GROOVE_LEN = 45.0
INLET_L = 22.0
CLEAR = 0.4

# ---- frame / pivot (Malta) ----
WALL_T = 2.5
WALL_H = 22.0
FLOOR_T = 2.0
PIVOT_D = 3.0
PIVOT_BORE = 3.3
PIVOT_BOSS_OD = 8.0
PIVOT_BOSS_H = 3.5
PIVOT_AXIAL_GAP = 0.5

MALTA_T = 2.0
MALTA_Z0 = FLOOR_T + PIVOT_BOSS_H + PIVOT_AXIAL_GAP
MALTA_H = 12.0
ARM_ROOT = DIVIDER_T / 2.0 + CLEAR
# Arm lengths = groove widths → flush with divider walls when parked
ARM_LARGE_L = LARGE_GROOVE_W
ARM_SMALL_L = SMALL_GROOVE_W

# Rack / pinion — small ring, circular pitch ≈ 1 mm for fine slider steps
# p = π·m = 1.0 mm ⇒ one tooth advance ≈ 1 mm on Gap_Slider
GEAR_MODULE = 1.0 / math.pi  # ≈ 0.3183
PINION_TEETH = 16  # compact Ø; travel/turn = π·m·z = 16.0 mm
PINION_FACE = 5.0
TOOTH_CLEAR = 0.15  # scaled for fine module (was 0.40 @ m=1)
CENTER_BACKLASH = 0.20
PRESSURE_ANGLE = 20.0
_PINION_PITCH_R = 0.5 * GEAR_MODULE * PINION_TEETH  # ≈ 2.55

SLIDER_Y = 0.0
SLIDER_T = 4.0
SLIDER_H = 4.0
SLIDER_LEN = 70.0

# Geneva + knob axis: −X of Malta, −Y so pinion meshes bar −Y face
KNOB_X = -18.0
KNOB_Y = -(SLIDER_T / 2.0 + CENTER_BACKLASH + _PINION_PITCH_R)  # ≈ -4.75
GENEVA_A = math.hypot(KNOB_X, KNOB_Y)  # center distance knob→Malta
#
# Gate throw 90° (closed across groove → open inward against divider).
# Drive packing stays classic α=45°; knob turns 90° (=2α) while Malta sweeps 90°.
#
GENEVA_ALPHA_DEG = 45.0
GENEVA_DRIVE_DEG = 2.0 * GENEVA_ALPHA_DEG  # 90° knob during index
N_DRIVE_SLOTS = 1
N_GENEVA_SLOTS = N_DRIVE_SLOTS
N_LOCK_ARCS = 2  # parks at SMALL and LARGE only
MALTA_INDEX_DEG = MALTA_ANGLE_LARGE - MALTA_ANGLE_SMALL  # 90° malta throw
# Divider pocket: open door nests here (sát thành), arm along +Y
DOOR_POCKET_CLEAR = 0.35
DOOR_POCKET_EXTRA_L = 1.0  # beyond arm tip
MALTA_HUB_R = 7.8  # lower gate boss (groove fit)
DRIVE_PIN_R = GENEVA_A * math.sin(math.radians(GENEVA_ALPHA_DEG))
MALTA_DISK_R = GENEVA_A * math.cos(math.radians(GENEVA_ALPHA_DEG))
LOCK_DISC_R = GENEVA_A - MALTA_DISK_R  # a(1−cos α)
LOCK_CLEAR = 0.35
LOCK_WING_R = MALTA_DISK_R + 1.2
DRIVER_R = max(3.5, LOCK_DISC_R * 0.55)
SLOT_W = 3.6
DRIVE_PIN_D = 3.0
_SLOT_FACE0 = 90.0
SLOT_PHASE_DEG = (
    math.degrees(math.atan2(KNOB_Y, KNOB_X))
    + GENEVA_ALPHA_DEG
    - _SLOT_FACE0
    - MALTA_ANGLE_SMALL
)
GATE_H = 7.0
GENEVA_DISK_H = 4.0
GENEVA_Z0 = MALTA_Z0 + GATE_H + 0.4
GENEVA_H = GENEVA_DISK_H
MALTA_H = GATE_H + 0.4 + GENEVA_DISK_H
# Video stack (Z↑): pinion → large gear disc → small lock disc → hand knob
# Large disc OD ≈ pin circle (≈ Maltese OD) — tỉ lệ đĩa dẫn như video
GEAR_DISC_R = DRIVE_PIN_R + 0.6
GEAR_DISC_H = 3.2
GEAR_DISC_Z0 = GENEVA_Z0 - GEAR_DISC_H - 0.25
PINION_Z0 = GEAR_DISC_Z0 - PINION_FACE
SLIDER_Z0 = PINION_Z0
KNOB_Z0 = GENEVA_Z0 + GENEVA_H + 1.5
KNOB_H = 9.0
KNOB_OD = 18.0  # núm tay (không phải đĩa Geneva)
KNOB_BORE = 3.2
# Short guide chutes: same X as small/large grooves; feed pills into divert.
# Under-arm height clears GATE sweep; +Y mouths sit outside tip keepout circle.
GUIDE_CHUTE_INLET_L = 8.0  # short inlet mouths
GUIDE_CHUTE_WALL_T = 1.2
GUIDE_CHUTE_UNDER_CLEAR = CLEAR  # below Malta arms
GUIDE_CHUTE_TIP_CLEAR = CLEAR  # radial gap to arm tip circle
PILL_CLEAR_H = MALTA_Z0 - FLOOR_T - 0.5
SLIDER_X0_AT_OPEN0 = -20.0

# Slider travel = width of small + large grooves only
SLIDER_TRAVEL_MM = SMALL_GROOVE_W + LARGE_GROOVE_W  # 17.5
OPEN_SMALL_LO = 0.0
OPEN_SMALL_HI = SMALL_GROOVE_W  # = THRESHOLD_MM
OPEN_TRANSIT_LO = THRESHOLD_MM
_TRAVEL_PER_TURN = math.pi * GEAR_MODULE * PINION_TEETH
# Knob turns GENEVA_DRIVE_DEG (90°) while Malta indexes MALTA_INDEX_DEG (90°)
GENEVA_INDEX_OPEN_MM = _TRAVEL_PER_TURN * (GENEVA_DRIVE_DEG / 360.0)
OPEN_TRANSIT_HI = THRESHOLD_MM + GENEVA_INDEX_OPEN_MM
OPEN_LARGE_LO = OPEN_TRANSIT_HI
OPEN_LARGE_HI = SLIDER_TRAVEL_MM
OPEN_DRIVE_LO = OPEN_SMALL_LO
OPEN_DRIVE_HI = OPEN_LARGE_HI
if OPEN_TRANSIT_HI > OPEN_LARGE_HI - 0.15:
    raise ValueError(
        "Geneva index travel %.2f mm does not fit in slider span %.2f mm "
        "(SMALL+LARGE); reduce PINION_TEETH/module"
        % (GENEVA_INDEX_OPEN_MM, SLIDER_TRAVEL_MM - THRESHOLD_MM)
    )

# Continuous U-rail under Gap_Slider bar
RAIL_MARGIN = 8.0
RAIL_X0 = SLIDER_X0_AT_OPEN0 + OPEN_SMALL_LO - RAIL_MARGIN
RAIL_X1 = SLIDER_X0_AT_OPEN0 + OPEN_LARGE_HI + SLIDER_LEN + RAIL_MARGIN
RAIL_BASE_T = 1.5
RAIL_SLOT_CLEAR = 0.35
RAIL_SLOT_DY = SLIDER_T + 2.0 * RAIL_SLOT_CLEAR
RAIL_WALL = 2.0
RAIL_OUTER_DY = RAIL_SLOT_DY + 2.0 * RAIL_WALL
RAIL_H = SLIDER_H + 2.5
RAIL_Z0 = SLIDER_Z0 - RAIL_BASE_T

APERTURE_MIN = 1.2
APERTURE_Y0 = 14.0
APERTURE_Y1 = 20.0
APERTURE_Z0 = FLOOR_T + 0.4
APERTURE_Z1 = MALTA_Z0 + MALTA_H * 0.55

_g_half = DIVIDER_T / 2.0
_SMALL_X0 = -_g_half - SMALL_GROOVE_W
_SMALL_X1 = -_g_half
_LARGE_X0 = _g_half
_LARGE_X1 = _g_half + LARGE_GROOVE_W
WIN_SMALL_W = SMALL_GROOVE_W
WIN_SMALL_REL = _SMALL_X0 - SLIDER_X0_AT_OPEN0 - OPEN_SMALL_HI
WIN_LARGE_W = LARGE_GROOVE_W
WIN_LARGE_REL = _LARGE_X0 - SLIDER_X0_AT_OPEN0 - OPEN_LARGE_HI

# Legacy aliases (sim / older imports)
L_Z0 = MALTA_Z0
L_H = MALTA_H
L_THICK = MALTA_T
FLAP_ANGLE_SMALL = MALTA_ANGLE_SMALL
FLAP_ANGLE_LARGE = MALTA_ANGLE_LARGE
ACT_Z0 = GENEVA_Z0
ACT_ARM_H = GENEVA_H
ACT_ARM_W = 2.4
ACT_ARM_A_L = ARM_LARGE_L
ACT_ARM_B_L = ARM_SMALL_L
DRIVE_PIN_R_LEGACY = DRIVE_PIN_R  # noqa: N816 — name kept for sim stubs
# Compat aliases for older sim imports
DRIVE_PIN_R = DRIVE_PIN_R  # geneva pin radius (re-export)
YOKE_H_Z0 = GENEVA_Z0
LUG_DRIVE_W = 2.5
LUG_DRIVE_T = 3.2


def lug_world_x(open_mm: float) -> tuple[float, float]:
    """Deprecated Scotch-yoke helper — parked; Geneva replaces lug drive."""
    x = slider_x_left(open_mm) + SLIDER_LEN * 0.5
    return (x + 50.0, x)


def _gear():
    from rotary_linear import spur_gear_math  # noqa: PLC0415

    return spur_gear_math(
        GEAR_MODULE,
        PINION_TEETH,
        alpha_deg=PRESSURE_ANGLE,
        tooth_clear=TOOTH_CLEAR,
        min_teeth=PINION_TEETH,  # allow compact z for groove-limited travel
    )


def travel_per_turn() -> float:
    return float(_gear()["travel_per_turn"])


def knob_angle_deg(open_mm: float) -> float:
    """Knob rotation from open_mm via rack pitch circumference."""
    # Use closed-form pitch travel (same as spur_gear_math) — no FreeCAD import.
    return (float(open_mm) - OPEN_SMALL_LO) / max(1e-6, _TRAVEL_PER_TURN) * 360.0


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
    return MALTA_ANGLE_LARGE if state == "LARGE" else MALTA_ANGLE_SMALL


def slider_x_left(open_mm: float) -> float:
    return SLIDER_X0_AT_OPEN0 + float(clamp_open(open_mm))


def clamp_open(open_mm: float) -> float:
    """Hard limit: slider only travels across small+large groove widths."""
    return max(OPEN_DRIVE_LO, min(float(open_mm), OPEN_DRIVE_HI))


def _geneva_psi_deg(open_mm: float) -> float:
    """Driver angle from line-of-centres during transit: −α … +α."""
    if open_mm <= OPEN_TRANSIT_LO:
        return -GENEVA_ALPHA_DEG
    if open_mm >= OPEN_TRANSIT_HI:
        return +GENEVA_ALPHA_DEG
    t = (open_mm - OPEN_TRANSIT_LO) / max(1e-6, OPEN_TRANSIT_HI - OPEN_TRANSIT_LO)
    return -GENEVA_ALPHA_DEG + t * (2.0 * GENEVA_ALPHA_DEG)


def _geneva_driven_phi_rad(psi_rad: float) -> float:
    """Classic external Geneva: driven φ vs driver ψ (pin radius = a·sin α)."""
    a = GENEVA_A
    r = DRIVE_PIN_R
    return math.atan2(math.sin(psi_rad), (a / r) - math.cos(psi_rad))


def malta_angle_for_open(slider_open_mm: float) -> float:
    """
    SMALL @ ≤TRANSIT_LO; LARGE @ ≥TRANSIT_HI; sweep 90° during transit
    while knob turns 90° (α=45° drive geometry).
    """
    if slider_open_mm <= OPEN_TRANSIT_LO:
        return MALTA_ANGLE_SMALL
    if slider_open_mm >= OPEN_TRANSIT_HI:
        return MALTA_ANGLE_LARGE
    t = (slider_open_mm - OPEN_TRANSIT_LO) / max(1e-6, OPEN_TRANSIT_HI - OPEN_TRANSIT_LO)
    # Smoothstep — reversible
    t = t * t * (3.0 - 2.0 * t)
    return MALTA_ANGLE_SMALL + t * (MALTA_ANGLE_LARGE - MALTA_ANGLE_SMALL)


def _driver_world_angle_deg(open_mm: float) -> float:
    """Absolute Z rotation of driver/knob: pin at aim+ψ (ψ=−α at TRANSIT_LO)."""
    aim = _bearing_to_malta_deg()
    psi = _geneva_psi_deg(open_mm)
    # Outside transit, continue with knob beyond ±α (dwell / multi-turn)
    if OPEN_TRANSIT_LO < open_mm < OPEN_TRANSIT_HI:
        return aim + psi
    ang = knob_angle_deg(open_mm)
    engage0 = knob_angle_deg(OPEN_TRANSIT_LO)
    # At LO: aim − α; elsewhere: same offset + (knob − engage0)
    return aim - GENEVA_ALPHA_DEG + (ang - engage0)


def flap_angle_for_open(slider_open_mm: float) -> float:
    return malta_angle_for_open(slider_open_mm)


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


def malta_slider_keepout_r() -> float:
    """World radius that clears Malta arms/hub through the Gap_Slider Y strip."""
    return guide_chute_keepout_r() + 1.2  # ≈ 14 mm


def _malta_travel_slot_cutter(x_left: float):
    """
    Elongated keepout fixed to the slider body so Malta stays clear over full travel.
    Local pivot x on the bar sweeps [ -x_left(max), -x_left(min) ] = [2.5, 20] mm.
    Y limited to the Gap_Slider corridor (do not nibble the aperture plate at +Y).
    """
    r = malta_slider_keepout_r()
    loc_lo = -SLIDER_X0_AT_OPEN0 - OPEN_DRIVE_HI  # at max open
    loc_hi = -SLIDER_X0_AT_OPEN0 - OPEN_DRIVE_LO  # at rest
    slot_x0 = x_left + loc_lo - r
    slot_x1 = x_left + loc_hi + r
    y0 = SLIDER_Y - SLIDER_T / 2.0 - 2.0
    y1 = SLIDER_Y + SLIDER_T / 2.0 + 2.0
    z0 = min(SLIDER_Z0, MALTA_Z0) - 1.0
    z1 = MALTA_Z0 + GATE_H + 3.0
    return _box(slot_x1 - slot_x0, y1 - y0, z1 - z0, slot_x0, y0, z0)


def make_aperture_plate(open_mm: float):
    g = groove_x_bounds()
    x_left = slider_x_left(open_mm)
    plate_x0 = g["outer_x0"] + WALL_T + CLEAR
    plate_x1 = g["outer_x1"] - WALL_T - CLEAR
    z0, z1 = APERTURE_Z0, APERTURE_Z1
    y0, y1 = APERTURE_Y0, APERTURE_Y1
    plate = _box(plate_x1 - plate_x0, y1 - y0, z1 - z0, plate_x0, y0, z0)

    wins = aperture_windows(open_mm)
    for a0, a1 in (wins["small"], wins["large"]):
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

    # Link plate → Gap_Slider ABOVE Malta gate; stem stays outside tip keepout
    r_ko = malta_slider_keepout_r()
    stem_w = 12.0
    stem_x0 = max(
        r_ko + 1.0,
        min(max(x_left + SLIDER_LEN * 0.55, plate_x0 + 2), plate_x1 - stem_w - 2),
    )
    z_over = MALTA_Z0 + GATE_H + 0.8  # clear of gate arms
    post = _box(stem_w, 2.5, max(1.0, (SLIDER_Z0 + SLIDER_H) - z_over), stem_x0, y0 + 0.5, z_over)
    bar_y0 = SLIDER_Y - SLIDER_T / 2.0
    bridge_dy = (y0 + 0.5) - bar_y0 + 0.8
    bridge = _box(stem_w, bridge_dy, 2.6, stem_x0, bar_y0 - 0.3, z_over)
    drop_h = z_over - (SLIDER_Z0 - 0.2)
    drop = _box(stem_w, SLIDER_T + 0.4, max(0.8, drop_h), stem_x0, bar_y0 - 0.2, SLIDER_Z0 - 0.2)
    body = plate.fuse(post).fuse(bridge).fuse(drop)
    return _keep(body)


def _pivot_xy():
    return (0.0, 0.0)


def _knob_xy():
    return (KNOB_X, KNOB_Y)


def make_divert_frame():
    g = groove_x_bounds()
    y_out = -GROOVE_LEN
    App, Part = _fc()

    floor = _box(
        g["outer_x1"] - g["outer_x0"] + 20.0,
        GROOVE_LEN + INLET_L + 28.0,
        FLOOR_T,
        g["outer_x0"] - 10.0,
        y_out - 8.0,
        0.0,
    )
    # Extend floor under knob
    floor = _fuse(
        floor,
        _box(36.0, 28.0, FLOOR_T, KNOB_X - 18.0, KNOB_Y - 16.0, 0.0),
        single=True,
    )

    wall_l = _box(WALL_T, GROOVE_LEN + INLET_L, WALL_H, g["outer_x0"], y_out, FLOOR_T)
    wall_r = _box(WALL_T, GROOVE_LEN + INLET_L, WALL_H, g["outer_x1"] - WALL_T, y_out, FLOOR_T)

    # Travel windows for Gap_Slider bar
    win_y0 = SLIDER_Y - SLIDER_T / 2 - 1.5
    win_y1 = SLIDER_Y + SLIDER_T / 2 + 1.5
    win_z0 = SLIDER_Z0 - 2.0
    win_z1 = SLIDER_Z0 + SLIDER_H + 2.0
    for wx0, wx1 in (
        (g["outer_x0"] - 8.0, g["outer_x0"] + WALL_T + 1.0),
        (g["outer_x1"] - WALL_T - 1.0, g["outer_x1"] + 8.0),
    ):
        cutter = _box(wx1 - wx0, win_y1 - win_y0, win_z1 - win_z0, wx0, win_y0, win_z0)
        wall_l = wall_l.cut(cutter)
        wall_r = wall_r.cut(cutter)

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

    div_y1 = -PIVOT_BOSS_OD / 2.0 - CLEAR
    div_h = min(WALL_H, GENEVA_Z0 - FLOOR_T - CLEAR)
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

    # Open-door pocket: arm along +Y nests into divider (mở vào trong, sát thành)
    pocket_y0 = ARM_ROOT - 0.4
    pocket_len = ARM_ROOT + ARM_LARGE_L + DOOR_POCKET_EXTRA_L - pocket_y0
    pocket_w = DIVIDER_T + 2.0 * DOOR_POCKET_CLEAR
    pocket_z0 = MALTA_Z0 - 0.15
    pocket_h = GATE_H + 0.5
    try:
        divider = divider.cut(
            _box(
                pocket_w,
                max(1.0, pocket_len),
                pocket_h,
                -pocket_w / 2.0,
                pocket_y0,
                pocket_z0,
            )
        )
    except Exception:
        pass
    # +Y inlet-side divider extension with same pocket (door sits past boss)
    inlet_div_y1 = ARM_ROOT + ARM_LARGE_L + DOOR_POCKET_EXTRA_L
    inlet_div_door = _box(
        DIVIDER_T,
        max(1.0, inlet_div_y1 - 1.0),
        min(div_h, MALTA_Z0 + GATE_H - FLOOR_T),
        -DIVIDER_T / 2.0,
        1.0,
        FLOOR_T,
    )
    try:
        inlet_div_door = inlet_div_door.cut(
            _box(
                pocket_w,
                max(1.0, pocket_len),
                pocket_h,
                -pocket_w / 2.0,
                pocket_y0,
                pocket_z0,
            )
        )
    except Exception:
        pass

    dir_h = max(1.0, min(MALTA_Z0 - FLOOR_T - CLEAR, PILL_CLEAR_H - 1.0))
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

    # Knob shaft boss
    kx, ky = _knob_xy()
    knob_boss = _cyl(10.0, PIVOT_BOSS_H + 1.0, kx, ky, FLOOR_T)
    knob_boss = knob_boss.cut(_cyl(KNOB_BORE + 0.4, PIVOT_BOSS_H + 3, kx, ky, FLOOR_T - 0.5))

    # Angle stops: closed across large (+X) and open nested on +Y divider
    stop_h = MALTA_H * 0.45
    stop_z = MALTA_Z0 + 2.0
    stop_small = _box(
        1.8, 1.8, stop_h,
        ARM_ROOT + ARM_LARGE_L - 0.8, -MALTA_T - 2.0, stop_z,
    )
    stop_large = _box(
        1.8, 1.8, stop_h,
        -MALTA_T - 2.0, ARM_ROOT + ARM_LARGE_L - 0.8, stop_z,
    )

    body = floor
    for p in (
        wall_l,
        wall_r,
        divider,
        inlet_div,
        inlet_div_door,
        end_wall,
        post_s,
        knob_boss,
        stop_small,
        stop_large,
    ):
        body = _fuse(body, p, single=True)

    pocket = _cyl(PIVOT_BOSS_OD + 1.0, MALTA_H + 1.0, px, py, MALTA_Z0 - 0.3)
    try:
        body = body.cut(pocket)
    except Exception:
        pass
    body = _fuse(body, post_s, single=True)

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

    # Clearance for Geneva pin orbit + Malta lock-wing + large gear disc
    try:
        body = body.cut(
            _cyl(LOCK_WING_R * 2.0 + 4.0, MALTA_H + 2.0, px, py, MALTA_Z0 - 0.5)
        )
        clear_d = 2.0 * (DRIVE_PIN_R + DRIVE_PIN_D + 3.0)
        body = body.cut(_cyl(clear_d, GENEVA_H + 10.0, kx, ky, GENEVA_Z0 - 3.0))
        body = body.cut(
            _cyl(GEAR_DISC_R * 2.0 + 6.0, MALTA_H + KNOB_H + 8.0, kx, ky, PINION_Z0 - 1.0)
        )
    except Exception:
        pass
    return _keep(body, single=True)


def make_slider_rail_parts():
    x0, x1 = RAIL_X0, RAIL_X1
    dx = x1 - x0
    y_out0 = -RAIL_OUTER_DY / 2.0
    z0 = RAIL_Z0
    z_slot = z0 + RAIL_BASE_T
    base = _box(dx, RAIL_OUTER_DY, RAIL_BASE_T, x0, y_out0, z0)
    wall_n = _box(dx, RAIL_WALL, RAIL_H, x0, y_out0, z_slot)
    wall_p = _box(dx, RAIL_WALL, RAIL_H, x0, RAIL_OUTER_DY / 2.0 - RAIL_WALL, z_slot)
    end_l = _box(RAIL_WALL, RAIL_OUTER_DY, RAIL_BASE_T + RAIL_H, x0, y_out0, z0)
    end_r = _box(RAIL_WALL, RAIL_OUTER_DY, RAIL_BASE_T + RAIL_H, x1 - RAIL_WALL, y_out0, z0)
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


def _malta_cam_locus_local(n: int = 16) -> list[tuple[float, float]]:
    """
    Pin centerline in Malta body frame while indexing 90°.
    α=45° packing (knob 90°) + cam slot ⇒ Malta throw 90°.
    """
    pts = []
    for i in range(n + 1):
        t = i / n
        op = OPEN_TRANSIT_LO + t * (OPEN_TRANSIT_HI - OPEN_TRANSIT_LO)
        m = math.radians(malta_angle_for_open(op))
        px, py = _pin_world_xy(op)
        lx = px * math.cos(-m) - py * math.sin(-m)
        ly = px * math.sin(-m) + py * math.cos(-m)
        pts.append((lx, ly))
    return pts


def make_malta_cross(angle_deg: float):
    """
    Malta = wings only (no full disk):
      - 2 gate arms @ 90 deg (lengths = groove widths)
        closed: across groove; open: along +Y into divider pocket
      - 1 cam-slot finger (pin locus for 90° index)
      - 2 short lock pads with concave arcs (SMALL/LARGE)
    """
    App, Part = _fc()
    px, py = _pivot_xy()
    z0 = MALTA_Z0
    z_disk = GENEVA_Z0
    kx, ky = _knob_xy()

    boss = _cyl(PIVOT_BOSS_OD - 0.5, GATE_H, 0, 0, z0)
    boss = boss.cut(_cyl(PIVOT_BORE, GATE_H + 2, 0, 0, z0 - 1))

    arm_large = _box(ARM_LARGE_L, MALTA_T, GATE_H, ARM_ROOT, -MALTA_T / 2, z0)
    arm_small = _box(ARM_SMALL_L, MALTA_T, GATE_H, ARM_ROOT, -MALTA_T / 2, z0)
    arm_small.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), MALTA_ARM_ANGLE_DEG)

    hub_r = max(PIVOT_BOSS_OD * 0.55, 3.2)
    hub = _cyl(hub_r * 2.0, GENEVA_DISK_H, 0, 0, z_disk)
    hub = hub.cut(_cyl(PIVOT_BORE, GENEVA_DISK_H + 2, 0, 0, z_disk - 1))

    # Cam finger: ribbon along 90° pin locus, slot corridor cut through
    locus = _malta_cam_locus_local(14)
    wall = 2.2
    half_slot = SLOT_W * 0.5
    finger = None
    slot_cut = None
    for i in range(len(locus) - 1):
        x0, y0 = locus[i]
        x1, y1 = locus[i + 1]
        dx, dy = x1 - x0, y1 - y0
        seg = math.hypot(dx, dy)
        if seg < 0.25:
            continue
        yaw = math.degrees(math.atan2(dy, dx))
        mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        # Outer solid ribbon
        ribbon = _box(
            seg + 0.4,
            SLOT_W + 2.0 * wall,
            GENEVA_DISK_H,
            -seg / 2.0 - 0.2,
            -(SLOT_W / 2.0 + wall),
            z_disk,
        )
        ribbon.translate(App.Vector(mx, my, 0))
        ribbon.rotate(App.Vector(mx, my, 0), App.Vector(0, 0, 1), yaw)
        finger = ribbon if finger is None else finger.fuse(ribbon)
        # Slot void
        void = _box(
            seg + 0.6,
            SLOT_W,
            GENEVA_DISK_H + 1.4,
            -seg / 2.0 - 0.3,
            -half_slot,
            z_disk - 0.7,
        )
        void.translate(App.Vector(mx, my, 0))
        void.rotate(App.Vector(mx, my, 0), App.Vector(0, 0, 1), yaw)
        slot_cut = void if slot_cut is None else slot_cut.fuse(void)
        # Round ends
        for ex, ey in ((x0, y0), (x1, y1)):
            tip = _cyl(SLOT_W, GENEVA_DISK_H + 1.4, ex, ey, z_disk - 0.7)
            slot_cut = tip if slot_cut is None else slot_cut.fuse(tip)
    if finger is not None and slot_cut is not None:
        try:
            finger = finger.cut(slot_cut)
        except Exception:
            pass
    if finger is None:
        # Fallback radial finger
        finger_w = SLOT_W + 2.4
        finger_len = LOCK_WING_R - hub_r + 0.8
        finger = _box(
            finger_w, finger_len, GENEVA_DISK_H,
            -finger_w / 2.0, hub_r - 0.3, z_disk,
        )
        slot = _box(
            SLOT_W, finger_len + 1.0, GENEVA_DISK_H + 1.2,
            -SLOT_W / 2.0, hub_r + 0.2, z_disk - 0.6,
        )
        try:
            finger = finger.cut(slot)
        except Exception:
            pass
        finger.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), SLOT_PHASE_DEG)

    pad_w = max(LOCK_DISC_R * 2.0, 12.0)
    pad_len = max(4.0, LOCK_WING_R - hub_r + 1.2)
    lock_pads = None
    for park in (MALTA_ANGLE_SMALL, MALTA_ANGLE_LARGE):
        # Cutter center in local frame so after malta.rotate(park) it sits on knob
        ca = math.cos(math.radians(-park))
        sa = math.sin(math.radians(-park))
        lx = ca * kx - sa * ky
        ly = sa * kx + ca * ky
        bearing = math.degrees(math.atan2(ly, lx))
        pad = _box(
            pad_w, pad_len, GENEVA_DISK_H,
            -pad_w / 2.0, hub_r - 0.4, z_disk,
        )
        # Aim +Y of pad toward (lx, ly)
        pad.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), bearing - 90.0)
        cutter = _cyl(
            (LOCK_DISC_R + LOCK_CLEAR) * 2.0,
            GENEVA_DISK_H + 2.0,
            lx, ly, z_disk - 1.0,
        )
        try:
            pad = pad.cut(cutter)
        except Exception:
            pass
        # Keep pad only if some solid remains after concave cut
        if pad is not None and getattr(pad, "Solids", None) and pad.Solids:
            lock_pads = pad if lock_pads is None else lock_pads.fuse(pad)

    stem = _cyl(PIVOT_D + 2.0, z_disk - (z0 + GATE_H) + 0.6, 0, 0, z0 + GATE_H - 0.3)
    stem = stem.cut(_cyl(PIVOT_BORE, 10, 0, 0, z0 + GATE_H - 1))

    cross = boss.fuse(arm_large).fuse(arm_small).fuse(stem).fuse(hub).fuse(finger)
    if lock_pads is not None:
        cross = cross.fuse(lock_pads)
    cross.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), angle_deg)
    cross.translate(App.Vector(px, py, 0))
    return _keep(cross)


def _bearing_to_malta_deg() -> float:
    """World angle from knob axis toward Malta pivot (deg)."""
    return math.degrees(math.atan2(-KNOB_Y, -KNOB_X))


def make_geneva_driver(open_mm: float):
    """
    Small raised lock disc (video) — hugs Malta concave arcs.
    Pin lives on the large gear disc below.
    """
    App, Part = _fc()
    kx, ky = _knob_xy()
    z0 = GENEVA_Z0

    lock = _cyl(LOCK_DISC_R * 2.0, GENEVA_H * 0.95, 0, 0, z0)
    lock = lock.cut(_cyl(KNOB_BORE, GENEVA_H + 2, 0, 0, z0 - 1))
    mouth_half_y = LOCK_DISC_R * math.tan(math.radians(GENEVA_ALPHA_DEG)) + 0.7
    mouth = _box(
        LOCK_DISC_R + 3.5,
        mouth_half_y * 2.0,
        GENEVA_H + 2.0,
        LOCK_DISC_R * 0.10,
        -mouth_half_y,
        z0 - 1.0,
    )
    try:
        lock = lock.cut(mouth)
    except Exception:
        pass

    hub = _cyl(max(DRIVER_R, LOCK_DISC_R * 0.7) * 2.0, GENEVA_H * 0.4, 0, 0, z0)
    hub = hub.cut(_cyl(KNOB_BORE, GENEVA_H + 2, 0, 0, z0 - 1))

    driver = lock.fuse(hub)
    driver.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), _driver_world_angle_deg(open_mm))
    driver.translate(App.Vector(kx, ky, 0))
    return _keep(driver)


def make_gear_drive_disc(open_mm: float):
    """
    Large disc (video driver OD ≈ pin circle) under the small lock disc.
    Carries drive pin (mấu) + involute pinion for Gap_Slider rack.
    """
    App, Part = _fc()
    from rotary_linear import make_involute_pinion_local  # noqa: PLC0415

    kx, ky = _knob_xy()
    g = _gear()
    ang = _driver_world_angle_deg(open_mm)

    # Large plate — tỉ lệ đĩa dẫn trong video (OD ≈ vòng mấu)
    disc = _cyl(GEAR_DISC_R * 2.0, GEAR_DISC_H, 0, 0, GEAR_DISC_Z0)
    disc = disc.cut(_cyl(KNOB_BORE, GEAR_DISC_H + 2, 0, 0, GEAR_DISC_Z0 - 1))
    # Clear Malta / gate stack (local: Malta at −knob before world translate)
    try:
        disc = disc.cut(
            _cyl(
                (LOCK_WING_R + 2.0) * 2.0,
                GEAR_DISC_H + 2.0,
                -kx,
                -ky,
                GEAR_DISC_Z0 - 1.0,
            )
        )
    except Exception:
        pass
    # Lighten rim scallops (cosmetic) — skip toward Malta
    bearing = math.degrees(math.atan2(-ky, -kx))
    for i in range(6):
        a = math.radians(i * 60.0 + 15.0)
        # Skip scallops on Malta-facing half
        dang = abs((math.degrees(a) - bearing + 180.0) % 360.0 - 180.0)
        if dang < 70.0:
            continue
        sx = (GEAR_DISC_R - 0.8) * math.cos(a)
        sy = (GEAR_DISC_R - 0.8) * math.sin(a)
        try:
            disc = disc.cut(_cyl(2.4, GEAR_DISC_H + 1.0, sx, sy, GEAR_DISC_Z0 - 0.5))
        except Exception:
            pass

    # Pin (mấu) on large disc — rises into Geneva / Malta band
    pin = _cyl(
        DRIVE_PIN_D,
        (GENEVA_Z0 + GENEVA_H + 0.8) - GEAR_DISC_Z0,
        DRIVE_PIN_R,
        0.0,
        GEAR_DISC_Z0 + 0.1,
    )
    head = _cyl(DRIVE_PIN_D + 1.0, 1.2, DRIVE_PIN_R, 0.0, GENEVA_Z0 + GENEVA_H * 0.85)

    pinion = make_involute_pinion_local(
        module=GEAR_MODULE,
        teeth=PINION_TEETH,
        face_w=PINION_FACE,
        bore=KNOB_BORE,
        alpha_deg=PRESSURE_ANGLE,
        tooth_clear=TOOTH_CLEAR,
        min_teeth=PINION_TEETH,
    )
    pinion.translate(App.Vector(0, 0, PINION_Z0))

    body = disc.fuse(pin).fuse(head).fuse(pinion)
    body.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), ang)
    body.translate(App.Vector(kx, ky, 0))
    return _keep(body), g


def make_drive_knob(open_mm: float):
    """Hand knob on top of shaft — rotate to drive Geneva + rack."""
    App, Part = _fc()
    kx, ky = _knob_xy()

    rim = _cyl(KNOB_OD, KNOB_H * 0.65, 0, 0, KNOB_Z0)
    rim = rim.cut(_cyl(KNOB_BORE, KNOB_H + 2, 0, 0, KNOB_Z0 - 1))
    for i in range(8):
        a = math.radians(i * 45.0)
        fx = (KNOB_OD / 2.0 - 0.35) * math.cos(a)
        fy = (KNOB_OD / 2.0 - 0.35) * math.sin(a)
        flat = _box(2.0, 1.1, KNOB_H * 0.55, fx - 1.0, fy - 0.55, KNOB_Z0 + 0.4)
        try:
            rim = rim.cut(flat)
        except Exception:
            pass
    # Stem down toward lock disc
    stem = _cyl(KNOB_BORE + 2.4, KNOB_Z0 - (GENEVA_Z0 + GENEVA_H) + 0.8, 0, 0, GENEVA_Z0 + GENEVA_H - 0.3)
    stem = stem.cut(_cyl(KNOB_BORE, 20, 0, 0, GENEVA_Z0 + GENEVA_H - 1))

    knob = rim.fuse(stem)
    knob.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), _driver_world_angle_deg(open_mm))
    knob.translate(App.Vector(kx, ky, 0))
    return _keep(knob)


def make_slider_rack(open_mm: float, g: dict):
    """
    Rack on −Y face of Gap_Slider bar — same spur_gear_math as pinion.
    Teeth point −Y toward knob; length along +X.
    """
    App, Part = _fc()
    x_left = slider_x_left(open_mm)
    y_bar0 = SLIDER_Y - SLIDER_T / 2.0
    z0 = SLIDER_Z0
    p = g["circular_pitch"]
    ha, hf = g["addendum"], g["dedendum"]
    th = g["tooth_half_w"]
    # Pitch line: pinion center + pitch_r toward +Y (toward bar)
    pitch_r = g["pitch_radius"]
    y_pitch = KNOB_Y + pitch_r + CENTER_BACKLASH
    y_tip = y_pitch - ha  # tip toward −Y (toward pinion)
    y_root = y_pitch + hf  # root toward +Y (into / past bar face)

    h_tip = th(+ha)
    h_root = th(-hf)
    if h_root <= h_tip:
        h_root = h_tip + 0.5

    # Body strip on bar −Y face
    body = _box(SLIDER_LEN - 4.0, max(0.8, y_bar0 - y_root + 0.2), SLIDER_H - 0.4,
                x_left + 2.0, y_root - 0.1, z0 + 0.2)

    # One tooth in XZ (half-widths along X), extruded in Y from tip to root
    # Tooth profile in X (along travel) × Y (depth)
    pts = [
        App.Vector(-h_root, y_root, 0),
        App.Vector(-h_tip, y_tip, 0),
        App.Vector(+h_tip, y_tip, 0),
        App.Vector(+h_root, y_root, 0),
        App.Vector(-h_root, y_root, 0),
    ]
    tooth0 = Part.Face(Part.makePolygon(pts)).extrude(App.Vector(0, 0, PINION_FACE))
    tooth0.translate(App.Vector(0, 0, z0 + (SLIDER_H - PINION_FACE) * 0.5))

    # Phase: SPACE at mesh X under pinion (kx) so pinion tooth seats in gap
    mesh_x = KNOB_X
    solid = body
    i0 = int(math.floor((x_left - mesh_x) / p)) - 2
    i1 = int(math.ceil((x_left + SLIDER_LEN - mesh_x) / p)) + 2
    for i in range(i0, i1 + 1):
        xc = mesh_x + (i + 0.5) * p
        if xc - h_root < x_left + 1.0 or xc + h_root > x_left + SLIDER_LEN - 1.0:
            continue
        tooth = tooth0.copy()
        tooth.translate(App.Vector(xc, 0, 0))
        solid = solid.fuse(tooth)
    return _keep(solid)


def make_gap_slider(open_mm: float):
    open_mm = clamp_open(open_mm)
    x_left = slider_x_left(open_mm)
    y0 = SLIDER_Y - SLIDER_T / 2
    z0 = SLIDER_Z0
    g = _gear()

    bar = _box(SLIDER_LEN, SLIDER_T, SLIDER_H, x_left, y0, z0)
    grip = _box(12.0, SLIDER_T + 1.5, 2.0, x_left + SLIDER_LEN - 14.0, y0 - 0.75, z0 + SLIDER_H - 0.3)

    shoe_dy = SLIDER_T - 2.0 * RAIL_SLOT_CLEAR + 0.1
    shoe_h = SLIDER_H - 0.2
    shoe_l = _box(6.0, shoe_dy, shoe_h, x_left + 2.0, -shoe_dy / 2, z0)
    shoe_r = _box(6.0, shoe_dy, shoe_h, x_left + SLIDER_LEN - 8.0, -shoe_dy / 2, z0)

    rack = make_slider_rack(open_mm, g)
    aperture = make_aperture_plate(open_mm)

    bar = bar.fuse(grip).fuse(shoe_l).fuse(shoe_r).fuse(rack)
    try:
        bar = bar.cut(_malta_travel_slot_cutter(x_left))
    except Exception:
        pass
    fused = bar.fuse(aperture)
    return _keep(fused)


def make_pivot_pin():
    px, py = _pivot_xy()
    z0 = FLOOR_T - 1.0
    h = GENEVA_Z0 + GENEVA_H - z0
    pin = _cyl(PIVOT_D, h, px, py, z0)
    head = _cyl(5.0, 1.2, px, py, z0)
    return _keep(pin.fuse(head))


def make_knob_shaft_pin():
    kx, ky = _knob_xy()
    z0 = FLOOR_T - 1.0
    h = KNOB_Z0 + KNOB_H * 0.65 - z0
    pin = _cyl(KNOB_BORE - 0.2, h, kx, ky, z0)
    head = _cyl(6.0, 1.2, kx, ky, z0)
    return _keep(pin.fuse(head))


def make_lane_labels_proxy():
    g = groove_x_bounds()
    z0 = FLOOR_T + 0.4
    small = _box(SMALL_GROOVE_W - 0.5, GROOVE_LEN - 4, 1.5, g["small_x0"] + 0.25, -GROOVE_LEN + 1, z0)
    large = _box(LARGE_GROOVE_W - 0.5, GROOVE_LEN - 4, 1.5, g["large_x0"] + 0.25, -GROOVE_LEN + 1, z0)
    inlet = _box(
        g["large_x1"] - g["small_x0"] - 0.6,
        6.0,
        min(PILL_CLEAR_H - 1.0, MALTA_Z0 - FLOOR_T - 0.5),
        g["small_x0"] + 0.3,
        2.0,
        FLOOR_T + 0.3,
    )
    return [
        ("Lane_Fill_Small_5p5", small, (0.30, 0.75, 0.95)),
        ("Lane_Fill_Large_12", large, (0.95, 0.55, 0.22)),
        ("Inlet_Pill_Passage", inlet, (0.45, 0.90, 0.55)),
    ]


def guide_chute_keepout_r() -> float:
    """Radial keepout for Malta arm tips (+ clearance) during full index."""
    return ARM_ROOT + ARM_LARGE_L + GUIDE_CHUTE_TIP_CLEAR


def guide_chute_under_h() -> float:
    """Wall/floor height under GATE arms — no Z overlap with Malta."""
    return max(1.0, MALTA_Z0 - FLOOR_T - GUIDE_CHUTE_UNDER_CLEAR)


def _chute_y_plus_keepout(x: float, r: float) -> float:
    """+Y intersection of keepout circle with vertical line at x (inlet side)."""
    inside = r * r - x * x
    if inside <= 0.0:
        return 0.0
    return math.sqrt(inside)


def _make_one_guide_chute(x0: float, x1: float, *, name_tag: str):
    """
    One U-trough co-linear with a groove:
      - under-arm continuous floor+walls through Malta (no gap to grooves)
      - short +Y inlet mouth outside tip keepout (feeds divert)
    Inner radial face = cylinder cut so park tip gap == TIP_CLEAR.
    """
    App, Part = _fc()
    r_ko = guide_chute_keepout_r()
    h_under = guide_chute_under_h()
    wt = GUIDE_CHUTE_WALL_T
    z0 = FLOOR_T
    xc = 0.5 * (x0 + x1)
    y_plus = _chute_y_plus_keepout(xc, r_ko)
    # Grooves live on −Y; connect from groove body up to keepout, then short inlet
    y_groove = -GROOVE_LEN + 2.0
    y_under_hi = max(y_plus, 1.0)  # through gate toward inlet keepout
    y_inlet0 = y_plus
    y_inlet1 = y_plus + GUIDE_CHUTE_INLET_L

    # --- Under-arm trough (connects to large/small grooves, clears GATE in Z) ---
    floor = _box(x1 - x0, y_under_hi - y_groove, 1.2, x0, y_groove, z0)
    wall_l = _box(wt, y_under_hi - y_groove, h_under, x0 - wt, y_groove, z0)
    wall_r = _box(wt, y_under_hi - y_groove, h_under, x1, y_groove, z0)
    under = floor.fuse(wall_l).fuse(wall_r)
    # Pocket for pivot boss / arm root
    try:
        under = under.cut(_cyl((PIVOT_BOSS_OD + 1.5), h_under + 2.0, 0, 0, z0 - 0.5))
    except Exception:
        pass

    # --- Short inlet mouth (+Y), full wall height, outside keepout ---
    h_in = min(WALL_H * 0.55, MALTA_Z0 + GATE_H * 0.35 - z0)
    inlet_floor = _box(x1 - x0, y_inlet1 - y_inlet0, 1.2, x0, y_inlet0, z0)
    inlet_wl = _box(wt, y_inlet1 - y_inlet0, h_in, x0 - wt, y_inlet0, z0)
    inlet_wr = _box(wt, y_inlet1 - y_inlet0, h_in, x1, y_inlet0, z0)
    inlet = inlet_floor.fuse(inlet_wl).fuse(inlet_wr)
    # Radial seal face: cylinder at tip keepout — gap to arm tip when parked
    try:
        cutter = _cyl(r_ko * 2.0, h_in + 4.0, 0.0, 0.0, z0 - 1.0)
        inlet = inlet.cut(cutter)
        under = under.cut(cutter)
    except Exception:
        pass

    body = under.fuse(inlet)
    return _keep(body), {
        "tag": name_tag,
        "x0": x0,
        "x1": x1,
        "width_mm": x1 - x0,
        "y_groove": y_groove,
        "y_under_hi": y_under_hi,
        "y_inlet0": round(y_inlet0, 3),
        "y_inlet1": round(y_inlet1, 3),
        "keepout_r": round(r_ko, 3),
        "under_h": round(h_under, 3),
        "inlet_h": round(h_in, 3),
    }


def make_groove_guide_chutes():
    """
    Two short chutes at the groove lanes — same direction as small/large máng.
    Connect continuously into divert; Malta tip keepout ⇒ no collision / no gap.
    Returns list of (name, shape, color) for Small + Large children.
    """
    g = groove_x_bounds()
    small, meta_s = _make_one_guide_chute(g["small_x0"], g["small_x1"], name_tag="small")
    large, meta_l = _make_one_guide_chute(g["large_x0"], g["large_x1"], name_tag="large")
    make_groove_guide_chutes._last_meta = (meta_s, meta_l)  # type: ignore[attr-defined]
    return [
        ("Guide_Chute_Small", small, (0.25, 0.70, 0.55)),
        ("Guide_Chute_Large", large, (0.90, 0.60, 0.25)),
    ]


def arm_tip_world(park_deg: float, which: str) -> tuple[float, float, float]:
    """World XY of arm tip + radius. which='large'|'small'."""
    if which == "large":
        L, a0 = ARM_LARGE_L, 0.0
    else:
        L, a0 = ARM_SMALL_L, MALTA_ARM_ANGLE_DEG
    a = math.radians(park_deg + a0)
    r = ARM_ROOT + L
    return r * math.cos(a), r * math.sin(a), r


def verify_guide_chutes(n_sweep: int = 9) -> dict:
    """
    Math: chute width == groove width; tip keepout = R_arm + CLEAR.
    Continuity: under-chute spans groove → inlet keepout.
    Collision: Malta∩chute == 0 over SMALL→LARGE sweep.
    Gap: at parks, tip radial gap ≈ TIP_CLEAR (no void larger than 2·CLEAR).
    """
    g = groove_x_bounds()
    parts = make_groove_guide_chutes()
    by = {n: s for n, s, _c in parts}
    chute_u = by["Guide_Chute_Small"].fuse(by["Guide_Chute_Large"])
    meta_s, meta_l = make_groove_guide_chutes._last_meta  # type: ignore[attr-defined]
    r_ko = guide_chute_keepout_r()

    width_ok = (
        abs(meta_s["width_mm"] - SMALL_GROOVE_W) < 0.05
        and abs(meta_l["width_mm"] - LARGE_GROOVE_W) < 0.05
    )
    keepout_ok = abs(r_ko - (ARM_ROOT + ARM_LARGE_L + GUIDE_CHUTE_TIP_CLEAR)) < 0.02
    # Under height strictly below Malta arms
    z_ok = guide_chute_under_h() <= (MALTA_Z0 - FLOOR_T - GUIDE_CHUTE_UNDER_CLEAR + 0.05)
    # Continuity: inlet starts at keepout +Y
    cont_ok = (
        abs(meta_s["y_inlet0"] - _chute_y_plus_keepout(0.5 * (g["small_x0"] + g["small_x1"]), r_ko))
        < 0.15
        and abs(meta_l["y_inlet0"] - _chute_y_plus_keepout(0.5 * (g["large_x0"] + g["large_x1"]), r_ko))
        < 0.15
        and meta_s["y_inlet1"] - meta_s["y_inlet0"] >= GUIDE_CHUTE_INLET_L - 0.05
        and meta_l["y_inlet1"] - meta_l["y_inlet0"] >= GUIDE_CHUTE_INLET_L - 0.05
    )

    max_ov = 0.0
    jam = 0
    sweep_rows = []
    for i in range(n_sweep):
        t = i / max(1, n_sweep - 1)
        op = OPEN_TRANSIT_LO + t * (OPEN_TRANSIT_HI - OPEN_TRANSIT_LO)
        # also parks outside transit
        if i == 0:
            op = OPEN_SMALL_LO
        if i == n_sweep - 1:
            op = OPEN_LARGE_HI
        ang = malta_angle_for_open(op)
        malta = make_malta_cross(ang)
        ov = common_volume(malta, chute_u)
        max_ov = max(max_ov, ov)
        if ov >= 0.5:
            jam += 1
        sweep_rows.append(
            {
                "open_mm": round(op, 3),
                "malta_deg": round(ang, 2),
                "overlap_mm3": round(ov, 3),
            }
        )

    # Park tip gaps (radial): tip_r should sit on keepout circle
    tip_gaps = []
    gap_ok = True
    for park, which, lane in (
        (MALTA_ANGLE_SMALL, "large", "large"),  # large arm tip near large outer at SMALL
        (MALTA_ANGLE_LARGE, "large", "small"),  # large arm swings toward small/inlet
        (MALTA_ANGLE_SMALL, "small", "small"),
        (MALTA_ANGLE_LARGE, "small", "large"),
    ):
        tx, ty, tr = arm_tip_world(park, which)
        gap = r_ko - tr  # design: large tip on keepout; small tip inside
        tip_gaps.append(
            {
                "park_deg": park,
                "arm": which,
                "lane_hint": lane,
                "tip_xy": [round(tx, 3), round(ty, 3)],
                "tip_r": round(tr, 3),
                "keepout_r": round(r_ko, 3),
                "radial_gap_mm": round(gap, 3),
            }
        )
    # Primary seal: large-arm tip radius + CLEAR == keepout
    primary_gap = abs((ARM_ROOT + ARM_LARGE_L + GUIDE_CHUTE_TIP_CLEAR) - r_ko)
    tip_seal_ok = primary_gap < 0.05 and GUIDE_CHUTE_TIP_CLEAR > 0.0
    # Small arm shorter — always inside keepout (positive gap to circle)
    small_inside = all(
        t["radial_gap_mm"] >= -0.05
        for t in tip_gaps
        if t["arm"] == "small"
    )
    gap_ok = tip_seal_ok and small_inside

    collision_ok = jam == 0 and max_ov < 0.5
    passed = bool(width_ok and keepout_ok and z_ok and cont_ok and collision_ok and gap_ok)

    return {
        "pass": passed,
        "width_ok": width_ok,
        "keepout_ok": keepout_ok,
        "under_z_ok": z_ok,
        "continuity_ok": cont_ok,
        "collision_ok": collision_ok,
        "gap_ok": gap_ok,
        "keepout_r_mm": round(r_ko, 3),
        "tip_clear_mm": GUIDE_CHUTE_TIP_CLEAR,
        "under_h_mm": round(guide_chute_under_h(), 3),
        "inlet_len_mm": GUIDE_CHUTE_INLET_L,
        "max_overlap_mm3": round(max_ov, 3),
        "jam_hits": jam,
        "meta_small": meta_s,
        "meta_large": meta_l,
        "tip_gaps": tip_gaps,
        "sweep": sweep_rows,
        "note": (
            "Guide chutes = groove X; under-arm continuous; "
            "+Y mouths outside tip keepout; Malta sweep overlap==0"
        ),
    }


def common_volume(a, b) -> float:
    try:
        inter = a.common(b)
        if inter is None or not getattr(inter, "Solids", None):
            return 0.0
        return float(sum(abs(s.Volume) for s in inter.Solids))
    except Exception:
        return 0.0


def _rail_walls_union():
    parts = make_slider_rail_parts()
    by = {n: s for n, s, _c in parts}
    walls = by["Slider_Rail_Wall_NegY"].fuse(by["Slider_Rail_Wall_PosY"])
    walls = walls.fuse(by["Slider_Rail_Stop_L"]).fuse(by["Slider_Rail_Stop_R"])
    return _keep(walls)


def _slider_bar_probe(open_mm: float):
    x_left = slider_x_left(open_mm)
    y0 = SLIDER_Y - SLIDER_T / 2
    z0 = SLIDER_Z0
    bar = _box(SLIDER_LEN, SLIDER_T, SLIDER_H, x_left, y0, z0)
    shoe_dy = SLIDER_T - 2.0 * RAIL_SLOT_CLEAR + 0.1
    shoe_h = SLIDER_H - 0.2
    shoe_l = _box(6.0, shoe_dy, shoe_h, x_left + 2.0, -shoe_dy / 2, z0)
    shoe_r = _box(6.0, shoe_dy, shoe_h, x_left + SLIDER_LEN - 8.0, -shoe_dy / 2, z0)
    return _keep(bar.fuse(shoe_l).fuse(shoe_r))


def geneva_math_report() -> dict:
    """
    1-slot Geneva for 90° gate (open inward to divider) + arms = groove widths.
    """
    n = N_DRIVE_SLOTS
    a = GENEVA_A
    alpha = GENEVA_ALPHA_DEG
    index_deg = MALTA_INDEX_DEG
    pin_at_rim = abs(DRIVE_PIN_R - a * math.sin(math.radians(alpha))) < 0.05
    malta_r_ok = abs(MALTA_DISK_R - a * math.cos(math.radians(alpha))) < 0.05
    lock_ok = abs(LOCK_DISC_R - (a - MALTA_DISK_R)) < 0.05
    engage_r = math.sqrt(
        a * a
        + DRIVE_PIN_R * DRIVE_PIN_R
        - 2.0 * a * DRIVE_PIN_R * math.cos(math.radians(alpha))
    )
    pin_at_engage_rim = abs(engage_r - MALTA_DISK_R) < 0.15
    pin_fits_slot = DRIVE_PIN_D < SLOT_W - 0.2
    z_overlap = GENEVA_Z0 < MALTA_Z0 + MALTA_H - 0.2
    hub_pack_ok = MALTA_HUB_R < 9.0
    lock_geo_ok = lock_ok and LOCK_DISC_R > 2.0 and N_LOCK_ARCS >= 2
    index_ok = abs(MALTA_ANGLE_LARGE - MALTA_ANGLE_SMALL - index_deg) < 5.0
    arms_ok = (
        abs(ARM_LARGE_L - LARGE_GROOVE_W) < 0.05
        and abs(ARM_SMALL_L - SMALL_GROOVE_W) < 0.05
        and abs(MALTA_ARM_ANGLE_DEG - 90.0) < 0.05
    )
    d_open = OPEN_TRANSIT_HI - OPEN_TRANSIT_LO
    d_knob = knob_angle_deg(OPEN_TRANSIT_HI) - knob_angle_deg(OPEN_TRANSIT_LO)
    malta_delta = MALTA_ANGLE_LARGE - MALTA_ANGLE_SMALL
    index_knob_ok = abs(d_knob - GENEVA_DRIVE_DEG) < 1.0
    malta_throw_ok = abs(malta_delta - MALTA_INDEX_DEG) < 1.0
    open_inward_ok = abs(MALTA_ANGLE_LARGE - 90.0) < 0.5
    closed_across_ok = abs(MALTA_ANGLE_SMALL - 0.0) < 0.5
    single_slot_ok = n == 1
    travel_span = OPEN_DRIVE_HI - OPEN_DRIVE_LO
    travel_ok = abs(travel_span - SLIDER_TRAVEL_MM) < 0.05 and travel_span <= (
        SMALL_GROOVE_W + LARGE_GROOVE_W + 0.05
    )
    geneva_fits = OPEN_TRANSIT_HI <= OPEN_LARGE_HI - 0.15

    passed = bool(
        hub_pack_ok
        and pin_at_rim
        and malta_r_ok
        and lock_geo_ok
        and pin_at_engage_rim
        and pin_fits_slot
        and z_overlap
        and index_ok
        and index_knob_ok
        and malta_throw_ok
        and single_slot_ok
        and travel_ok
        and geneva_fits
        and arms_ok
        and open_inward_ok
        and closed_across_ok
    )
    return {
        "pass": passed,
        "geneva_alpha_deg": alpha,
        "n_drive_slots": n,
        "n_lock_arcs": N_LOCK_ARCS,
        "malta_arm_angle_deg": MALTA_ARM_ANGLE_DEG,
        "single_slot": single_slot_ok,
        "slider_travel_mm": round(travel_span, 3),
        "slider_travel_ok": travel_ok,
        "geneva_fits_in_travel": geneva_fits,
        "index_deg": index_deg,
        "arms_ok": arms_ok,
        "arm_large_l_mm": ARM_LARGE_L,
        "arm_small_l_mm": ARM_SMALL_L,
        "open_inward_ok": open_inward_ok,
        "closed_across_ok": closed_across_ok,
        "center_distance_a_mm": round(a, 3),
        "drive_pin_r_mm": round(DRIVE_PIN_R, 3),
        "malta_disk_r_mm": round(MALTA_DISK_R, 3),
        "malta_hub_r_mm": round(MALTA_HUB_R, 3),
        "lock_disc_r_mm": round(LOCK_DISC_R, 3),
        "lock_wing_r_mm": round(LOCK_WING_R, 3),
        "gear_disc_r_mm": round(GEAR_DISC_R, 3),
        "engage_pin_to_malta_mm": round(engage_r, 3),
        "pin_on_rim_at_engage": pin_at_engage_rim,
        "classic_pin_r": pin_at_rim,
        "classic_malta_r": malta_r_ok,
        "classic_lock_r": lock_ok,
        "lock_geo_ok": lock_geo_ok,
        "pin_fits_slot": pin_fits_slot,
        "z_overlap_pin_hub": z_overlap,
        "slot_phase_deg": round(SLOT_PHASE_DEG, 2),
        "hub_clears_walls": hub_pack_ok,
        "index_knob_matches_drive": index_knob_ok,
        "malta_throw_ok": malta_throw_ok,
        "note": (
            "Arms 90° (L=groove W); closed +X / open +Y into divider; "
            "knob 90° (α=45° pin/lock)"
        ),
        "malta_index_delta_deg": round(malta_delta, 2),
        "transit_open_mm": round(d_open, 3),
        "transit_knob_deg": round(d_knob, 3),
        "threshold_mm": THRESHOLD_MM,
        "knob_xy": [KNOB_X, KNOB_Y],
        "geneva_z0": GENEVA_Z0,
        "gate_h": GATE_H,
        "malta_z_band": [MALTA_Z0, MALTA_Z0 + MALTA_H],
    }


def verify_open_door_nest() -> dict:
    """
    When a chute door is OPEN it nests in the divider pocket (inward, sát thành).
      SMALL park: small-arm along +Y in pocket
      LARGE park: large-arm along +Y in pocket
    Closed: large-arm across +X fills large groove width.
    """
    math_r = geneva_math_report()
    frame = make_divert_frame()

    # Closed: large arm tip at +X ≈ large outer wall
    tx0, ty0, tr0 = arm_tip_world(MALTA_ANGLE_SMALL, "large")
    closed_across = abs(ty0) < 1.5 and tx0 > (LARGE_GROOVE_W * 0.5)

    # Open nests: arm along +Y → tip near (0, R)
    rows = []
    nest_ok = True
    for park, which in (
        (MALTA_ANGLE_SMALL, "small"),  # small arm @ 90° when malta=0
        (MALTA_ANGLE_LARGE, "large"),  # large arm @ 90° when malta=90
    ):
        tx, ty, tr = arm_tip_world(park, which)
        along_y = abs(tx) < 1.5 and ty > ARM_ROOT
        malta = make_malta_cross(park)
        ov = common_volume(malta, frame)
        # Soft nest: small overlap with pocket walls OK; deep jam not OK
        soft_ok = ov < 40.0
        nest_ok = nest_ok and along_y and soft_ok
        rows.append(
            {
                "park_deg": park,
                "arm": which,
                "tip_xy": [round(tx, 3), round(ty, 3)],
                "along_plus_y": along_y,
                "overlap_frame_mm3": round(ov, 3),
                "soft_nest_ok": soft_ok,
            }
        )

    # Sweep collision (mid) should stay low aside from intentional nest at parks
    max_mid = 0.0
    for t in (0.25, 0.5, 0.75):
        ang = MALTA_ANGLE_SMALL + t * (MALTA_ANGLE_LARGE - MALTA_ANGLE_SMALL)
        ov = common_volume(make_malta_cross(ang), frame)
        max_mid = max(max_mid, ov)

    passed = bool(
        math_r.get("pass")
        and closed_across
        and nest_ok
        and max_mid < 25.0
    )
    return {
        "pass": passed,
        "closed_across_large": closed_across,
        "closed_tip_xy": [round(tx0, 3), round(ty0, 3)],
        "open_nests": rows,
        "max_mid_overlap_mm3": round(max_mid, 3),
        "door_motion": "inward_to_divider_pocket",
        "malta_index_deg": MALTA_INDEX_DEG,
        "arm_angle_deg": MALTA_ARM_ANGLE_DEG,
        "note": "Open door swings into divider pocket and sits flush (sát thành máng)",
    }


def _pin_world_xy(open_mm: float) -> tuple[float, float]:
    th = math.radians(_driver_world_angle_deg(open_mm))
    return (
        KNOB_X + DRIVE_PIN_R * math.cos(th),
        KNOB_Y + DRIVE_PIN_R * math.sin(th),
    )


def pin_slot_engagement(open_mm: float) -> dict:
    """
    Geometric seat: pin in slot fan during transit (rim → inward → rim).
    Perfect seat in void ⇒ common_volume(pin, malta)≈0 (OK).
    """
    px, py = _pin_world_xy(open_mm)
    r = math.hypot(px, py)
    pin_ang = math.degrees(math.atan2(py, px))
    malta_ang = malta_angle_for_open(open_mm)
    best = 999.0
    for i in range(N_DRIVE_SLOTS):
        sa = 90.0 + SLOT_PHASE_DEG + malta_ang + 360.0 * i / max(1, N_DRIVE_SLOTS)
        d = abs((pin_ang - sa + 180.0) % 360.0 - 180.0)
        best = min(best, d)
    half_w_deg = math.degrees(math.atan2(SLOT_W * 0.5 - 0.15, max(r, 1.0)))
    in_r = 1.5 <= r <= (LOCK_WING_R + 0.5)
    aligned = best <= max(8.0, half_w_deg + 3.0)
    return {
        "r_mm": round(r, 3),
        "pin_ang_deg": round(pin_ang, 2),
        "best_slot_delta_deg": round(best, 2),
        "in_hub_ring": in_r,
        "aligned": aligned,
        "engaged": bool(in_r and aligned),
    }


def _geneva_pin_probe(open_mm: float):
    """Drive pin solid alone (for solid-interference checks)."""
    App, Part = _fc()
    kx, ky = _knob_xy()
    pin = _cyl(
        DRIVE_PIN_D,
        (GENEVA_Z0 + GENEVA_H + 0.8) - GEAR_DISC_Z0,
        DRIVE_PIN_R,
        0.0,
        GEAR_DISC_Z0 + 0.1,
    )
    pin.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), _driver_world_angle_deg(open_mm))
    pin.translate(App.Vector(kx, ky, 0))
    return _keep(pin)


def verify_geneva_knob_rotation(n_steps: int = 24) -> dict:
    """
    Sweep knob via open_mm. Check math, pin-in-slot geometry at THRESHOLD,
    and solid jams (pin into lobe, driver∩frame, malta∩frame).
    Perfect seat in slot void ⇒ common_volume(pin,malta)≈0 — that is OK.
    """
    math_r = geneva_math_report()
    frame = make_divert_frame()

    opens = [
        OPEN_SMALL_LO + (OPEN_LARGE_HI - OPEN_SMALL_LO) * i / max(1, n_steps - 1)
        for i in range(n_steps)
    ]
    for t in (0.0, 0.25, 0.5, 0.75, 1.0):
        opens.append(OPEN_TRANSIT_LO + t * (OPEN_TRANSIT_HI - OPEN_TRANSIT_LO))
    opens = sorted(set(round(o, 4) for o in opens))

    rows = []
    max_illegal = 0.0
    jam_hits = 0
    dwell_deep = 0

    for op in opens:
        malta = make_malta_cross(malta_angle_for_open(op))
        driver = make_geneva_driver(op)
        pin = _geneva_pin_probe(op)
        eng = pin_slot_engagement(op)

        ov_dm = common_volume(driver, malta)
        ov_pm = common_volume(pin, malta)
        ov_df = common_volume(driver, frame)
        ov_mf = common_volume(malta, frame)

        in_transit = OPEN_TRANSIT_LO - 0.15 <= op <= OPEN_TRANSIT_HI + 0.15

        # Mid-transit: pin rides in slot (contact OK). Outside: flag lobe digs.
        if in_transit:
            ill_pm = 0.0
        elif eng["engaged"]:
            ill_pm = ov_pm if ov_pm > 8.0 else 0.0
        else:
            ill_pm = ov_pm if ov_pm > 18.0 else 0.0
        ill_dm = 0.0 if in_transit else (ov_dm if ov_dm > 20.0 else 0.0)
        ill_df = ov_df if ov_df > 5.0 else 0.0
        ill_mf = ov_mf if ov_mf > 14.0 else 0.0
        illegal = max(ill_pm, ill_dm, ill_df, ill_mf)
        max_illegal = max(max_illegal, illegal)
        if illegal >= 8.0:
            jam_hits += 1
        if (not in_transit) and ov_dm > 20.0:
            dwell_deep += 1

        rows.append({
            "open_mm": round(op, 3),
            "knob_deg": round(knob_angle_deg(op), 2),
            "malta_deg": round(malta_angle_for_open(op), 2),
            "state": flap_state_for_open(op),
            "in_transit": in_transit,
            "pin_engaged": eng["engaged"],
            "pin_slot_delta_deg": eng["best_slot_delta_deg"],
            "pin_r_mm": eng["r_mm"],
            "overlap_driver_malta_mm3": round(ov_dm, 3),
            "overlap_pin_malta_mm3": round(ov_pm, 3),
            "overlap_driver_frame_mm3": round(ov_df, 3),
            "overlap_malta_frame_mm3": round(ov_mf, 3),
            "illegal_mm3": round(illegal, 3),
        })

    at_thresh = [r for r in rows if abs(r["open_mm"] - OPEN_TRANSIT_LO) < 0.05]
    engage_ok = bool(at_thresh) and bool(at_thresh[0]["pin_engaged"])
    dwell_ok = dwell_deep == 0
    malta_moved = abs(
        malta_angle_for_open(OPEN_LARGE_HI) - malta_angle_for_open(OPEN_SMALL_LO)
    ) > (MALTA_INDEX_DEG - 15.0)

    passed = bool(
        math_r["pass"]
        and jam_hits == 0
        and max_illegal < 8.0
        and engage_ok
        and dwell_ok
        and malta_moved
    )
    return {
        "pass": passed,
        "math": math_r,
        "jam_hits": jam_hits,
        "max_illegal_mm3": round(max_illegal, 3),
        "engage_ok": engage_ok,
        "dwell_ok": dwell_ok,
        "malta_moved_index": malta_moved,
        "malta_index_deg": MALTA_INDEX_DEG,
        "threshold_engagement": at_thresh[0] if at_thresh else None,
        "samples": rows,
    }


def verify_geneva_bidirectional(n_per_leg: int = 8) -> dict:
    """
    Forward (open ↑): SMALL → LARGE — đóng hẹp / mở rộng.
    Reverse (open ↓): LARGE → SMALL — mở hẹp / đóng rộng.
    Checks pin seat at both transit ends and collision both ways.
    """
    math_r = geneva_math_report()
    frame = make_divert_frame()

    def leg(opens: list[float], direction: str) -> dict:
        rows = []
        max_illegal = 0.0
        jam = 0
        malta_angles = []
        for op in opens:
            malta = make_malta_cross(malta_angle_for_open(op))
            driver = make_geneva_driver(op)
            pin = _geneva_pin_probe(op)
            eng = pin_slot_engagement(op)
            ov_pm = common_volume(pin, malta)
            ov_df = common_volume(driver, frame)
            ov_mf = common_volume(malta, frame)
            ov_dm = common_volume(driver, malta)
            in_transit = OPEN_TRANSIT_LO - 0.15 <= op <= OPEN_TRANSIT_HI + 0.15
            if eng["engaged"]:
                ill_pm = ov_pm if ov_pm > 8.0 else 0.0
            elif in_transit:
                ill_pm = 0.0
            else:
                # Single-slot: pin may wipe rim while approaching/leaving seat
                ill_pm = ov_pm if ov_pm > 18.0 else 0.0
            ill_df = ov_df if ov_df > 5.0 else 0.0
            ill_mf = ov_mf if ov_mf > 14.0 else 0.0
            ill_dm = 0.0 if in_transit else (ov_dm if ov_dm > 20.0 else 0.0)
            illegal = max(ill_pm, ill_df, ill_mf, ill_dm)
            max_illegal = max(max_illegal, illegal)
            if illegal >= 8.0:
                jam += 1
            mang = malta_angle_for_open(op)
            malta_angles.append(mang)
            rows.append({
                "open_mm": round(op, 3),
                "knob_deg": round(knob_angle_deg(op), 2),
                "malta_deg": round(mang, 2),
                "state": flap_state_for_open(op),
                "direction": direction,
                "in_transit": in_transit,
                "pin_engaged": eng["engaged"],
                "pin_slot_delta_deg": eng["best_slot_delta_deg"],
                "overlap_pin_malta_mm3": round(ov_pm, 3),
                "overlap_driver_frame_mm3": round(ov_df, 3),
                "illegal_mm3": round(illegal, 3),
            })
        return {
            "rows": rows,
            "max_illegal_mm3": round(max_illegal, 3),
            "jam_hits": jam,
            "malta_start_deg": round(malta_angles[0], 2) if malta_angles else None,
            "malta_end_deg": round(malta_angles[-1], 2) if malta_angles else None,
            "malta_delta_deg": round(malta_angles[-1] - malta_angles[0], 2)
            if malta_angles
            else None,
        }

    # Sample open path: dwell → transit → dwell (and reverse)
    def transit_samples():
        return [
            OPEN_TRANSIT_LO + t * (OPEN_TRANSIT_HI - OPEN_TRANSIT_LO)
            for t in (0.0, 0.25, 0.5, 0.75, 1.0)
        ]

    fwd_opens = (
        [OPEN_SMALL_LO, 3.0, OPEN_TRANSIT_LO - 0.01]
        + transit_samples()
        + [OPEN_TRANSIT_HI + 0.01, min(OPEN_LARGE_HI, OPEN_TRANSIT_HI + 3.0)]
    )
    # unique sorted ascending
    fwd_opens = sorted(set(round(o, 4) for o in fwd_opens if o >= OPEN_SMALL_LO))
    rev_opens = list(reversed(fwd_opens))

    fwd = leg(fwd_opens, "forward")
    rev = leg(rev_opens, "reverse")

    eng_lo = pin_slot_engagement(OPEN_TRANSIT_LO)
    eng_hi = pin_slot_engagement(OPEN_TRANSIT_HI)
    # Near end of index (exit): pin has left the slot (classic Geneva) — expected
    # Reverse re-entry uses the same LO seat after returning through transit.
    eng_near_hi = pin_slot_engagement(
        OPEN_TRANSIT_HI - 0.02 * (OPEN_TRANSIT_HI - OPEN_TRANSIT_LO)
    )

    fwd_ok = (
        fwd["malta_delta_deg"] is not None
        and fwd["malta_delta_deg"] > 80.0
        and fwd["jam_hits"] == 0
        and fwd["max_illegal_mm3"] < 8.0
    )
    rev_ok = (
        rev["malta_delta_deg"] is not None
        and rev["malta_delta_deg"] < -80.0
        and rev["jam_hits"] == 0
        and rev["max_illegal_mm3"] < 8.0
    )
    # Forward enters at LO; reverse completes back to LO seat (HI is exit, not seat)
    seat_fwd = bool(eng_lo["engaged"])
    seat_rev = bool(eng_lo["engaged"]) and abs(rev["malta_end_deg"] - MALTA_ANGLE_SMALL) < 2.0
    pin_exits_at_hi = not bool(eng_hi["engaged"])  # normal Geneva exit
    # Monotonic malta on each leg
    fwd_mono = all(
        fwd["rows"][i]["malta_deg"] <= fwd["rows"][i + 1]["malta_deg"] + 0.05
        for i in range(len(fwd["rows"]) - 1)
    )
    rev_mono = all(
        rev["rows"][i]["malta_deg"] >= rev["rows"][i + 1]["malta_deg"] - 0.05
        for i in range(len(rev["rows"]) - 1)
    )

    aw_small = aperture_widths(OPEN_SMALL_LO)
    door_fwd = aw_small["active"] == "SMALL" and flap_state_for_open(OPEN_LARGE_LO + 0.5) == "LARGE"
    door_rev = flap_state_for_open(OPEN_SMALL_HI - 0.5) == "SMALL"

    by_f = {r["open_mm"]: r["malta_deg"] for r in fwd["rows"]}
    by_r = {r["open_mm"]: r["malta_deg"] for r in rev["rows"]}
    sym_err = 0.0
    for op, mf in by_f.items():
        if op in by_r:
            sym_err = max(sym_err, abs(mf - by_r[op]))
    symmetric = sym_err < 0.05

    passed = bool(
        math_r["pass"]
        and fwd_ok
        and rev_ok
        and seat_fwd
        and seat_rev
        and pin_exits_at_hi
        and fwd_mono
        and rev_mono
        and door_fwd
        and door_rev
        and symmetric
    )
    return {
        "pass": passed,
        "math": math_r,
        "forward": {
            "ok": fwd_ok,
            "monotonic": fwd_mono,
            "malta_delta_deg": fwd["malta_delta_deg"],
            "jam_hits": fwd["jam_hits"],
            "max_illegal_mm3": fwd["max_illegal_mm3"],
            "meaning": "open↑ / knob+: close narrow lane, open wide lane",
            "samples": fwd["rows"],
        },
        "reverse": {
            "ok": rev_ok,
            "monotonic": rev_mono,
            "malta_delta_deg": rev["malta_delta_deg"],
            "jam_hits": rev["jam_hits"],
            "max_illegal_mm3": rev["max_illegal_mm3"],
            "meaning": "open↓ / knob-: open narrow lane, close wide lane",
            "samples": rev["rows"],
        },
        "seat_at_transit_lo": eng_lo,
        "seat_at_transit_hi": eng_hi,
        "seat_near_hi_exit": eng_near_hi,
        "seat_forward_entry": seat_fwd,
        "seat_reverse_return_to_lo": seat_rev,
        "pin_exits_at_hi_ok": pin_exits_at_hi,
        "door_logic_ok": door_fwd and door_rev,
        "pose_symmetric": symmetric,
        "pose_sym_err_deg": round(sym_err, 4),
        "transit_knob_deg": round(
            knob_angle_deg(OPEN_TRANSIT_HI) - knob_angle_deg(OPEN_TRANSIT_LO), 3
        ),
        "note": "Geneva 1-slot: pin seats at LO, exits at HI after 135°; reverse returns to LO; multi-turn ≤1 index/dir",
    }


def _count_malta_transitions(angles: list[float], mid: float) -> tuple[int, int]:
    """Count rising (below→above mid) and falling (above→below) crossings."""
    rise = fall = 0
    for i in range(1, len(angles)):
        a0, a1 = angles[i - 1], angles[i]
        if a0 < mid <= a1:
            rise += 1
        if a0 > mid >= a1:
            fall += 1
    return rise, fall


def verify_malta_lock_wings(spin_deg: float = 25.0) -> dict:
    """
    At SMALL and LARGE dwells (well clear of transit), the knob lock disc sits
    in a Malta wing arc. Forced free-spin of Malta by ±spin_deg must jam into
    the lock disc — proving the two wings prevent free rotation.
    """
    math_r = geneva_math_report()
    tpt = travel_per_turn()
    # ~180° of knob before/after transit — circular lock faces wing (mouth away)
    small_op = OPEN_TRANSIT_LO - tpt * (180.0 / 360.0)
    large_op = OPEN_TRANSIT_HI + tpt * (180.0 / 360.0)
    parks = [
        ("small", small_op, MALTA_ANGLE_SMALL),
        ("large", large_op, MALTA_ANGLE_LARGE),
    ]
    rows = []
    all_ok = True
    for name, op, ang in parks:
        driver = make_geneva_driver(op)
        malta = make_malta_cross(ang)
        ov_park = common_volume(driver, malta)
        park_clear = ov_park < 15.0
        jam_pos = common_volume(driver, make_malta_cross(ang + spin_deg))
        jam_neg = common_volume(driver, make_malta_cross(ang - spin_deg))
        locked = jam_pos > 5.0 or jam_neg > 5.0
        ok = park_clear and locked
        all_ok = all_ok and ok
        rows.append({
            "park": name,
            "open_mm": round(op, 3),
            "knob_deg": round(knob_angle_deg(op), 2),
            "malta_deg": round(ang, 2),
            "ov_park_mm3": round(ov_park, 3),
            "park_clear": park_clear,
            "jam_plus_mm3": round(jam_pos, 3),
            "jam_minus_mm3": round(jam_neg, 3),
            "free_spin_blocked": locked,
            "ok": ok,
        })
    passed = bool(math_r.get("pass") and all_ok)
    return {
        "pass": passed,
        "lock_disc_r_mm": LOCK_DISC_R,
        "lock_wing_r_mm": round(LOCK_WING_R, 3),
        "lock_clear_mm": LOCK_CLEAR,
        "spin_probe_deg": spin_deg,
        "parks": rows,
        "note": "2 concave wing arcs hug knob lock disc at SMALL/LARGE — blocks free Malta spin",
    }


def verify_malta_single_index(n_extra_turns: int = 3) -> dict:
    """
    Regardless of how many knob/open revolutions after the first index:
      forward campaign → exactly 1 SMALL→LARGE
      reverse campaign → exactly 1 LARGE→SMALL
    Also: after LARGE, further forward pin seats == 0; after SMALL, further
    reverse does not re-index (pose stays SMALL).
    """
    math_r = geneva_math_report()
    mid = 0.5 * (MALTA_ANGLE_SMALL + MALTA_ANGLE_LARGE)
    tpt = travel_per_turn()

    # Forward: start below transit, go many turns past LARGE
    o0 = OPEN_SMALL_LO
    o1 = OPEN_TRANSIT_HI + n_extra_turns * tpt
    n = max(40, int(8 * (n_extra_turns + 2)))
    fwd_opens = [o0 + (o1 - o0) * i / (n - 1) for i in range(n)]
    fwd_ang = [malta_angle_for_open(o) for o in fwd_opens]
    rise, fall_f = _count_malta_transitions(fwd_ang, mid)

    # Reverse: start above transit, go many turns below SMALL
    o2 = OPEN_TRANSIT_HI + n_extra_turns * tpt
    o3 = OPEN_SMALL_LO
    rev_opens = [o2 + (o3 - o2) * i / (n - 1) for i in range(n)]
    rev_ang = [malta_angle_for_open(o) for o in rev_opens]
    rise_r, fall = _count_malta_transitions(rev_ang, mid)

    # Extra forward after already LARGE: pin must not seat (rim lock)
    extra_fwd_seat = 0
    extra_fwd_samples = []
    for k in range(1, n_extra_turns * 4 + 1):
        op = OPEN_TRANSIT_HI + k * (tpt / 4.0)
        eng = pin_slot_engagement(op)
        extra_fwd_samples.append({
            "open_mm": round(op, 3),
            "knob_deg": round(knob_angle_deg(op), 2),
            "malta_deg": round(malta_angle_for_open(op), 2),
            "pin_engaged": eng["engaged"],
        })
        if eng["engaged"]:
            extra_fwd_seat += 1

    # Extra reverse while clamped at SMALL (open stuck at LO): no rise
    stuck_small = all(
        abs(malta_angle_for_open(OPEN_SMALL_LO) - MALTA_ANGLE_SMALL) < 0.5
        for _ in range(5)
    )

    fwd_once = rise == 1 and fall_f == 0
    rev_once = fall == 1 and rise_r == 0
    no_reseat_fwd = extra_fwd_seat == 0
    ends_large = abs(fwd_ang[-1] - MALTA_ANGLE_LARGE) < 1.0
    ends_small = abs(rev_ang[-1] - MALTA_ANGLE_SMALL) < 1.0

    # Collision spot-check: LO seat + a few extra-turn poses
    frame = make_divert_frame()
    jam = 0
    max_ill = 0.0
    for op in (OPEN_TRANSIT_LO, OPEN_TRANSIT_HI, OPEN_TRANSIT_HI + tpt, OPEN_TRANSIT_HI + 2 * tpt):
        malta = make_malta_cross(malta_angle_for_open(op))
        driver = make_geneva_driver(op)
        ov_df = common_volume(driver, frame)
        ov_dm = common_volume(driver, malta)
        eng = pin_slot_engagement(op)
        in_transit = OPEN_TRANSIT_LO - 0.2 <= op <= OPEN_TRANSIT_HI + 0.2
        ill = 0.0
        if ov_df > 5.0:
            ill = max(ill, ov_df)
        # After first index, pin∩rim (no 2nd slot) is intentional lock — not a jam
        if (
            (not eng["engaged"])
            and (not in_transit)
            and op <= OPEN_TRANSIT_HI + 0.3
            and ov_dm > 35.0
        ):
            ill = max(ill, ov_dm)
        max_ill = max(max_ill, ill)
        if ill >= 8.0:
            jam += 1

    passed = bool(
        math_r["pass"]
        and fwd_once
        and rev_once
        and no_reseat_fwd
        and ends_large
        and ends_small
        and stuck_small
        and jam == 0
        and N_DRIVE_SLOTS == 1
    )
    return {
        "pass": passed,
        "math": math_r,
        "n_drive_slots": N_DRIVE_SLOTS,
        "n_extra_turns": n_extra_turns,
        "forward": {
            "rise_count": rise,
            "fall_count": fall_f,
            "once_ok": fwd_once,
            "ends_at_large": ends_large,
            "open_span_mm": [round(o0, 3), round(o1, 3)],
        },
        "reverse": {
            "rise_count": rise_r,
            "fall_count": fall,
            "once_ok": rev_once,
            "ends_at_small": ends_small,
            "open_span_mm": [round(o2, 3), round(o3, 3)],
        },
        "extra_forward_pin_seats": extra_fwd_seat,
        "no_reseat_after_large": no_reseat_fwd,
        "extra_forward_samples": extra_fwd_samples[:12],
        "jam_hits": jam,
        "max_illegal_mm3": round(max_ill, 3),
        "note": "1 slot + saturated malta(open): multi-turn forward/reverse → exactly one index each",
    }


def verify_knob_slider_drive(n_steps: int = 8) -> dict:
    """
    Knob rotation must translate Gap_Slider via rack/pinion:
      Δopen_mm = travel_per_turn × Δknob_deg / 360
    Fine ring: circular pitch ≈ 1 mm (one tooth ≈ 1 mm slider).
    Mesh: pinion∩rack overlap stays small at a few sampled poses.
    """
    from rotary_linear import make_involute_pinion_local  # noqa: PLC0415

    g = _gear()
    p = float(g["circular_pitch"])
    tpt = float(g["travel_per_turn"])
    z = int(g["teeth"])
    m = float(g["module"])
    pitch_ok = abs(p - 1.0) < 0.06
    fine_ok = m < 0.55 and z <= 20
    open_per_tooth = tpt / z
    tooth_step_ok = abs(open_per_tooth - 1.0) < 0.06

    samples = []
    max_ov = 0.0
    couple_ok = True
    mesh_ok = True

    # Coupling samples (cheap — no solids)
    for i in range(n_steps):
        op = OPEN_DRIVE_LO + (OPEN_DRIVE_HI - OPEN_DRIVE_LO) * i / max(1, n_steps - 1)
        kd = knob_angle_deg(op)
        op_back = OPEN_SMALL_LO + tpt * (kd / 360.0)
        err = abs(op_back - op)
        if err > 0.05:
            couple_ok = False
        samples.append(
            {
                "open_mm": round(op, 3),
                "knob_deg": round(kd, 2),
                "couple_err_mm": round(err, 4),
                "slider_x_left": round(slider_x_left(op), 3),
            }
        )

    # Mesh at 3 poses only (boolean is expensive with fine teeth)
    App, _Part = _fc()
    pinion0 = make_involute_pinion_local(
        module=GEAR_MODULE,
        teeth=PINION_TEETH,
        face_w=PINION_FACE,
        bore=KNOB_BORE,
        alpha_deg=PRESSURE_ANGLE,
        tooth_clear=TOOTH_CLEAR,
        min_teeth=PINION_TEETH,
    )
    pinion0.translate(App.Vector(0, 0, PINION_Z0))
    mesh_opens = [OPEN_SMALL_LO, 0.5 * (OPEN_SMALL_LO + OPEN_DRIVE_HI), OPEN_DRIVE_HI]
    for op in mesh_opens:
        pin = pinion0.copy()
        pin.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), _driver_world_angle_deg(op))
        pin.translate(App.Vector(KNOB_X, KNOB_Y, 0))
        rack = make_slider_rack(op, g)
        ov = common_volume(pin, rack)
        max_ov = max(max_ov, ov)
        if ov > 25.0:
            mesh_ok = False
        for s in samples:
            if abs(s["open_mm"] - op) < 0.05:
                s["overlap_mm3"] = round(ov, 3)

    o0 = OPEN_SMALL_LO + 2.0
    o1 = o0 + 1.0
    d_knob = knob_angle_deg(o1) - knob_angle_deg(o0)
    step_1mm_ok = abs(d_knob - (360.0 / z)) < 1.0

    passed = bool(
        pitch_ok
        and fine_ok
        and tooth_step_ok
        and couple_ok
        and mesh_ok
        and step_1mm_ok
        and max_ov < 25.0
    )
    return {
        "pass": passed,
        "module": round(m, 4),
        "teeth": z,
        "circular_pitch_mm": round(p, 4),
        "travel_per_turn_mm": round(tpt, 4),
        "open_per_tooth_mm": round(open_per_tooth, 4),
        "knob_deg_per_1mm": round(360.0 / tpt, 2),
        "pitch_1mm_ok": pitch_ok,
        "fine_ring_ok": fine_ok,
        "tooth_step_1mm_ok": tooth_step_ok,
        "step_1mm_knob_ok": step_1mm_ok,
        "couple_ok": couple_ok,
        "mesh_ok": mesh_ok,
        "max_overlap_mm3": round(max_ov, 3),
        "knob_xy": [KNOB_X, round(KNOB_Y, 3)],
        "pitch_radius_mm": round(g["pitch_radius"], 3),
        "samples": samples,
        "note": "Small pinion: p≈1mm; knob turn slides Gap_Slider; check mesh overlap",
    }


def verify_mechanism(opens: list[float] | None = None) -> dict:
    if opens is None:
        # Sparse sweep — full involute knob is expensive per sample
        opens = [
            OPEN_SMALL_LO,
            3.0,
            OPEN_SMALL_HI,
            0.5 * (OPEN_TRANSIT_LO + OPEN_TRANSIT_HI),
            OPEN_TRANSIT_HI,
            OPEN_LARGE_LO + 2.0,
            OPEN_LARGE_HI,
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
        ang = malta_angle_for_open(op)
        aw = aperture_widths(op)
        malta = make_malta_cross(ang)
        driver = make_geneva_driver(op)
        # Avoid rebuilding involute pinion each sample (very slow boolean)
        slider = _slider_bar_probe(op)
        bar = slider
        aperture = make_aperture_plate(op)

        ov_af = common_volume(aperture, frame)
        ov_am = common_volume(aperture, malta)
        ov_sf = common_volume(slider, frame)
        ov_sm = common_volume(slider, malta)
        ov_sw = common_volume(bar, rail_walls)
        # Skip heavy knob∩malta boolean every sample — pose-only for knob
        ov_km = 0.0
        ov_dm = common_volume(driver, malta) if abs(op - THRESHOLD_MM) < 2.5 else 0.0

        in_transit = OPEN_TRANSIT_LO - 0.3 <= op <= OPEN_TRANSIT_HI + 0.3
        # Geneva pin/slot contact during transit is intentional
        ov_dm_ill = 0.0 if in_transit else (ov_dm if ov_dm > 15.0 else 0.0)
        ov_km_ill = 0.0 if ov_km < 8.0 else ov_km

        illegal = max(ov_af, ov_am, ov_sf, ov_sm, ov_sw, ov_dm_ill, ov_km_ill)
        max_illegal = max(max_illegal, illegal)
        max_overlap = max(max_overlap, illegal, ov_dm, ov_km)
        if illegal >= 8.0:
            jam_hits += 1

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
            if abs(ang - MALTA_ANGLE_SMALL) > 1.0 and op <= OPEN_TRANSIT_LO:
                state_ok = False
        else:
            if op >= OPEN_LARGE_LO and aw["large_mm"] < 0.5 and op > OPEN_LARGE_LO + 0.5:
                aperture_ok = False
            if abs(ang - MALTA_ANGLE_LARGE) > 1.0 and op >= OPEN_TRANSIT_HI:
                state_ok = False

        rows.append({
            "open_mm": round(op, 3),
            "state": state,
            "malta_deg": round(ang, 2),
            "knob_deg": round(knob_angle_deg(op), 2),
            "aperture": aw,
            "overlap_aperture_frame": round(ov_af, 3),
            "overlap_aperture_malta": round(ov_am, 3),
            "overlap_slider_frame": round(ov_sf, 3),
            "overlap_slider_malta": round(ov_sm, 3),
            "overlap_bar_rail_walls": round(ov_sw, 3),
            "overlap_driver_malta": round(ov_dm, 3),
            "overlap_knob_malta": round(ov_km, 3),
            "illegal_mm3": round(illegal, 3),
            "bar_zmin": round(float(bb.ZMin), 3),
            "rail_base_zmax": round(base_zmax, 3),
            "in_slot_y": in_slot_y,
            "on_rail_x": on_rail_x,
        })

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
        and max_illegal < 8.0
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
        "gear": {
            "module": GEAR_MODULE,
            "teeth": PINION_TEETH,
            "travel_per_turn": round(travel_per_turn(), 3),
        },
        "samples": rows,
    }


def build_l_flap_divert_parts(
    slider_open_mm: float = 3.0,
    prev_state: str | None = None,
    *,
    include_slider_gear: bool = True,
):
    state = flap_state_for_open(slider_open_mm, prev_state)
    ang = malta_angle_for_open(slider_open_mm)
    aw = aperture_widths(slider_open_mm)

    parts = [
        ("Divert_Frame", make_divert_frame(), (0.55, 0.58, 0.62)),
        ("Malta_Cross", make_malta_cross(ang), (0.20, 0.55, 0.85)),
        ("Geneva_Driver", make_geneva_driver(slider_open_mm), (0.95, 0.50, 0.12)),
    ]
    parts.extend(make_groove_guide_chutes())
    if include_slider_gear:
        gear_disc, g = make_gear_drive_disc(slider_open_mm)
        parts.append(("Gear_Drive_Disc", gear_disc, (0.75, 0.35, 0.15)))
        parts.append(("Drive_Knob", make_drive_knob(slider_open_mm), (0.85, 0.75, 0.25)))
        parts.extend(make_slider_rail_parts())
        parts.extend(
            [
                ("Gap_Slider", make_gap_slider(slider_open_mm), (0.55, 0.25, 0.70)),
                ("Knob_Shaft", make_knob_shaft_pin(), (0.45, 0.45, 0.50)),
            ]
        )
    else:
        # Still show large disc + pin (no rack) so Geneva looks complete
        gear_disc, g = make_gear_drive_disc(slider_open_mm)
        parts.append(("Gear_Drive_Disc", gear_disc, (0.75, 0.35, 0.15)))
        parts.append(("Drive_Knob", make_drive_knob(slider_open_mm), (0.85, 0.75, 0.25)))
    parts.append(("Pivot_Pin", make_pivot_pin(), (0.40, 0.40, 0.45)))
    parts.extend(make_lane_labels_proxy())

    print(
        "Grooves: small=%.1f large=%.1f | Malta 2-arm | Geneva a=%.1f | "
        "pinion m=%.1f z=%d (%.1f mm/turn) | slider_gear=%s"
        % (
            SMALL_GROOVE_W, LARGE_GROOVE_W, GENEVA_A,
            GEAR_MODULE, PINION_TEETH, g["travel_per_turn"],
            include_slider_gear,
        )
    )
    print(
        "bands S[%.1f..%.1f] T[%.1f..%.1f] L[%.1f..%.1f] | threshold=%.1f → close narrow / open wide"
        % (
            OPEN_SMALL_LO, OPEN_SMALL_HI,
            OPEN_TRANSIT_LO, OPEN_TRANSIT_HI,
            OPEN_LARGE_LO, OPEN_LARGE_HI,
            THRESHOLD_MM,
        )
    )
    print(
        "L_Flap_Divert: open=%.2f mm | state=%s | malta=%.1f deg | knob=%.1f deg | "
        "aperture small=%.2f large=%.2f active=%.2f"
        % (
            slider_open_mm, state, ang, knob_angle_deg(slider_open_mm),
            aw["small_mm"], aw["large_mm"], aw["active_width_mm"],
        )
    )
    return parts
