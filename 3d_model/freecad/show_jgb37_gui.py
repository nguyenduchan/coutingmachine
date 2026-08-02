"""
JGB37-520 geared DC motor + L mounting bracket — FreeCAD GUI.

Datasheet (Shopee GB37/JGB37-520, L=26.5 for ratio 131/168):
  Gearbox Ø37 x 26.5, 6xM3 PCD Ø31
  Boss Ø12 x 6, shaft OFFSET 7 mm from gearbox axis
  Shaft Ø6 D-flat 5.5, 15 mm past boss, flat 12 mm
  Motor can Ø33 x 22.7, rear boss Ø7.5, terminals pitch 24.9

Launch:
  freecad.exe 3d_model/freecad/show_jgb37_gui.py
"""

from __future__ import annotations

import math
import re
import sys
import zipfile
from pathlib import Path

# Windows freecadcmd defaults to cp1252 — unicode in print() aborts the rebuild mid-model
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import FreeCAD as App
import Part

try:
    import FreeCADGui as Gui
except ImportError:
    Gui = None

try:
    _HERE = Path(__file__).resolve().parent
except NameError:
    _HERE = Path(r"c:\workspace\embedded\CountingMachine\3d_model\freecad")
OUT = _HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)
FCSTD = OUT / "jgb37_motor_bracket.FCStd"

# Geometric settings (edit box_settings.py — sizes + shapes)
import box_settings as BX
from box_settings import DISC as _DISC_CFG
from box_settings import HUB as _HUB_CFG
from box_settings import LID as _LID_CFG
from box_settings import lid_plan_full as _lid_plan_full

# ---- Motor datasheet (mm) ----
GB_D, GB_L = 37.0, 26.5
MOUNT_PCD = 31.0
BOSS_D, BOSS_H = 12.0, 6.0
SHAFT_OFFSET = 7.0  # eccentric — NOT center shaft
SHAFT_D, SHAFT_FLAT = 6.0, 5.5
SHAFT_L, SHAFT_FLAT_L = 15.0, 12.0
CAN_D, CAN_L = 33.0, 22.7
REAR_BOSS_D, REAR_BOSS_H = 7.5, 3.0
TERM_PITCH, TERM_L, TERM_W, TERM_T = 24.9, 6.5, 3.0, 0.6

# ---- L-bracket (GB37 face mount) ----
BR_T, BR_W = 2.5, 40.0
BR_VERT_H, BR_BASE_D = 48.0, 40.0
BR_SLOT_W, BR_SLOT_H = 14.0, 26.0  # stadium for offset boss
BR_MOUNT_HOLE, BR_BASE_HOLE = 3.5, 4.5
BR_BASE_MARGIN = 6.0


def make_motor() -> Part.Shape:
    """
    Shaft +Z. Gearbox front at z=0.
    Boss/shaft axis offset +Y by SHAFT_OFFSET (7 mm eccentric).
    """
    gb = Part.makeCylinder(GB_D / 2, GB_L)
    gb.translate(App.Vector(0, 0, -GB_L))

    motor = gb
    for i in range(6):
        a = math.radians(i * 60)
        x = (MOUNT_PCD / 2) * math.cos(a)
        y = (MOUNT_PCD / 2) * math.sin(a)
        d = 3.0 if (i % 2 == 0) else 4.0
        depth = 3.5 if (i % 2 == 0) else GB_L
        hole = Part.makeCylinder(d / 2, depth)
        hole.translate(App.Vector(x, y, -depth))
        motor = motor.cut(hole)

    boss = Part.makeCylinder(BOSS_D / 2, BOSS_H)
    boss.translate(App.Vector(0, SHAFT_OFFSET, 0))

    shaft = Part.makeCylinder(SHAFT_D / 2, SHAFT_L)
    shaft.translate(App.Vector(0, SHAFT_OFFSET, BOSS_H))
    flat = Part.makeBox(SHAFT_D + 2, 4.0, SHAFT_FLAT_L + 0.2)
    flat.translate(
        App.Vector(
            -SHAFT_D / 2 - 1,
            SHAFT_OFFSET + SHAFT_FLAT / 2,
            BOSS_H + SHAFT_L - SHAFT_FLAT_L,
        )
    )
    shaft = shaft.cut(flat)

    can = Part.makeCylinder(CAN_D / 2, CAN_L)
    can.translate(App.Vector(0, 0, -GB_L - CAN_L))
    rear = Part.makeCylinder(REAR_BOSS_D / 2, REAR_BOSS_H)
    rear.translate(App.Vector(0, 0, -GB_L - CAN_L - REAR_BOSS_H))

    motor = motor.fuse(boss).fuse(shaft).fuse(can).fuse(rear)
    for sx in (-1.0, 1.0):
        t = Part.makeBox(TERM_W, TERM_T, TERM_L)
        t.translate(
            App.Vector(
                sx * TERM_PITCH / 2 - TERM_W / 2,
                -TERM_T / 2,
                -GB_L - CAN_L - TERM_L,
            )
        )
        motor = motor.fuse(t)
    return motor.removeSplitter()


def stadium_face(width: float, height: float, cx=0.0, cy=0.0) -> Part.Face:
    r = width / 2.0
    straight = height - width
    p1 = App.Vector(cx + r, cy + straight / 2, 0)
    p2 = App.Vector(cx - r, cy + straight / 2, 0)
    p3 = App.Vector(cx - r, cy - straight / 2, 0)
    p4 = App.Vector(cx + r, cy - straight / 2, 0)
    top = Part.Arc(p1, App.Vector(cx, cy + height / 2, 0), p2).toShape()
    left = Part.LineSegment(p2, p3).toShape()
    bot = Part.Arc(p3, App.Vector(cx, cy - height / 2, 0), p4).toShape()
    right = Part.LineSegment(p4, p1).toShape()
    return Part.Face(Part.Wire([top, left, bot, right]))


def make_bracket() -> Part.Shape:
    half_w = BR_W / 2.0
    rect_h = BR_VERT_H - half_w
    cy = half_w  # mount / gearbox center height on plate

    edges = [
        Part.LineSegment(App.Vector(-half_w, 0, 0), App.Vector(half_w, 0, 0)).toShape(),
        Part.LineSegment(App.Vector(half_w, 0, 0), App.Vector(half_w, rect_h, 0)).toShape(),
        Part.Arc(
            App.Vector(half_w, rect_h, 0),
            App.Vector(0, BR_VERT_H, 0),
            App.Vector(-half_w, rect_h, 0),
        ).toShape(),
        Part.LineSegment(App.Vector(-half_w, rect_h, 0), App.Vector(-half_w, 0, 0)).toShape(),
    ]
    vert = Part.Face(Part.Wire(edges)).extrude(App.Vector(0, 0, BR_T))

    slot = stadium_face(BR_SLOT_W, BR_SLOT_H, 0, cy).extrude(App.Vector(0, 0, BR_T + 0.4))
    slot.translate(App.Vector(0, 0, -0.2))
    vert = vert.cut(slot)

    # Same PCD / angles / diameters as motor face (Ø3 M3 / Ø4 through)
    for i in range(6):
        a = math.radians(i * 60)
        hx = (MOUNT_PCD / 2) * math.cos(a)
        hy = cy + (MOUNT_PCD / 2) * math.sin(a)
        d = 3.0 if (i % 2 == 0) else 4.0
        hole = Part.makeCylinder(d / 2, BR_T + 0.4)
        hole.translate(App.Vector(hx, hy, -0.2))
        vert = vert.cut(hole)

    vert.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), 90)

    base = Part.makeBox(BR_W, BR_BASE_D, BR_T)
    base.translate(App.Vector(-half_w, 0, 0))
    m = BR_BASE_MARGIN
    for sx in (-1.0, 1.0):
        for by in (m, BR_BASE_D - m):
            hole = Part.makeCylinder(BR_BASE_HOLE / 2, BR_T + 0.4)
            hole.translate(App.Vector(sx * (half_w - m), by, -0.2))
            base = base.cut(hole)

    return base.fuse(vert).removeSplitter()


# ---- Vertical drive + Rx-4 Manual Gate upper (from video CM4_RVPX__8) ----
DISC_D = float(_DISC_CFG["diameter"])
DISC_T = float(_DISC_CFG["thickness"])
DRIVE_SHAFT_D = 6.0
BEARING_OD, BEARING_ID, BEARING_H = 19.0, 6.0, 6.0  # 626ZZ
COUPLER_OD, COUPLER_L = 18.0, 25.0
HUB_D, HUB_H = float(_HUB_CFG["diameter"]), float(_HUB_CFG["height"])

# Housing footprint — outer W×D from box_settings.HOUSING (20×20 cm)
GUIDE_WALL = float(BX.GUIDE["wall_radial_thickness"])
_OUTER_GUIDE_SIDE = (DISC_D + float(BX.GUIDE["bore_clearance_on_disc"])) + 2.0 * GUIDE_WALL
BOX_PAD = float(BX.HOUSING.get("pad_around_guide", 6.0))
_BOX_FROM_GUIDE = _OUTER_GUIDE_SIDE + 2.0 * BOX_PAD
BOX_W = float(BX.HOUSING.get("outer_width", _BOX_FROM_GUIDE))
BOX_D = float(BX.HOUSING.get("outer_depth", _BOX_FROM_GUIDE))
BOX_T = float(BX.HOUSING["wall_thickness"])
# Keep SAME placement rule as before: face_z = SHELF_Z - 8 - COUPLER_L
# Raise shelf so motor body (below face) clears floor.
MOTOR_BODY_LEN = GB_L + CAN_L + REAR_BOSS_H + TERM_L  # ~58.7
SHELF_Z = BOX_T + MOTOR_BODY_LEN + COUPLER_L + 8.0 + 12.0  # ~108
BOX_H = SHELF_Z + 75.0
TOP_Z = BOX_H
SPAN = TOP_Z - SHELF_Z
FACE_Z = SHELF_Z - 8.0 - COUPLER_L  # identical formula as previous place_motor_vertical

# Manual lining-up gate (YouTube: "Lining up mechanism 1")
GATE_GAP = float(BX.GATE["nominal_gap"])
GATE_GAP_MAX = float(BX.GATE["gap_max"])
GATE_BEVEL = 18.0
KNOB_D, KNOB_H = 28.0, 14.0
JAW_T = 4.0
JAW_LEN = 42.0
EXIT_Y = float(BX.GATE["exit_y"])
# Disc access lid — from box_settings.LID
LID_DISC_CLEAR = float(_LID_CFG["disc_clear"])
LID_TOP_T = float(_LID_CFG["top_thickness"])
LID_WALL_T = float(_LID_CFG["wall_thickness"])
LID_WALL_H = float(_LID_CFG["wall_height"])
LID_STACK_H = float(_LID_CFG["stack_height"])
LID_WIDTH_BAR_H = float(_LID_CFG["width_bar"]["height"])
LID_HEIGHT_BAR_H = float(_LID_CFG["height_bar"]["height"])
LID_HEIGHT_BAR_T = float(_LID_CFG["height_bar"]["thickness"])
_LID_BOT = _LID_CFG["plan"].get("bottom_plate", {})
LID_BOTTOM_EN = bool(_LID_BOT.get("enabled", True))
LID_BOTTOM_T = float(_LID_BOT.get("thickness", LID_TOP_T))
LID_BOTTOM_DISC_CLR = float(_LID_BOT.get("disc_clearance", 0.5))
LID_BOTTOM_OPEN_CHUTE = bool(_LID_BOT.get("open_over_chute", True))
_LID_FILL = _LID_CFG["plan"].get("annulus_fill", {})
LID_FILL_EN = bool(_LID_FILL.get("enabled", True))
# Exit tray — Left straight | Right = 1/4 Ø10cm + straight
# FROZEN placement (do not change unless user explicitly asks to move):
EXIT_TRAY_ARC_D = float(BX.EXIT_TRAY["arc_diameter"])
EXIT_TRAY_ARC_R = EXIT_TRAY_ARC_D / 2.0
EXIT_TRAY_CH_W = float(BX.EXIT_TRAY["channel_width"])
EXIT_TRAY_STRAIGHT_LEN = float(BX.EXIT_TRAY["straight_length"])
EXIT_TRAY_WALL_H = float(BX.EXIT_TRAY["wall_height"])
EXIT_TRAY_FLOOR_T = float(BX.EXIT_TRAY["floor_thickness"])
EXIT_TRAY_WALL_T = float(BX.EXIT_TRAY["wall_thickness"])
# Đế rộng hơn thành theo chiều ngang (mỗi bên) — shape only
EXIT_TRAY_FLOOR_SIDE_PAD = float(BX.EXIT_TRAY["floor_side_pad"])
# Thành ngắn lại: mép trước tường cách cạnh ngang trước của đế 3 cm — shape only
EXIT_TRAY_WALL_FRONT_CLEAR = float(BX.EXIT_TRAY["wall_front_clear"])
EXIT_TRAY_ARC_CX = float(BX.EXIT_TRAY["arc_cx_local"])
EXIT_TRAY_ARC_CY = float(BX.EXIT_TRAY["arc_cy_local"])
# Recirculation: leave rim path open so pills can skip gap and go another loop
EXIT_TRAY_RECYC_GAP = float(BX.EXIT_TRAY["recycle_gap"])
EXIT_TRAY_DISC_CLEAR = float(BX.EXIT_TRAY["disc_clear"])
EXIT_TRAY_ARC_A0 = float(BX.EXIT_TRAY["arc_a0_deg"])
EXIT_TRAY_ARC_A1 = float(BX.EXIT_TRAY["arc_a1_deg"])
# Gap curved guard (Ø10cm, concentric with exit tray right arc)
GAP_CURVE_T = float(BX.GAP["curve_thickness"])
GAP_CURVE_A0, GAP_CURVE_A1 = float(BX.GAP["curve_a0_deg"]), float(BX.GAP["curve_a1_deg"])
# Max radial open from hug pose (2 cm) — left wall tip meets guard at this stroke
GAP_CURVE_STROKE_MAX = float(BX.GAP["stroke_max"])
GAP_RACK_MODULE = float(BX.GAP["rack_module"])
GAP_PINION_TEETH = int(BX.GAP["pinion_teeth"])
GAP_RAIL_CLEAR = 0.4
GAP_RAIL_WALL = 2.5
# Exit press / reject: ép viên vào khe hoặc cho trượt vòng lại
PRESS_FINGER_H = float(BX.PRESS["finger_height"])
PRESS_FINGER_T = float(BX.PRESS["finger_thickness"])
PRESS_TIP_R = float(BX.PRESS["tip_radius"])
PRESS_BYPASS_DR = float(BX.PRESS["bypass_dr"])










def _cyl_z(d: float, h: float, z0: float, x=0.0, y=0.0) -> Part.Shape:
    c = Part.makeCylinder(d / 2, h)
    c.translate(App.Vector(x, y, z0))
    return c


def make_box_frame() -> Part.Shape:
    """
    Housing sized to Outer_Guide_Arc footprint (centered on disc axis).
    """
    ox = -BOX_W / 2.0
    oy = -BOX_D / 2.0
    outer = Part.makeBox(BOX_W, BOX_D, BOX_H)
    outer.translate(App.Vector(ox, oy, 0))

    inner = Part.makeBox(BOX_W - 2 * BOX_T, BOX_D - 2 * BOX_T, BOX_H - BOX_T + 1)
    inner.translate(App.Vector(ox + BOX_T, oy + BOX_T, BOX_T))
    shell = outer.cut(inner)

    lid = Part.makeBox(BOX_W, BOX_D, BOX_T)
    lid.translate(App.Vector(ox, oy, TOP_Z))
    # Full square outer — no disc hole / exit notch

    shelf = Part.makeBox(BOX_W - 2 * BOX_T - 4, BOX_D - 2 * BOX_T - 4, BOX_T)
    shelf.translate(App.Vector(ox + BOX_T + 2, oy + BOX_T + 2, SHELF_Z))
    shelf = shelf.cut(_cyl_z(BEARING_OD + 0.3, BOX_T + 1, SHELF_Z - 0.5))

    drawer_cut = Part.makeBox(90, 22, 50)
    drawer_cut.translate(App.Vector(-45, oy + BOX_D - BOX_T - 4, 25))
    shell = shell.cut(drawer_cut)

    print(
        "Housing_Shell outer=%.0fx%.0f mm (22x22 cm) | Outer_Guide side=%.1f"
        % (BOX_W, BOX_D, _OUTER_GUIDE_SIDE)
    )
    return shell.fuse(lid).fuse(shelf)


def place_bracket_only(face_z: float) -> Part.Shape:
    """L-bracket: face-plate PCD centered on gearbox axis (0, -SHAFT_OFFSET)."""
    b = make_bracket()
    b.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), -90)
    # Plate-local gearbox center is y = BR_W/2; map onto motor gearbox axis
    cy = BR_W / 2.0
    b.translate(App.Vector(0, -SHAFT_OFFSET - cy, face_z - BR_T))
    return b


def motor_face_holes_world() -> list[tuple[float, float, float]]:
    """
    JGB37 face holes after place_motor_vertical — same as make_motor():
      PCD Ø31, angles i*60°, Ø3.0 (even i, M3) / Ø4.0 (odd i, through).
    Returns (x, y, diameter).
    """
    holes = []
    for i in range(6):
        a = math.radians(i * 60)
        x = (MOUNT_PCD / 2) * math.cos(a)
        y = (MOUNT_PCD / 2) * math.sin(a) - SHAFT_OFFSET
        d = 3.0 if (i % 2 == 0) else 4.0
        holes.append((x, y, d))
    return holes


def apply_motor_face_holes(shape: Part.Shape, face_z: float) -> Part.Shape:
    """
    Cut ONLY the 6 JGB37 face holes (+ eccentric boss slot) into the mount lid.
    Positions/diameters identical to make_motor() after place_motor_vertical.
    """
    for x, y, d in motor_face_holes_world():
        hole = Part.makeCylinder(d / 2.0, MOUNT_TOP_T + 4.0)
        hole.translate(App.Vector(x, y, face_z - 1.0))
        shape = shape.cut(hole)

    # Eccentric boss Ø12 at shaft axis (0,0); stadium matches L-bracket slot
    slot = stadium_face(BR_SLOT_W, BR_SLOT_H, 0.0, -SHAFT_OFFSET)
    slot_solid = slot.extrude(App.Vector(0, 0, MOUNT_TOP_T + 4.0))
    slot_solid.translate(App.Vector(0, 0, face_z - 1.0))
    shape = shape.cut(slot_solid)

    boss_clear = Part.makeCylinder(BOSS_D / 2.0 + 0.3, MOUNT_TOP_T + 4.0)
    boss_clear.translate(App.Vector(0.0, 0.0, face_z - 1.0))
    shape = shape.cut(boss_clear)
    return shape


def make_hole_align_pins(face_z: float) -> Part.Shape:
    """Thin pins on motor hole axes for visual alignment check (GUI only)."""
    pins = None
    for x, y, d in motor_face_holes_world():
        pin = Part.makeCylinder(max(d / 2.0 - 0.35, 0.6), MOUNT_TOP_T + GB_L * 0.35)
        pin.translate(App.Vector(x, y, face_z - GB_L * 0.25))
        pins = pin if pins is None else pins.fuse(pin)
    return pins.removeSplitter()


# Top flange — motor face screws only (mount is fused into housing)
MOUNT_TOP_T = 6.0
MOUNT_AIR_GAP = 5.0
MOUNT_WALL = 4.5
MOUNT_BOX_EXTRA = 4.0
MOUNT_BRACE_W = 8.0


def _keep_largest_solid(shape: Part.Shape) -> Part.Shape:
    if shape is None or getattr(shape, "isNull", lambda: False)():
        return shape
    solids = list(shape.Solids)
    if len(solids) <= 1:
        return shape
    solids.sort(key=lambda s: abs(float(s.Volume)), reverse=True)
    return solids[0]


def _safe_refine(shape: Part.Shape) -> Part.Shape:
    """removeSplitter can throw Bnd_Box is void on helix fusions — keep raw solid."""
    if shape is None or getattr(shape, "isNull", lambda: False)():
        return shape
    try:
        out = shape.removeSplitter()
        if out is None or out.isNull():
            return shape
        return out
    except Exception:
        return shape


def mount_layout(face_z: float) -> dict:
    gx, gy = 0.0, -SHAFT_OFFSET
    inner = GB_D + 2.0 * MOUNT_AIR_GAP + MOUNT_BOX_EXTRA
    wall = MOUNT_WALL
    outer_w = inner + 2.0 * wall
    outer_d = inner + wall
    ox = gx - outer_w / 2.0
    oy = gy - inner / 2.0
    body_len = GB_L + CAN_L + REAR_BOSS_H + TERM_L + 8.0
    z_bot = face_z - body_len
    z_lid = face_z + MOUNT_TOP_T
    return {
        "gx": gx,
        "gy": gy,
        "inner": inner,
        "wall": wall,
        "outer_w": outer_w,
        "outer_d": outer_d,
        "ox": ox,
        "oy": oy,
        "z_bot": z_bot,
        "z_lid": z_lid,
    }


def make_l_bracket_mount_core(face_z: float) -> Part.Shape:
    """
    Motor mount structure grown from housing floor (no separate fasteners).
    Square pocket, open -Y, thick lid with motor screw holes, braces to shelf.
    """
    L = mount_layout(face_z)
    gx, gy = L["gx"], L["gy"]
    inner, wall = L["inner"], L["wall"]
    outer_w, outer_d = L["outer_w"], L["outer_d"]
    ox, oy = L["ox"], L["oy"]
    z_bot, z_lid = L["z_bot"], L["z_lid"]
    h_all = z_lid - z_bot
    cav_h = face_z - z_bot
    half_w = BR_W / 2.0
    cy = half_w

    # Continuous stem from floor up into motor box (one solid with housing after fuse)
    stem = Part.makeBox(outer_w, outer_d, z_lid - BOX_T)
    stem.translate(App.Vector(ox, oy, BOX_T))

    # L-outline lid deck
    edges = [
        Part.LineSegment(App.Vector(-half_w, 0, 0), App.Vector(half_w, 0, 0)).toShape(),
        Part.LineSegment(
            App.Vector(half_w, 0, 0), App.Vector(half_w, BR_VERT_H - half_w, 0)
        ).toShape(),
        Part.Arc(
            App.Vector(half_w, BR_VERT_H - half_w, 0),
            App.Vector(0, BR_VERT_H, 0),
            App.Vector(-half_w, BR_VERT_H - half_w, 0),
        ).toShape(),
        Part.LineSegment(
            App.Vector(-half_w, BR_VERT_H - half_w, 0), App.Vector(-half_w, 0, 0)
        ).toShape(),
    ]
    lid = Part.Face(Part.Wire(edges)).extrude(App.Vector(0, 0, MOUNT_TOP_T))
    lid.translate(App.Vector(0, -SHAFT_OFFSET - cy, face_z))

    # Braces ±X from floor to shelf (integral stiffeners)
    braces = None
    for px in (ox - MOUNT_BRACE_W, ox + outer_w):
        brace = Part.makeBox(MOUNT_BRACE_W, outer_d, SHELF_Z - BOX_T)
        brace.translate(App.Vector(px, oy, BOX_T))
        braces = brace if braces is None else braces.fuse(brace)

    # Back web to shelf / floor
    web = Part.makeBox(outer_w + 2.0 * MOUNT_BRACE_W, wall, SHELF_Z - BOX_T)
    web.translate(App.Vector(ox - MOUNT_BRACE_W, oy + outer_d - wall, BOX_T))

    # Floor fillet pad (spreads into housing floor when fused)
    pad_w = outer_w + 2.0 * MOUNT_BRACE_W + 20.0
    pad_d = outer_d + 12.0
    pad = Part.makeBox(pad_w, pad_d, 3.0)
    pad.translate(App.Vector(gx - pad_w / 2.0, oy - 2.0, BOX_T))

    mono = stem.fuse(lid).fuse(braces).fuse(web).fuse(pad)

    # Square cavity under lid + open -Y
    cavity = Part.makeBox(inner, inner, cav_h)
    cavity.translate(App.Vector(gx - inner / 2.0, gy - inner / 2.0, z_bot))
    mono = mono.cut(cavity)

    tunnel = Part.makeBox(inner + 1.0, outer_d + 50.0, cav_h)
    tunnel.translate(App.Vector(gx - (inner + 1.0) / 2.0, gy - inner / 2.0 - 50.0, z_bot))
    mono = mono.cut(tunnel)

    # Also open tunnel through stem below z_bot for service path continuity
    if z_bot > BOX_T + 1.0:
        under = Part.makeBox(inner + 1.0, outer_d + 50.0, z_bot - BOX_T)
        under.translate(
            App.Vector(gx - (inner + 1.0) / 2.0, gy - inner / 2.0 - 50.0, BOX_T)
        )
        mono = mono.cut(under)

    # Wall vents only (no extra lid holes — those looked like wrong motor holes)
    vent_h = cav_h * 0.55
    vent_z0 = z_bot + (cav_h - vent_h) * 0.5
    vw, vd = 12.0, wall + 6.0
    for dx, dy, sx, sy in (
        (gx + inner / 2.0 - 1.0, gy - vw / 2.0, vd, vw),
        (gx - inner / 2.0 - vd + 1.0, gy - vw / 2.0, vd, vw),
        (gx - vw / 2.0, gy + inner / 2.0 - 1.0, vw, vd),
    ):
        v = Part.makeBox(sx, sy, vent_h)
        v.translate(App.Vector(dx, dy, vent_z0))
        mono = mono.cut(v)

    mono = apply_motor_face_holes(mono, face_z)
    print(
        "Mount face holes (=motor): "
        + ", ".join("D%.1f@(%.2f,%.2f)" % (d, x, y) for x, y, d in motor_face_holes_world())
    )
    return _keep_largest_solid(mono.removeSplitter())


def make_housing_with_mount(face_z: float) -> Part.Shape:
    """Housing + L_Bracket_Mount_Frame as ONE continuous solid (no joints)."""
    frame = make_box_frame()
    mount = make_l_bracket_mount_core(face_z)
    mono = frame.fuse(mount)
    # Re-apply after fuse so housing cannot fill motor holes
    mono = apply_motor_face_holes(mono, face_z)
    mono = _keep_largest_solid(mono.removeSplitter())

    # Verify coaxial with placed motor pattern
    ok = True
    for i, (x, y, d) in enumerate(motor_face_holes_world()):
        p = App.Vector(x, y, face_z + MOUNT_TOP_T / 2.0)
        dist = mono.distToShape(Part.Vertex(p))[0]
        # center of a through-hole is ~d/2 from wall
        if abs(dist - d / 2.0) > 0.15:
            ok = False
            print("WARN hole i=%d D%.1f dist=%.3f expected~%.3f" % (i, d, dist, d / 2.0))
    print(
        "Housing+mount ONE solid | motor holes verify=%s (PCD31 D3/D4, no lid vents)"
        % ("PASS" if ok else "FAIL")
    )
    return mono


def place_motor_vertical(motor: Part.Shape) -> Part.Shape:
    """Motor pose unchanged: shaft +Z, eccentric corrected."""
    m = motor.copy()
    m.translate(App.Vector(0, -SHAFT_OFFSET, 0))
    face_z = SHELF_Z - 8.0 - COUPLER_L
    m.translate(App.Vector(0, 0, face_z))
    return m


def make_coupler(z0: float) -> Part.Shape:
    body = _cyl_z(COUPLER_OD, COUPLER_L, z0)
    return body.cut(_cyl_z(DRIVE_SHAFT_D + 0.2, COUPLER_L + 1, z0 - 0.5))


def make_drive_shaft(z0: float, length: float) -> Part.Shape:
    return _cyl_z(DRIVE_SHAFT_D, length, z0)


def make_bearing(z0: float) -> Part.Shape:
    return _cyl_z(BEARING_OD, BEARING_H, z0).cut(
        _cyl_z(BEARING_ID + 0.05, BEARING_H + 0.2, z0 - 0.1)
    )


def make_disc(z0: float) -> Part.Shape:
    disc = _cyl_z(DISC_D, DISC_T, z0).cut(
        _cyl_z(DRIVE_SHAFT_D + 0.1, DISC_T + 1, z0 - 0.5)
    )
    return disc


def make_center_hub(z0: float) -> Part.Shape:
    """Black textured hub on disc center (Rx-4)."""
    hub = _cyl_z(HUB_D, HUB_H, z0 + DISC_T)
    # scallops
    for i in range(12):
        a = math.radians(i * 30)
        hx = (HUB_D / 2 - 2) * math.cos(a)
        hy = (HUB_D / 2 - 2) * math.sin(a)
        hub = hub.cut(_cyl_z(4.0, HUB_H + 1, z0 + DISC_T - 0.5, hx, hy))
    return hub.cut(_cyl_z(DRIVE_SHAFT_D + 0.2, HUB_H + 1, z0 + DISC_T - 0.5))


def _guide_dims():
    """Outer_guide envelope: wall, bore Ø, outer side length."""
    wall = GUIDE_WALL
    bore_d = DISC_D + 0.5
    side = bore_d + 2.0 * wall
    return wall, bore_d, side


def _annular_sector(
    r_in: float, r_out: float, deg0: float, deg1: float, z0: float, h: float
) -> Part.Shape:
    """Solid ring sector [deg0, deg1] deg, CCW from +X, extruded along +Z."""
    a0 = math.radians(deg0)
    a1 = math.radians(deg1)
    n = max(3, int(round(abs(deg1 - deg0))))
    outer = [
        App.Vector(r_out * math.cos(a0 + (a1 - a0) * i / n), r_out * math.sin(a0 + (a1 - a0) * i / n), z0)
        for i in range(n + 1)
    ]
    inner = [
        App.Vector(r_in * math.cos(a1 - (a1 - a0) * i / n), r_in * math.sin(a1 - (a1 - a0) * i / n), z0)
        for i in range(n + 1)
    ]
    wire = Part.makePolygon(outer + inner + [outer[0]])
    return Part.Face(wire).extrude(App.Vector(0, 0, h))


def make_outer_guide_parts(z_disc: float) -> list[tuple[str, Part.Shape, tuple]]:
    """
    Split Outer_guide into editable components:
      - Outer_Guide_Floor: one circular base disc (shaft hole)
      - Outer_Guide_Wall_xxx: wall ring sectors every 10° (full 360°)

    Where the lid straight chute crosses the ring, those wall sectors are
    cut open (GUIDE.cut_straight_chute) so the channel is not blocked.
    """
    wall, bore_d, _side = _guide_dims()
    r_in = bore_d / 2.0
    r_out = r_in + wall
    floor_t = DISC_T
    z_floor = z_disc - floor_t
    wall_h = 26.0
    step = 10  # degrees

    parts: list[tuple[str, Part.Shape, tuple]] = []

    # 1) Circular floor disc
    floor = _cyl_z(2.0 * r_out, floor_t, z_floor)
    floor = floor.cut(_cyl_z(DRIVE_SHAFT_D + 0.3, floor_t + 2.0, z_floor - 1.0))
    parts.append(("Outer_Guide_Floor", _keep_largest_solid(floor.removeSplitter()), (0.18, 0.18, 0.2)))

    # Chute cutout prism (expanded) — punches through ring where red chute crosses
    chute_cutter = None
    guide_cfg = BX.GUIDE
    if bool(guide_cfg.get("cut_straight_chute", True)):
        try:
            plan = _lid_plan_points()
            pad = float(guide_cfg.get("chute_cut_pad", 1.0))
            n_in, n_out = plan["n_in"], plan["n_out"]
            e_in, e_out = plan["e_in"], plan["e_out"]
            # Expand chute polygon outward by pad (along ±X) so wall thickness clears
            x_lo = min(float(n_in[0]), float(n_out[0]), float(e_in[0]), float(e_out[0])) - pad
            x_hi = max(float(n_in[0]), float(n_out[0]), float(e_in[0]), float(e_out[0])) + pad
            y_hi = max(float(n_in[1]), float(n_out[1])) + pad
            y_lo = min(float(e_in[1]), float(e_out[1])) - pad
            chute_xy = [
                (x_hi, y_hi),
                (x_hi, y_lo),
                (x_lo, y_lo),
                (x_lo, y_hi),
            ]
            chute_cutter = _prism_from_xy(chute_xy, z_disc - 1.0, wall_h + 2.0)
        except Exception as exc:
            print("Outer_Guide chute cut skipped:", exc)
            chute_cutter = None

    # 2) Wall sectors every 10° — cut open where chute crosses
    cut_n = 0
    for i in range(0, 360, step):
        seg = _annular_sector(r_in, r_out, float(i), float(i + step), z_disc, wall_h)
        if chute_cutter is not None:
            try:
                before = float(seg.Volume)
                seg = seg.cut(chute_cutter).removeSplitter()
                if float(seg.Volume) < before - 1.0:
                    cut_n += 1
            except Exception:
                pass
        kept = _fuse_significant_solids(seg, min_vol=0.5)
        if kept is None or not kept.Solids:
            continue  # sector fully removed by chute cut
        name = "Outer_Guide_Wall_%03d" % i
        parts.append((name, kept, (0.12, 0.12, 0.14)))

    print(
        "Outer_guide split: Floor + %d wall sectors @ %d° | chute_cut sectors=%d"
        % (len(parts) - 1, step, cut_n)
    )
    return parts


def make_outer_guide_arc(z_disc: float) -> Part.Shape:
    """Fused Outer_guide (compat). Prefer make_outer_guide_parts for editing."""
    fused = None
    for _name, shape, _color in make_outer_guide_parts(z_disc):
        fused = shape if fused is None else fused.fuse(shape)
    return _keep_largest_solid(fused.removeSplitter())


def _cyl_along_xy(
    x0: float,
    y0: float,
    z0: float,
    ux: float,
    uy: float,
    length: float,
    radius: float,
) -> Part.Shape:
    """Cylinder starting at (x0,y0,z0), axis along unit (ux,uy) in XY."""
    c = Part.makeCylinder(radius, length)
    c.rotate(App.Vector(0, 0, 0), App.Vector(0, 1, 0), 90)  # +Z -> +X
    ang = math.degrees(math.atan2(uy, ux))
    c.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), ang)
    c.translate(App.Vector(x0, y0, z0))
    return c


def _involute_pinion(
    module: float,
    teeth: int,
    thickness: float,
    bore: float,
) -> Part.Shape:
    """Simple printable spur gear (approx teeth as radial boxes)."""
    pd = module * float(teeth)
    tip_r = pd / 2.0 + module
    root_r = max(bore / 2.0 + 1.0, pd / 2.0 - 1.25 * module)
    tooth_h = tip_r - root_r
    tooth_w = max(0.8, 0.5 * math.pi * module)
    hub = Part.makeCylinder(root_r, thickness)
    gear = hub
    for i in range(teeth):
        a = math.radians(i * 360.0 / teeth)
        t = Part.makeBox(tooth_h + 0.2, tooth_w, thickness)
        t.translate(App.Vector(root_r - 0.1, -tooth_w / 2.0, 0.0))
        t.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), math.degrees(a))
        gear = gear.fuse(t)
    if bore > 0.5:
        gear = gear.cut(Part.makeCylinder(bore / 2.0, thickness + 2.0))
    return _keep_largest_solid(gear.removeSplitter())


def _make_rack(
    module: float,
    n_teeth: int,
    width: float,
    height: float,
    stem_w: float,
    stem_h: float,
    flange_w: float,
    flange_h: float,
) -> tuple[Part.Shape, float]:
    """
    Removable rack: bar + side teeth (+Y) + T-foot under bar.
    Local: +X length, body Y in [0, width], Z in [0, height];
    T-foot below Z=0. Returns (shape, length).
    """
    pitch = math.pi * module
    length = n_teeth * pitch + pitch
    tooth_h = 1.5 * module
    tooth_w = max(0.8, 0.5 * math.pi * module)
    bar = Part.makeBox(length, width, height)
    # T-foot: stem then wide flange (anti-lift / anti-twist in rail)
    stem = Part.makeBox(length, stem_w, stem_h)
    stem.translate(App.Vector(0.0, (width - stem_w) / 2.0, -stem_h))
    flange = Part.makeBox(length, flange_w, flange_h)
    flange.translate(
        App.Vector(0.0, (width - flange_w) / 2.0, -(stem_h + flange_h))
    )
    rack = bar.fuse(stem).fuse(flange)
    for i in range(n_teeth):
        x = pitch * 0.5 + i * pitch - tooth_w / 2.0
        t = Part.makeBox(tooth_w, tooth_h + 0.1, height * 0.9)
        t.translate(App.Vector(x, width - 0.05, height * 0.05))
        rack = rack.fuse(t)
    # Pull tab at outer (+X) end — grab to slide rack out of open rail
    tab = Part.makeBox(8.0, width + 2.0, height * 0.55)
    tab.translate(App.Vector(length - 1.0, -1.0, height * 0.2))
    rack = rack.fuse(tab)
    # Carrier tongue at inner (−X): seats in guard socket (radial slide-in)
    tongue = Part.makeBox(7.0, width + 2.0, height)
    tongue.translate(App.Vector(-5.0, -1.0, 0.0))
    rack = rack.fuse(tongue)
    return _keep_largest_solid(rack.removeSplitter()), length


def _make_rack_rail(
    length: float,
    rack_w: float,
    rack_h: float,
    stem_w: float,
    stem_h: float,
    flange_w: float,
    flange_h: float,
    clear: float,
    wall: float,
    tooth_h: float,
) -> Part.Shape:
    """
    T-slot rail along +X. Open at outer (+X) end so Gap_Rack slides out.
    -Y wall full height; +Y wall low (teeth + pinion mesh stay clear).
    Local origin: rack body Y in [0, rack_w], Z in [0, rack_h] (same as rack).
    """
    foot_h = stem_h + flange_h
    # Outer envelope
    out_w = max(flange_w, rack_w) + 2.0 * wall + 2.0 * clear
    out_h = foot_h + rack_h + wall
    y0 = (rack_w - out_w) / 2.0
    z0 = -(foot_h + clear)
    body = Part.makeBox(length, out_w, out_h)
    body.translate(App.Vector(0.0, y0, z0))

    # T-cavity: wide flange pocket + stem neck + body tunnel
    cav_fl_w = flange_w + 2.0 * clear
    cav_fl_h = flange_h + clear
    cav_st_w = stem_w + 2.0 * clear
    cav_st_h = stem_h + clear
    cav_bd_w = rack_w + 2.0 * clear
    cav_bd_h = rack_h + clear + 0.5
    # open through +X (length + overhang) so rack can exit outer end
    cav_len = length + 4.0

    fl = Part.makeBox(cav_len, cav_fl_w, cav_fl_h)
    fl.translate(
        App.Vector(-2.0, (rack_w - cav_fl_w) / 2.0, -(stem_h + flange_h) - clear * 0.5)
    )
    st = Part.makeBox(cav_len, cav_st_w, cav_st_h)
    st.translate(
        App.Vector(-2.0, (rack_w - cav_st_w) / 2.0, -stem_h - clear * 0.5)
    )
    bd = Part.makeBox(cav_len, cav_bd_w, cav_bd_h)
    bd.translate(App.Vector(-2.0, -clear, -clear * 0.5))
    # Mesh window on +Y: open teeth side for pinion (full rail length)
    win = Part.makeBox(cav_len, tooth_h + wall + 4.0, rack_h + 2.0)
    win.translate(App.Vector(-2.0, rack_w - 1.0, -1.0))

    rail = body.cut(fl).cut(st).cut(bd).cut(win)
    return _keep_largest_solid(rail.removeSplitter())


def _padded_bb(shape: Part.Shape, pad: float = 1.5) -> Part.Shape:
    """Axis-aligned pad around shape BoundBox (clearance cutter)."""
    bb = shape.BoundBox
    b = Part.makeBox(
        bb.XLength + 2.0 * pad,
        bb.YLength + 2.0 * pad,
        bb.ZLength + 2.0 * pad,
    )
    b.translate(App.Vector(bb.XMin - pad, bb.YMin - pad, bb.ZMin - pad))
    return b


def _radial_stroke_clearance(
    shape: Part.Shape,
    ux: float,
    uy: float,
    stroke: float,
    pad: float = 1.5,
    steps: int = 8,
) -> Part.Shape:
    """Fuse padded copies along radial travel 0..stroke (guarantees free motion)."""
    fused = None
    for i in range(steps + 1):
        s = shape.copy()
        d = stroke * float(i) / float(steps)
        if d != 0.0:
            s.translate(App.Vector(ux * d, uy * d, 0.0))
        pad_s = _padded_bb(s, pad)
        fused = pad_s if fused is None else fused.fuse(pad_s)
    return fused.removeSplitter()


def _fuse_significant_solids(shape: Part.Shape, min_vol: float = 30.0) -> Part.Shape:
    """Keep all sizable solids after heavy clearance cuts (not only largest)."""
    solids = [s for s in shape.Solids if s.Volume >= min_vol]
    if not solids:
        return _keep_largest_solid(shape)
    out = solids[0]
    for s in solids[1:]:
        out = out.fuse(s)
    return out.removeSplitter()


def _make_drive_box(
    lx: float,
    ly: float,
    z0: float,
    z1: float,
    wall: float,
    bot_t: float,
    top_t: float,
    shaft_xy: tuple[float, float],
    shaft_d: float,
    motion_cuts: list[tuple[float, float, float, float, float, float]],
    ang: float,
    ox: float,
    oy: float,
) -> Part.Shape:
    """
    Enclosure around pinion. Local box -> rotate(ang) -> translate(ox,oy).
    Shaft holes on bottom + top. motion_cuts open rack/guard tunnels.
    """
    sx, sy = shaft_xy
    h = z1 - z0
    outer = Part.makeBox(lx, ly, h)
    outer.translate(App.Vector(-lx / 2.0, -ly / 2.0, z0))
    iw = lx - 2.0 * wall
    id_ = ly - 2.0 * wall
    ih = h - bot_t - top_t
    if iw > 2.0 and id_ > 2.0 and ih > 2.0:
        inner = Part.makeBox(iw, id_, ih)
        inner.translate(App.Vector(-iw / 2.0, -id_ / 2.0, z0 + bot_t))
        box = outer.cut(inner)
    else:
        box = outer
    br = shaft_d / 2.0 + 0.25
    bot_hole = Part.makeCylinder(br, bot_t + 2.0)
    bot_hole.translate(App.Vector(sx, sy, z0 - 1.0))
    top_hole = Part.makeCylinder(br, top_t + 2.0)
    top_hole.translate(App.Vector(sx, sy, z1 - top_t - 1.0))
    box = box.cut(bot_hole).cut(top_hole)
    for x0, y0, length, width, z_lo, z_hi in motion_cuts:
        zh = max(z_hi - z_lo, 1.0)
        cut = Part.makeBox(length, width, zh)
        cut.translate(App.Vector(x0, y0 - width / 2.0, z_lo))
        box = box.cut(cut)
    box.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), ang)
    box.translate(App.Vector(ox, oy, 0.0))
    return box


def make_lining_up_gap_parts(z_disc: float) -> list[tuple[str, Part.Shape, tuple]]:
    """
    Gap_Lining_Up: rack + pinion in enclosed drive box.

      Gap_Curve_Guard — curved Ø10cm barrier + socket for rack tongue
      Gap_Rack_Rail — fixed T-slot; open outer end -> rack removable
      Gap_Rack — T-foot bar in rail
      Gap_Drive_Box — shell; dual shaft holes; grooves for rack+guard travel
      Gap_Pinion + shaft + knob — vertical axis, dual-bearing

    Geometry mates Exit_Guide_Tray in world via FCStd Placements.
    """
    _pls, _vis, _parts, _names = load_state_from_fcstd(FCSTD)
    tray_pl = _pls.get("Exit_Guide_Tray")
    gap_pl = _pls.get("Gap_Lining_Up")
    tpx = float(tray_pl.Base.x) if tray_pl is not None else 0.0
    tpy = float(tray_pl.Base.y) if tray_pl is not None else 0.0
    gpx = float(gap_pl.Base.x) if gap_pl is not None else 0.0
    gpy = float(gap_pl.Base.y) if gap_pl is not None else 0.0
    acx = EXIT_TRAY_ARC_CX + tpx - gpx
    acy = EXIT_TRAY_ARC_CY + tpy - gpy

    ra = EXIT_TRAY_ARC_R
    tray_wt = EXIT_TRAY_WALL_T
    r_hug = ra + tray_wt
    curve_t = GAP_CURVE_T
    a0, a1 = GAP_CURVE_A0, GAP_CURVE_A1
    amid = 0.5 * (a0 + a1)
    rad = math.radians(amid)
    ux, uy = math.cos(rad), math.sin(rad)
    px_hat, py_hat = -uy, ux
    ang = math.degrees(math.atan2(uy, ux))

    z_wall = z_disc + DISC_T
    wh = EXIT_TRAY_WALL_H
    jaw_h = DISC_T + 2.0

    module = GAP_RACK_MODULE
    pitch = math.pi * module
    pinion_teeth = GAP_PINION_TEETH
    pd = module * float(pinion_teeth)
    tip_r = pd / 2.0 + module
    rack_n = max(8, int(math.ceil(GAP_CURVE_STROKE_MAX / pitch)) + 4)
    rack_w = 8.0
    rack_h = 8.0
    stem_w, stem_h = 4.0, 2.5
    flange_w, flange_h = 12.0, 2.0
    pinion_t = rack_h
    pinion_bore = 6.0
    tooth_h = 1.5 * module
    clear = GAP_RAIL_CLEAR
    wall = GAP_RAIL_WALL

    grey = (0.92, 0.92, 0.93)
    jaw_c = (0.85, 0.88, 0.9)
    slide_c = (0.95, 0.55, 0.15)
    gear_c = (0.55, 0.55, 0.58)
    rail_c = (0.75, 0.78, 0.82)
    knob_c = (0.05, 0.05, 0.05)

    # Curved barrier + open socket for removable rack tongue
    guard = _annular_sector(r_hug, r_hug + curve_t, a0, a1, z_wall, wh)
    guard.translate(App.Vector(acx, acy, 0.0))

    r_tip = r_hug + curve_t
    rack_z = z_wall + wh * 0.35
    rack, rack_len = _make_rack(
        module, rack_n, rack_w, rack_h, stem_w, stem_h, flange_w, flange_h
    )
    # place rack: local body Y [0,w] -> center on ray by -w/2
    def _place_on_ray(shape: Part.Shape, r0: float) -> Part.Shape:
        s = shape.copy()
        s.translate(App.Vector(0.0, -rack_w / 2.0, rack_z))
        s.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), ang)
        s.translate(App.Vector(acx + r0 * ux, acy + r0 * uy, 0.0))
        return s

    rack = _place_on_ray(rack, r_tip)

    # Guard socket: pocket open radially out + slightly up so tongue slides in/out
    sock_w = rack_w + 2.0 + 2.0 * clear
    sock_h = rack_h + 2.0 * clear
    sock_d = 6.0
    socket = Part.makeBox(sock_d + 2.0, sock_w + 4.0, sock_h + 3.0)
    socket.translate(App.Vector(0.0, -(sock_w + 4.0) / 2.0, rack_z - 1.5))
    socket.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), ang)
    socket.translate(App.Vector(acx + (r_tip - 1.0) * ux, acy + (r_tip - 1.0) * uy, 0.0))
    cav = Part.makeBox(sock_d + 4.0, sock_w, sock_h)
    cav.translate(App.Vector(-1.0, -sock_w / 2.0, rack_z))
    cav.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), ang)
    cav.translate(App.Vector(acx + (r_tip - 2.0) * ux, acy + (r_tip - 2.0) * uy, 0.0))
    socket = socket.cut(cav)
    guard = guard.fuse(socket)

    # Fixed T-rail: covers stroke + rack length; open at outer end
    rail_len = rack_len + GAP_CURVE_STROKE_MAX + 10.0
    rail = _make_rack_rail(
        rail_len,
        rack_w,
        rack_h,
        stem_w,
        stem_h,
        flange_w,
        flange_h,
        clear,
        wall,
        tooth_h,
    )
    rail = _place_on_ray(rail, r_tip - 2.0)

    # Pinion beside rack at mid-stroke
    r_mesh = r_tip + GAP_CURVE_STROKE_MAX * 0.5
    y_off = rack_w / 2.0 + tooth_h + tip_r - 0.4
    px = acx + r_mesh * ux + y_off * px_hat
    py = acy + r_mesh * uy + y_off * py_hat
    pinion_z = rack_z
    pinion = _involute_pinion(module, pinion_teeth, pinion_t, pinion_bore)
    pinion.translate(App.Vector(px, py, pinion_z))

    # Drive box sits mainly on pinion side; open toward rack/guard
    box_wall = 3.0
    box_bot_t = 4.0
    box_top_t = 4.0
    foot_h = stem_h + flange_h
    box_z0 = rack_z - foot_h - clear - box_bot_t
    box_z1 = pinion_z + pinion_t + 8.0 + box_top_t
    stroke = GAP_CURVE_STROKE_MAX
    # Shift box toward pinion (+perp) so guard arc does not sit inside walls
    local_cy = y_off * 0.15
    lx = 2.0 * tip_r + stroke + rack_len * 0.35 + 24.0
    ly = tip_r * 2.0 + y_off + 18.0
    box_ox = px + local_cy * px_hat
    box_oy = py + local_cy * py_hat
    shaft_local = (0.0, -local_cy)
    rack_local_y = -(y_off + local_cy)
    # Wide open bay on rack/guard side (−Y local) through full height
    rack_tun_w = ly  # open entire rack-facing half
    rack_tun_z0 = min(box_z0, z_wall) - 2.0
    rack_tun_z1 = max(box_z1, z_wall + wh) + 2.0
    open_bay = (
        -lx / 2.0 - 6.0,
        rack_local_y - ly * 0.25,
        lx + 12.0,
        ly * 0.85,
        rack_tun_z0,
        rack_tun_z1,
    )
    # Through tunnel for rack body + teeth + T-foot (full stroke + remove)
    rack_path_w = max(flange_w, rack_w) + tooth_h + 2.0 * wall + 8.0
    rack_path = (
        -lx / 2.0 - 6.0,
        rack_local_y + tooth_h * 0.4,
        lx + 12.0,
        rack_path_w,
        box_z0 - 2.0,
        rack_z + rack_h + 4.0,
    )
    drive_box = _make_drive_box(
        lx,
        ly,
        box_z0,
        box_z1,
        box_wall,
        box_bot_t,
        box_top_t,
        shaft_local,
        pinion_bore,
        [open_bay, rack_path],
        ang,
        box_ox,
        box_oy,
    )
    # Boolean: cut swept volumes of guard + rack over 0..20 mm (true free stroke)
    guard_clear = _radial_stroke_clearance(guard, ux, uy, stroke, pad=2.0, steps=10)
    rack_clear = _radial_stroke_clearance(
        rack, ux, uy, stroke + 8.0, pad=1.5, steps=10
    )
    drive_box = drive_box.cut(guard_clear).cut(rack_clear)
    drive_box = _fuse_significant_solids(drive_box.removeSplitter())

    # Shaft spans bottom bearing -> top bearing -> knob above lid
    shaft_z0 = box_z0 - 1.0
    shaft_z1 = box_z1 + 2.0
    shaft_h = shaft_z1 - shaft_z0
    pshaft = Part.makeCylinder(pinion_bore / 2.0 - 0.15, shaft_h)
    pshaft.translate(App.Vector(px, py, shaft_z0))
    kz = box_z1 + 1.0
    knob = Part.makeCylinder(KNOB_D / 2.0, KNOB_H)
    knob.translate(App.Vector(px, py, kz))
    for i in range(12):
        a = math.radians(i * 30)
        fx = px + (KNOB_D / 2.0 - 1.2) * math.cos(a)
        fy = py + (KNOB_D / 2.0 - 1.2) * math.sin(a)
        flute = Part.makeCylinder(2.0, KNOB_H + 1.0)
        flute.translate(App.Vector(fx, fy, kz - 0.5))
        knob = knob.cut(flute)

    _wall, bore_d, _side = _guide_dims()
    x_rim = -bore_d / 2.0
    fixed = Part.makeBox(JAW_T, JAW_LEN, jaw_h)
    fixed.translate(
        App.Vector(x_rim - 8.0, EXIT_Y - JAW_LEN / 2.0, z_disc)
    )

    print(
        "Gap_Lining_Up: drive box clearance-swept | rack free stroke %.0fmm | "
        "M%.1f ARC_C=(%.1f,%.1f)"
        % (GAP_CURVE_STROKE_MAX, module, acx, acy)
    )
    return [
        ("Gap_Drive_Box", drive_box, grey),
        ("Gap_Fixed_Jaw", _keep_largest_solid(fixed.removeSplitter()), jaw_c),
        (
            "Gap_Curve_Guard",
            _keep_largest_solid(guard.removeSplitter()),
            slide_c,
        ),
        ("Gap_Rack_Rail", rail, rail_c),
        ("Gap_Rack", rack, gear_c),
        ("Gap_Pinion", pinion, gear_c),
        ("Gap_Pinion_Shaft", pshaft.removeSplitter(), knob_c),
        ("Gap_Knob", _keep_largest_solid(knob.removeSplitter()), knob_c),
    ]


def make_lining_up_gap_mechanism(z_disc: float):
    """Back-compat: box, fixed, guard, rack, knob."""
    by_name = {n: sh for n, sh, _c in make_lining_up_gap_parts(z_disc)}
    return (
        by_name["Gap_Drive_Box"],
        by_name["Gap_Fixed_Jaw"],
        by_name["Gap_Curve_Guard"],
        by_name["Gap_Rack"],
        by_name["Gap_Knob"],
    )


def make_manual_gate_assembly(z_disc: float):
    """Back-compat wrapper -> lining-up gap mechanism parts."""
    mount, fixed, slide, screw, knob = make_lining_up_gap_mechanism(z_disc)
    body = mount.fuse(fixed)
    return body, knob, screw, slide


def _box_along_xy(
    x0: float,
    y0: float,
    ux: float,
    uy: float,
    length: float,
    width: float,
    height: float,
    z0: float,
) -> Part.Shape:
    """Axis-aligned box in local frame: +X=length along (ux,uy), +Y=width."""
    b = Part.makeBox(length, width, height)
    b.translate(App.Vector(0.0, -width / 2.0, z0))
    ang = math.degrees(math.atan2(uy, ux))
    b.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), ang)
    b.translate(App.Vector(x0, y0, 0.0))
    return b



def _tray_disc_center_local() -> tuple[float, float]:
    """Disc axis (world 0,0) expressed in Exit_Guide_Tray local coords."""
    _pls, _vis, _parts, _names = load_state_from_fcstd(FCSTD)
    tray_pl = _pls.get("Exit_Guide_Tray")
    tpx = float(tray_pl.Base.x) if tray_pl is not None else 0.0
    tpy = float(tray_pl.Base.y) if tray_pl is not None else 0.0
    return (-tpx, -tpy)


def _cut_disc_keepout(
    shape: Part.Shape,
    z0: float,
    h: float,
    disc_xy: tuple[float, float],
    r_clear: float,
) -> Part.Shape:
    """Remove tray material that sits on the disc (blocks recirculation)."""
    cx, cy = disc_xy
    cut = Part.makeCylinder(r_clear, h + 4.0)
    cut.translate(App.Vector(cx, cy, z0 - 2.0))
    try:
        out = shape.cut(cut)
    except Exception:
        return shape
    if not out.Solids:
        return shape
    return _keep_largest_solid(out.removeSplitter())


def make_exit_tray_floor_basic_parts(
    z_disc: float,
) -> list[tuple[str, Part.Shape, tuple]]:
    """
    Exit_Tray_Floor children — basic geometry only.
    Disc keep-out: no floor paving on the turntable (recirculation free).
    Move whole tray via Exit_Guide_Tray Placement (restored from FCStd).
    """
    z0 = z_disc + DISC_T
    ft = EXIT_TRAY_FLOOR_T
    wt = EXIT_TRAY_WALL_T
    ra = EXIT_TRAY_ARC_R
    ch = EXIT_TRAY_CH_W
    sl = EXIT_TRAY_STRAIGHT_LEN
    pad_x = EXIT_TRAY_FLOOR_SIDE_PAD
    front_clr = EXIT_TRAY_WALL_FRONT_CLEAR
    acx, acy = EXIT_TRAY_ARC_CX, EXIT_TRAY_ARC_CY
    clear_c = (0.55, 0.85, 0.95)
    disc_xy = _tray_disc_center_local()
    r_keep = DISC_D / 2.0 + EXIT_TRAY_DISC_CLEAR

    x_right = acx - ra
    y_arc_top = acy + ra
    y_join = acy
    y_floor_front = y_join - sl
    y_wall_front = y_floor_front + front_clr
    x_left = x_right - ch - wt
    x_right_wall = x_right - wt / 2.0
    x_ch0 = x_left + wt / 2.0
    x_ch1 = x_right_wall - wt / 2.0
    x0 = x_left - wt / 2.0 - pad_x
    x1 = x_right + wt + pad_x
    floor_w = x1 - x0

    def box_xy(x_lo, x_hi, y_lo, y_hi) -> Part.Shape:
        b = Part.makeBox(max(0.5, x_hi - x_lo), max(0.5, y_hi - y_lo), ft)
        b.translate(App.Vector(x_lo, y_lo, z0))
        return b

    rect_front = box_xy(x0, x1, y_floor_front - 2.0, y_wall_front)
    rect_left = box_xy(x0, x_ch0, y_wall_front, y_arc_top + 2.0)
    rect_right = box_xy(x_ch1, x1, y_wall_front, y_join + 2.0)

    sq = min(18.0, floor_w * 0.35, front_clr + 4.0)
    square = Part.makeBox(sq, sq, ft)
    square.translate(App.Vector(x0 + 1.0, y_floor_front - 1.0, z0))

    # Ring only on channel-outer side; then disc keep-out
    r_ch_out = ra + ch
    r_out = ra + ch + 2.0 * wt + pad_x
    ring = _annular_sector(
        r_ch_out, r_out, EXIT_TRAY_ARC_A0, EXIT_TRAY_ARC_A1, z0, ft
    )
    ring.translate(App.Vector(acx, acy, 0.0))

    parts_raw = [
        ("Exit_Tray_Floor_Rect_Front", rect_front, clear_c),
        ("Exit_Tray_Floor_Rect_Left", rect_left, clear_c),
        ("Exit_Tray_Floor_Rect_Right", rect_right, clear_c),
        ("Exit_Tray_Floor_Square", square, clear_c),
        ("Exit_Tray_Floor_Ring_Sector", ring, clear_c),
    ]
    # Drop Floor_Disc washer — it paved ARC_C on top of the turntable
    out = []
    for name, sh, col in parts_raw:
        cut = _cut_disc_keepout(sh, z0, ft + 2.0, disc_xy, r_keep)
        if cut is None or not getattr(cut, "Solids", None):
            continue
        if cut.Volume < 50.0:
            continue
        out.append((name, cut.removeSplitter(), col))

    print(
        "Exit_Tray_Floor: disc keep-out r=%.1f @ local=(%.1f,%.1f) | "
        "%d pieces | tray Placement movable"
        % (r_keep, disc_xy[0], disc_xy[1], len(out))
    )
    return out


def make_exit_guide_tray_parts(z_disc: float) -> list[tuple[str, Part.Shape, tuple]]:
    """
    Exit tray walls. Right arc shortened + disc keep-out so rim recirculation
    stays open. Left tip stops short of sealing against Curve_Guard
    (EXIT_TRAY_RECYC_GAP). Move tray: Transform Exit_Guide_Tray (Placement saved).
    """
    z0 = z_disc + DISC_T
    wh = EXIT_TRAY_WALL_H
    wt = EXIT_TRAY_WALL_T
    ra = EXIT_TRAY_ARC_R
    ch = EXIT_TRAY_CH_W
    sl = EXIT_TRAY_STRAIGHT_LEN
    front_clr = EXIT_TRAY_WALL_FRONT_CLEAR
    acx, acy = EXIT_TRAY_ARC_CX, EXIT_TRAY_ARC_CY
    clear_c = (0.55, 0.85, 0.95)
    disc_xy = _tray_disc_center_local()
    r_keep = DISC_D / 2.0 + EXIT_TRAY_DISC_CLEAR

    x_right = acx - ra
    y_arc_top = acy + ra
    y_join = acy
    y_floor_front = y_join - sl
    y_wall_front = y_floor_front + front_clr
    x_left = x_right - ch - wt
    x_right_wall = x_right - wt / 2.0
    x_left_inner = x_left + wt / 2.0

    # Tip meets max-open guard, then back off for recirculation gap
    r_touch = ra + wt + GAP_CURVE_T + GAP_CURVE_STROKE_MAX
    dx = x_left_inner - acx
    y_left_hi = y_arc_top
    if abs(dx) < r_touch - 1e-6:
        dy = math.sqrt(max(0.0, r_touch * r_touch - dx * dx))
        y_touch = acy + dy
        ang = math.degrees(math.atan2(y_touch - acy, dx))
        if ang < 0:
            ang += 360.0
        if GAP_CURVE_A0 - 5.0 <= ang <= GAP_CURVE_A1 + 5.0:
            y_left_hi = min(y_arc_top, y_touch) - EXIT_TRAY_RECYC_GAP
        print(
            "Exit_Tray_Wall_Left: tip y=%.1f (recyc gap %.0fmm vs guard touch)"
            % (y_left_hi, EXIT_TRAY_RECYC_GAP)
        )

    def wall_vert(xc: float, y0w: float, y1: float) -> Part.Shape:
        y_lo, y_hi = min(y0w, y1), max(y0w, y1)
        if y_hi - y_lo < 1.0:
            y_hi = y_lo + 1.0
        b = Part.makeBox(wt, y_hi - y_lo, wh)
        b.translate(App.Vector(xc - wt / 2.0, y_lo, z0))
        return b

    w_left = wall_vert(x_left, y_wall_front, y_left_hi)
    arc = _annular_sector(
        ra, ra + wt, EXIT_TRAY_ARC_A0, EXIT_TRAY_ARC_A1, z0, wh
    )
    arc.translate(App.Vector(acx, acy, 0.0))
    w_right_st = wall_vert(x_right_wall, y_wall_front, y_join + 0.5)

    # Walls: do NOT full disc-cut (arc/gap live near rim). Open recirculation via
    # shortened left tip + upstream arc start. Optional light trim of deep interior.
    r_inner = DISC_D / 2.0 - 18.0  # only clear deep interior, keep rim channel
    w_left = _cut_disc_keepout(w_left, z0, wh + 2.0, disc_xy, r_inner)
    arc = _cut_disc_keepout(arc, z0, wh + 2.0, disc_xy, r_inner)
    w_right_st = _cut_disc_keepout(w_right_st, z0, wh + 2.0, disc_xy, r_inner)

    print(
        "Exit_Guide_Tray walls: ARC %.0f-%.0f deg | left recyc gap %.0fmm | "
        "Placement movable (Transform Exit_Guide_Tray)"
        % (EXIT_TRAY_ARC_A0, EXIT_TRAY_ARC_A1, EXIT_TRAY_RECYC_GAP)
    )
    return [
        ("Exit_Tray_Wall_Left", w_left.removeSplitter(), clear_c),
        ("Exit_Tray_Wall_Right_Arc", arc.removeSplitter(), clear_c),
        (
            "Exit_Tray_Wall_Right_Straight",
            w_right_st.removeSplitter(),
            clear_c,
        ),
    ]


def make_exit_guide_tray(z_disc: float) -> Part.Shape:
    """Fused tray (compat). Prefer floor + wall parts + parent groups."""
    fused = None
    for _n, sh, _c in make_exit_tray_floor_basic_parts(z_disc):
        fused = sh if fused is None else fused.fuse(sh)
    for _n, sh, _c in make_exit_guide_tray_parts(z_disc):
        fused = sh if fused is None else fused.fuse(sh)
    return _keep_largest_solid(fused.removeSplitter())


def make_clear_exit_cover(z_disc: float) -> Part.Shape:
    """Clear acrylic cover over single-file exit path (Rx-4)."""
    z0 = z_disc + DISC_T + 1
    cover = Part.makeBox(70, GATE_GAP + 16, 2.5)
    cover.translate(App.Vector(-DISC_D / 2 - 25, -(GATE_GAP + 16) / 2, z0 + 18))
    # Side walls of clear funnel
    w1 = Part.makeBox(70, 2, 16)
    w1.translate(App.Vector(-DISC_D / 2 - 25, GATE_GAP / 2 + 4, z0 + 2))
    w2 = Part.makeBox(70, 2, 16)
    w2.translate(App.Vector(-DISC_D / 2 - 25, -GATE_GAP / 2 - 6, z0 + 2))
    return cover.fuse(w1).fuse(w2)


def make_separator_tab(z_disc: float) -> Part.Shape:
    """Height-adjustable separator over disc near gate (anti-stack)."""
    blade = Part.makeBox(35, 6, 8)
    blade.translate(App.Vector(-DISC_D / 2 + 25, -3, z_disc + DISC_T + 2))
    return blade


def make_outlet_chute(z_disc: float) -> Part.Shape:
    """Drop into front-left collection (Rx-4)."""
    z0 = z_disc + DISC_T
    chute = Part.makeBox(30, 28, 40)
    chute.translate(App.Vector(-DISC_D / 2 - 55, -14, z0 - 15))
    hollow = Part.makeBox(24, 22, 38)
    hollow.translate(App.Vector(-DISC_D / 2 - 52, -11, z0 - 14))
    return chute.cut(hollow)


def make_sensor_fork(z_disc: float) -> Part.Shape:
    z0 = z_disc + DISC_T + 3
    x0 = -DISC_D / 2 - 35
    left = Part.makeBox(8, 3, 20)
    left.translate(App.Vector(x0, GATE_GAP / 2 + 2, z0))
    right = Part.makeBox(8, 3, 20)
    right.translate(App.Vector(x0, -GATE_GAP / 2 - 5, z0))
    top = Part.makeBox(8, GATE_GAP + 10, 3)
    top.translate(App.Vector(x0, -GATE_GAP / 2 - 5, z0 + 17))
    return left.fuse(right).fuse(top)


def make_collection_drawer() -> Part.Shape:
    d = Part.makeBox(95, 65, 40)
    d.translate(App.Vector(-DISC_D / 2 - 40, BOX_D / 2 - 75, 28))
    inn = Part.makeBox(87, 55, 32)
    inn.translate(App.Vector(-DISC_D / 2 - 36, BOX_D / 2 - 68, 34))
    return d.cut(inn)


def make_control_panel() -> Part.Shape:
    """Front-right keypad + LED bezel (Rx-4)."""
    panel = Part.makeBox(95, 6, 70)
    panel.translate(App.Vector(15, -BOX_D / 2 - 2, BOX_H - 75))
    # Display window recess
    disp = Part.makeBox(40, 4, 18)
    disp.translate(App.Vector(25, -BOX_D / 2 - 1, BOX_H - 55))
    panel = panel.cut(disp)
    return panel


# ---- Split assemblies -> basic geometry children (box / cylinder / sector) ----

def make_motor_parts() -> list[tuple[str, Part.Shape, tuple]]:
    """JGB37 children as basic solids; same world pose as place_motor_vertical."""
    c = (0.75, 0.75, 0.78)
    gb = Part.makeCylinder(GB_D / 2, GB_L)
    gb.translate(App.Vector(0, 0, -GB_L))
    for i in range(6):
        a = math.radians(i * 60)
        x = (MOUNT_PCD / 2) * math.cos(a)
        y = (MOUNT_PCD / 2) * math.sin(a)
        d = 3.0 if (i % 2 == 0) else 4.0
        depth = 3.5 if (i % 2 == 0) else GB_L
        hole = Part.makeCylinder(d / 2, depth)
        hole.translate(App.Vector(x, y, -depth))
        gb = gb.cut(hole)

    boss = Part.makeCylinder(BOSS_D / 2, BOSS_H)
    boss.translate(App.Vector(0, SHAFT_OFFSET, 0))

    shaft = Part.makeCylinder(SHAFT_D / 2, SHAFT_L)
    shaft.translate(App.Vector(0, SHAFT_OFFSET, BOSS_H))
    flat = Part.makeBox(SHAFT_D + 2, 4.0, SHAFT_FLAT_L + 0.2)
    flat.translate(
        App.Vector(
            -SHAFT_D / 2 - 1,
            SHAFT_OFFSET + SHAFT_FLAT / 2,
            BOSS_H + SHAFT_L - SHAFT_FLAT_L,
        )
    )
    shaft = shaft.cut(flat)

    can = Part.makeCylinder(CAN_D / 2, CAN_L)
    can.translate(App.Vector(0, 0, -GB_L - CAN_L))
    rear = Part.makeCylinder(REAR_BOSS_D / 2, REAR_BOSS_H)
    rear.translate(App.Vector(0, 0, -GB_L - CAN_L - REAR_BOSS_H))

    terms = []
    for sx, tag in ((-1.0, "L"), (1.0, "R")):
        t = Part.makeBox(TERM_W, TERM_T, TERM_L)
        t.translate(
            App.Vector(
                sx * TERM_PITCH / 2 - TERM_W / 2,
                -TERM_T / 2,
                -GB_L - CAN_L - TERM_L,
            )
        )
        terms.append(("JGB37_Terminal_%s" % tag, place_motor_vertical(t), c))

    parts = [
        ("JGB37_Gearbox", place_motor_vertical(gb), c),
        ("JGB37_Boss", place_motor_vertical(boss), c),
        ("JGB37_Shaft", place_motor_vertical(shaft), c),
        ("JGB37_Can", place_motor_vertical(can), c),
        ("JGB37_Rear_Boss", place_motor_vertical(rear), c),
    ] + terms
    return [(n, _keep_largest_solid(s.removeSplitter()), col) for n, s, col in parts]


def make_hole_align_pin_parts(face_z: float) -> list[tuple[str, Part.Shape, tuple]]:
    c = (1.0, 0.15, 0.05)
    parts = []
    for i, (x, y, d) in enumerate(motor_face_holes_world()):
        pin = Part.makeCylinder(max(d / 2.0 - 0.35, 0.6), MOUNT_TOP_T + GB_L * 0.35)
        pin.translate(App.Vector(x, y, face_z - GB_L * 0.25))
        parts.append(("Hole_Align_Pin_%d" % i, pin.removeSplitter(), c))
    return parts


def make_housing_mount_parts(face_z: float) -> list[tuple[str, Part.Shape, tuple]]:
    """
    L_Bracket_Mount_Frame children: housing shell/lid/shelf + mount boxes.
    Pose / hole pattern unchanged (jgb37-mount-freeze).
    """
    hc = (0.85, 0.88, 0.86)
    ox = -BOX_W / 2.0
    oy = -BOX_D / 2.0
    outer = Part.makeBox(BOX_W, BOX_D, BOX_H)
    outer.translate(App.Vector(ox, oy, 0))
    inner = Part.makeBox(BOX_W - 2 * BOX_T, BOX_D - 2 * BOX_T, BOX_H - BOX_T + 1)
    inner.translate(App.Vector(ox + BOX_T, oy + BOX_T, BOX_T))
    shell = outer.cut(inner)
    drawer_cut = Part.makeBox(90, 22, 50)
    drawer_cut.translate(App.Vector(-45, oy + BOX_D - BOX_T - 4, 25))
    shell = shell.cut(drawer_cut)

    lid = Part.makeBox(BOX_W, BOX_D, BOX_T)
    lid.translate(App.Vector(ox, oy, TOP_Z))
    # Housing_Lid: full closed square — no disc hole / exit notch

    shelf = Part.makeBox(BOX_W - 2 * BOX_T - 4, BOX_D - 2 * BOX_T - 4, BOX_T)
    shelf.translate(App.Vector(ox + BOX_T + 2, oy + BOX_T + 2, SHELF_Z))
    shelf = shelf.cut(_cyl_z(BEARING_OD + 0.3, BOX_T + 1, SHELF_Z - 0.5))

    L = mount_layout(face_z)
    gx, gy = L["gx"], L["gy"]
    inner_m, wall = L["inner"], L["wall"]
    outer_w, outer_d = L["outer_w"], L["outer_d"]
    mox, moy = L["ox"], L["oy"]
    z_bot, z_lid = L["z_bot"], L["z_lid"]
    cav_h = face_z - z_bot
    half_w = BR_W / 2.0
    cy = half_w

    stem = Part.makeBox(outer_w, outer_d, z_lid - BOX_T)
    stem.translate(App.Vector(mox, moy, BOX_T))
    cavity = Part.makeBox(inner_m, inner_m, cav_h)
    cavity.translate(App.Vector(gx - inner_m / 2.0, gy - inner_m / 2.0, z_bot))
    stem = stem.cut(cavity)
    tunnel = Part.makeBox(inner_m + 1.0, outer_d + 50.0, cav_h)
    tunnel.translate(
        App.Vector(gx - (inner_m + 1.0) / 2.0, gy - inner_m / 2.0 - 50.0, z_bot)
    )
    stem = stem.cut(tunnel)
    if z_bot > BOX_T + 1.0:
        under = Part.makeBox(inner_m + 1.0, outer_d + 50.0, z_bot - BOX_T)
        under.translate(
            App.Vector(gx - (inner_m + 1.0) / 2.0, gy - inner_m / 2.0 - 50.0, BOX_T)
        )
        stem = stem.cut(under)
    vent_h = cav_h * 0.55
    vent_z0 = z_bot + (cav_h - vent_h) * 0.5
    vw, vd = 12.0, wall + 6.0
    for dx, dy, sx, sy in (
        (gx + inner_m / 2.0 - 1.0, gy - vw / 2.0, vd, vw),
        (gx - inner_m / 2.0 - vd + 1.0, gy - vw / 2.0, vd, vw),
        (gx - vw / 2.0, gy + inner_m / 2.0 - 1.0, vw, vd),
    ):
        v = Part.makeBox(sx, sy, vent_h)
        v.translate(App.Vector(dx, dy, vent_z0))
        stem = stem.cut(v)

    edges = [
        Part.LineSegment(App.Vector(-half_w, 0, 0), App.Vector(half_w, 0, 0)).toShape(),
        Part.LineSegment(
            App.Vector(half_w, 0, 0), App.Vector(half_w, BR_VERT_H - half_w, 0)
        ).toShape(),
        Part.Arc(
            App.Vector(half_w, BR_VERT_H - half_w, 0),
            App.Vector(0, BR_VERT_H, 0),
            App.Vector(-half_w, BR_VERT_H - half_w, 0),
        ).toShape(),
        Part.LineSegment(
            App.Vector(-half_w, BR_VERT_H - half_w, 0), App.Vector(-half_w, 0, 0)
        ).toShape(),
    ]
    mount_lid = Part.Face(Part.Wire(edges)).extrude(App.Vector(0, 0, MOUNT_TOP_T))
    mount_lid.translate(App.Vector(0, -SHAFT_OFFSET - cy, face_z))
    mount_lid = apply_motor_face_holes(mount_lid, face_z)

    braces = []
    for i, px in enumerate((mox - MOUNT_BRACE_W, mox + outer_w)):
        brace = Part.makeBox(MOUNT_BRACE_W, outer_d, SHELF_Z - BOX_T)
        brace.translate(App.Vector(px, moy, BOX_T))
        braces.append(("Mount_Brace_%d" % i, brace, hc))

    web = Part.makeBox(outer_w + 2.0 * MOUNT_BRACE_W, wall, SHELF_Z - BOX_T)
    web.translate(App.Vector(mox - MOUNT_BRACE_W, moy + outer_d - wall, BOX_T))

    pad_w = outer_w + 2.0 * MOUNT_BRACE_W + 20.0
    pad_d = outer_d + 12.0
    pad = Part.makeBox(pad_w, pad_d, 3.0)
    pad.translate(App.Vector(gx - pad_w / 2.0, moy - 2.0, BOX_T))

    parts = [
        ("Housing_Shell", _keep_largest_solid(shell.removeSplitter()), hc),
        ("Housing_Lid", _keep_largest_solid(lid.removeSplitter()), hc),
        ("Housing_Shelf", _keep_largest_solid(shelf.removeSplitter()), hc),
        ("Mount_Stem", _keep_largest_solid(stem.removeSplitter()), hc),
        ("Mount_Lid", _keep_largest_solid(mount_lid.removeSplitter()), hc),
        ("Mount_Web", web.removeSplitter(), hc),
        ("Mount_Floor_Pad", pad.removeSplitter(), hc),
    ] + [(n, s.removeSplitter(), col) for n, s, col in braces]
    return parts


def make_coupler_parts(z0: float) -> list[tuple[str, Part.Shape, tuple]]:
    c = (0.85, 0.55, 0.15)
    body = _cyl_z(COUPLER_OD, COUPLER_L, z0).cut(
        _cyl_z(DRIVE_SHAFT_D + 0.2, COUPLER_L + 1, z0 - 0.5)
    )
    return [("Coupler_Body", _keep_largest_solid(body.removeSplitter()), c)]


def make_drive_shaft_parts(z0: float, length: float) -> list[tuple[str, Part.Shape, tuple]]:
    return [("Shaft_Cylinder", _cyl_z(DRIVE_SHAFT_D, length, z0), (0.55, 0.55, 0.6))]


def make_bearing_parts(name_prefix: str, z0: float) -> list[tuple[str, Part.Shape, tuple]]:
    c = (0.15, 0.45, 0.85)
    race = _cyl_z(BEARING_OD, BEARING_H, z0).cut(
        _cyl_z(BEARING_ID + 0.05, BEARING_H + 0.2, z0 - 0.1)
    )
    return [("%s_Race" % name_prefix, _keep_largest_solid(race.removeSplitter()), c)]


def make_disc_parts(z0: float) -> list[tuple[str, Part.Shape, tuple]]:
    c = (0.95, 0.95, 0.95)
    disc = _cyl_z(DISC_D, DISC_T, z0).cut(
        _cyl_z(DRIVE_SHAFT_D + 0.1, DISC_T + 1, z0 - 0.5)
    )
    return [("Disc_Plate", _keep_largest_solid(disc.removeSplitter()), c)]


def make_center_hub_parts(z0: float) -> list[tuple[str, Part.Shape, tuple]]:
    c = (0.08, 0.08, 0.08)
    hub = _cyl_z(HUB_D, HUB_H, z0 + DISC_T)
    for i in range(12):
        a = math.radians(i * 30)
        hx = (HUB_D / 2 - 2) * math.cos(a)
        hy = (HUB_D / 2 - 2) * math.sin(a)
        hub = hub.cut(_cyl_z(4.0, HUB_H + 1, z0 + DISC_T - 0.5, hx, hy))
    hub = hub.cut(_cyl_z(DRIVE_SHAFT_D + 0.2, HUB_H + 1, z0 + DISC_T - 0.5))
    return [("Hub_Body", _keep_largest_solid(hub.removeSplitter()), c)]


def _fluted_knob(cx: float, cy: float, cz: float, d: float, h: float, n_flute: int = 10) -> Part.Shape:
    knob = Part.makeCylinder(d / 2.0, h)
    knob.translate(App.Vector(cx, cy, cz))
    fr = max(1.2, d * 0.06)
    for i in range(n_flute):
        a = math.radians(i * (360.0 / n_flute))
        fx = cx + (d / 2.0 - fr * 0.55) * math.cos(a)
        fy = cy + (d / 2.0 - fr * 0.55) * math.sin(a)
        flute = Part.makeCylinder(fr, h + 1.0)
        flute.translate(App.Vector(fx, fy, cz - 0.5))
        knob = knob.cut(flute)
    return _keep_largest_solid(knob.removeSplitter())


def _lid_plan_points() -> dict:
    """2D lid plan (XY) from box_settings — chute ends at disc far rim (−Y)."""
    return _lid_plan_full()


def _wall_along_poly(pts: list, thick: float, height: float, z0: float) -> Part.Shape | None:
    acc = None
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot(dx, dy)
        if length < 1e-4:
            continue
        ang = math.degrees(math.atan2(dy, dx))
        seg = Part.makeBox(length, thick, height)
        seg.translate(App.Vector(0.0, -thick / 2.0, z0))
        seg.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), ang)
        seg.translate(App.Vector(x0, y0, 0.0))
        acc = seg if acc is None else acc.fuse(seg)
    if acc is None:
        return None
    return _fuse_significant_solids(acc.removeSplitter(), min_vol=1.0)


def _prism_from_xy(pts: list, z0: float, height: float) -> Part.Shape:
    vecs = [App.Vector(p[0], p[1], 0.0) for p in pts]
    if vecs[0].distanceToPoint(vecs[-1]) > 1e-6:
        vecs.append(vecs[0])
    wire = Part.makePolygon(vecs)
    face = Part.Face(wire)
    solid = face.extrude(App.Vector(0, 0, height))
    solid.translate(App.Vector(0, 0, z0))
    return _keep_largest_solid(solid.removeSplitter())


def _lid_z_underside(z_disc: float) -> float:
    """Z of lid underside / disc-region wall bottoms = disc top + disc_clear."""
    return z_disc + DISC_T + LID_DISC_CLEAR


def _arc_out_pts_wide_tip(plan: dict) -> list:
    """
    Lid_Wall_Arc_Out path: keep arc_out pose; only extend wide-mouth tip +X
    toward the Ø20 cm rim (does not move w_out / recompute the arc).
    """
    pts = [tuple(p) for p in plan["arc_out"]]
    if not pts:
        return pts
    tip_inset = float(
        _LID_CFG["plan"]["funnel_walls"].get("arc_out_wide_tip_inset", 0.5)
    )
    tip_x = float(plan["r_disc"]) - tip_inset
    x0, y0 = float(pts[0][0]), float(pts[0][1])
    if tip_x > x0 + 1e-6:
        print(
            "Lid_Wall_Arc_Out: tip only %.1f -> %.1f (+X); arc body unchanged"
            % (x0, tip_x)
        )
        return [(tip_x, y0)] + pts
    return pts


def _lid_square_minus_disc(
    xl: float,
    xr: float,
    yb: float,
    yt: float,
    z0: float,
    thickness: float,
    hole_d: float,
) -> Part.Shape:
    """Closed square plate/prism with circular disc opening (no AABB gaps)."""
    body = Part.makeBox(xr - xl, yt - yb, thickness)
    body.translate(App.Vector(xl, yb, z0))
    body = body.cut(_cyl_z(hole_d, thickness + 4.0, z0 - 1.0))
    return _fuse_significant_solids(body.removeSplitter(), min_vol=10.0)


def make_lid_bottom_parts(z_disc: float) -> list[tuple[str, Part.Shape, tuple]]:
    """
    Lid_Bottom — underside at disc top + 0.5 mm; open over disc + chute,
    but sealed under Rim_Pocket and Deck_S_Rim (same XY as those top pieces).
    """
    from box_settings import lid_rim_pocket_xy

    if not LID_BOTTOM_EN:
        return []
    plan = _lid_plan_points()
    z0 = _lid_z_underside(z_disc)  # bottom face = disc top + clear
    bot_c = (0.55, 0.62, 0.70)
    rim_c = (0.72, 0.78, 0.55)
    deck_c = (0.62, 0.70, 0.78)
    xl, xr = float(plan["box_xl"]), float(plan["box_xr"])
    yb, yt = float(plan["box_yb"]), float(plan["box_yt"])
    hole_d = DISC_D + LID_BOTTOM_DISC_CLR
    r_disc = float(plan["r_disc"])
    y_mouth = float(plan["y_mouth"])
    x_in = float(plan["x_inner"])

    floor = _lid_square_minus_disc(xl, xr, yb, yt, z0, LID_BOTTOM_T, hole_d)
    chute_cut = False
    chute_xy = [plan["n_in"], plan["e_in"], plan["e_out"], plan["n_out"]]
    if LID_BOTTOM_OPEN_CHUTE and floor is not None and floor.Solids:
        try:
            chute_prism = _prism_from_xy(chute_xy, z0 - 1.0, LID_BOTTOM_T + 2.0)
            floor = floor.cut(chute_prism).removeSplitter()
            chute_cut = True
        except Exception:
            pass
    parts: list[tuple[str, Part.Shape, tuple]] = []
    if floor is not None and floor.Solids:
        parts.append(("Lid_Bottom_Floor", floor, bot_c))

    # Seal patches under Rim_Pocket / Deck_S_Rim (inside the disc opening)
    disc_mask = _cyl_z(DISC_D + 0.05, LID_BOTTOM_T + 4.0, z0 - 1.0)
    seal_names: list[str] = []

    def _keep_bot(shape: Part.Shape, min_vol: float = 2.0) -> Part.Shape | None:
        if shape is None or not shape.Solids:
            return None
        kept = _fuse_significant_solids(shape, min_vol=min_vol)
        if kept is None or not kept.Solids or kept.Volume < min_vol:
            return None
        return kept

    try:
        rim_prism = _prism_from_xy(
            lid_rim_pocket_xy(plan), z0, LID_BOTTOM_T
        )
        rim_seal = _keep_bot(rim_prism.common(disc_mask), min_vol=3.0)
        if rim_seal is not None:
            parts.append(("Lid_Bottom_Rim_Pocket", rim_seal, rim_c))
            seal_names.append("Rim_Pocket")
    except Exception as exc:
        print("Lid_Bottom_Rim_Pocket skipped:", exc)

    # Deck_S_Rim XY = over-disc remainder south of mouth, west of chute-in
    # (same split as Lid_Top_Deck_S_Rim): disc ∩ box − chute − rim
    try:
        dx = x_in - (-r_disc - 2.0)
        dy = y_mouth - (-r_disc - 2.0)
        if dx > 1e-3 and dy > 1e-3:
            box = Part.makeBox(dx, dy, LID_BOTTOM_T + 2.0)
            box.translate(App.Vector(-r_disc - 2.0, -r_disc - 2.0, z0 - 1.0))
            deck = box.common(disc_mask)
            try:
                deck = deck.cut(
                    _prism_from_xy(chute_xy, z0 - 1.0, LID_BOTTOM_T + 2.0)
                )
            except Exception:
                pass
            try:
                deck = deck.cut(
                    _prism_from_xy(
                        lid_rim_pocket_xy(plan), z0 - 1.0, LID_BOTTOM_T + 2.0
                    )
                )
            except Exception:
                pass
            # Clip height to bottom plate band
            band = Part.makeBox(xr - xl + 4.0, yt - yb + 4.0, LID_BOTTOM_T)
            band.translate(App.Vector(xl - 2.0, yb - 2.0, z0))
            deck_seal = _keep_bot(deck.common(band).removeSplitter(), min_vol=2.0)
            if deck_seal is not None:
                parts.append(("Lid_Bottom_Deck_S_Rim", deck_seal, deck_c))
                seal_names.append("Deck_S_Rim")
    except Exception as exc:
        print("Lid_Bottom_Deck_S_Rim skipped:", exc)

    print(
        "Lid_Bottom: underside z=disc+%.1f | T=%.0f | holeD=%.1f | chute_open=%s | seal=%s"
        % (
            LID_DISC_CLEAR,
            LID_BOTTOM_T,
            hole_d,
            chute_cut,
            ",".join(seal_names) if seal_names else "none",
        )
    )
    return parts


def make_lid_fill_parts(z_disc: float) -> list[tuple[str, Part.Shape, tuple]]:
    """
    Solid fill between disc rim and square — sits on bottom plate,
    up to underside of top plate.
    """
    if not LID_FILL_EN:
        return []
    plan = _lid_plan_points()
    z_under = _lid_z_underside(z_disc)
    z_fill0 = z_under + (LID_BOTTOM_T if LID_BOTTOM_EN else 0.0)
    h_fill = LID_WALL_H - (LID_BOTTOM_T if LID_BOTTOM_EN else 0.0)
    if h_fill < 1.0:
        h_fill = LID_WALL_H
        z_fill0 = z_under
    fill_c = (0.60, 0.66, 0.72)
    xl, xr = float(plan["box_xl"]), float(plan["box_xr"])
    yb, yt = float(plan["box_yb"]), float(plan["box_yt"])
    hole_d = DISC_D + LID_BOTTOM_DISC_CLR
    fill = _lid_square_minus_disc(xl, xr, yb, yt, z_fill0, h_fill, hole_d)
    parts: list[tuple[str, Part.Shape, tuple]] = []
    if fill is not None and fill.Solids:
        parts.append(("Lid_Fill_Outside", fill, fill_c))
    print(
        "Lid_Fill_Outside: on bottom | H=%.0f holeD=%.1f"
        % (h_fill, hole_d)
    )
    return parts


def make_lid_top_parts(z_disc: float) -> list[tuple[str, Part.Shape, tuple]]:
    """
    Lid_Top — continuous square top face, then split at wall lines.

    Build one sealed plate (hub / optional chute openings only), then carve into
    named children whose union == that plate (no gaps). Splits follow walls:
      square mid-axes, mouth, chute, funnel arcs, disc rim.
    """
    from box_settings import lid_rim_pocket_xy

    plan = _lid_plan_points()
    z_under = _lid_z_underside(z_disc)
    z_top0 = z_under + LID_WALL_H
    top_c = (0.75, 0.80, 0.88)
    out_c = (0.68, 0.74, 0.82)
    roof_c = (0.62, 0.72, 0.82)
    rim_c = (0.72, 0.78, 0.55)
    xl, xr = float(plan["box_xl"]), float(plan["box_xr"])
    yb, yt = float(plan["box_yb"]), float(plan["box_yt"])
    r_disc = float(plan["r_disc"])
    y_mouth = float(plan["y_mouth"])
    x_in = float(plan["x_inner"])
    x_out = float(plan["x_outer"])

    fc = _LID_CFG["plan"]["funnel_chamber"]
    roof_funnel = bool(fc.get("roofed_by_lid_top", True))
    roof_chute = bool(fc.get("roof_chute", False))
    cut_hub = bool(_LID_CFG["plan"]["top_plate"].get("cut_hub", True))

    funnel_xy = (
        [plan["w_in"]]
        + plan["arc_in"]
        + [plan["n_in"], plan["n_out"]]
        + list(reversed(plan["arc_out"]))
        + [plan["w_out"]]
    )
    chute_xy = [plan["n_in"], plan["e_in"], plan["e_out"], plan["n_out"]]

    parts: list[tuple[str, Part.Shape, tuple]] = []

    def _keep(shape: Part.Shape, min_vol: float = 2.0) -> Part.Shape | None:
        if shape is None or not shape.Solids:
            return None
        kept = _fuse_significant_solids(shape, min_vol=min_vol)
        if kept is None or not kept.Solids or kept.Volume < min_vol:
            return None
        return kept

    def _box_mask(x0: float, x1: float, y0: float, y1: float) -> Part.Shape:
        dx, dy = x1 - x0, y1 - y0
        if dx < 1e-6 or dy < 1e-6:
            return Part.Shape()
        b = Part.makeBox(dx, dy, LID_TOP_T + 4.0)
        b.translate(App.Vector(x0, y0, z_top0 - 1.0))
        return b

    def _add(name: str, shape: Part.Shape | None, color: tuple, min_vol: float = 2.0):
        kept = _keep(shape, min_vol=min_vol)
        if kept is not None:
            parts.append((name, kept, color))

    # --- 1) Continuous sealed square plate ---
    plate = Part.makeBox(xr - xl, yt - yb, LID_TOP_T)
    plate.translate(App.Vector(xl, yb, z_top0))
    if cut_hub:
        plate = plate.cut(_cyl_z(HUB_D + 4.0, LID_TOP_T + 4.0, z_top0 - 1.0))
    # Shaft clearance for Width_Adjust knob — only if vertical (legacy worm drive)
    drv = _LID_CFG.get("width_bar", {}).get("drive", {})
    if bool(drv.get("enabled", False)) and str(drv.get("mechanism", "")) == "worm_leadscrew":
        try:
            cx, cy = plan.get("width_bar_center", (0.0, 0.0))
            shaft_d = float(drv.get("shaft_od", 6.0)) + 0.6
            plate = plate.cut(
                _cyl_z(shaft_d, LID_TOP_T + 4.0, z_top0 - 1.0, float(cx), float(cy))
            )
        except Exception:
            pass
    # Height_Adjust shaft // Z (bearing block / journal through lid)
    hdrv = _LID_CFG.get("height_bar", {}).get("drive", {})
    if bool(hdrv.get("enabled", False)) and str(hdrv.get("mechanism", "")) in (
        "coaxial_leadscrew",
        "fixed_screw_traveling_nut",
        "face_cam_follower",
        # rack_pinion: shaft is horizontal (Y) — no vertical lid journal
    ):
        try:
            hx, hy = plan.get("height_drive_xy", plan.get("height_bar_center", (0.0, 0.0)))
            jod = float(hdrv.get("journal_od", hdrv.get("leadscrew_od", 8.0)))
            plate = plate.cut(
                _cyl_z(jod + 0.8, LID_TOP_T + 4.0, z_top0 - 1.0, float(hx), float(hy))
            )
        except Exception:
            pass
    if not roof_funnel:
        try:
            plate = plate.cut(_prism_from_xy(funnel_xy, z_top0 - 1.0, LID_TOP_T + 2.0))
        except Exception:
            pass
    if not roof_chute:
        try:
            plate = plate.cut(_prism_from_xy(chute_xy, z_top0 - 1.0, LID_TOP_T + 2.0))
        except Exception:
            pass
    plate = plate.removeSplitter()
    plate_vol = float(plate.Volume)

    disc_mask = _cyl_z(DISC_D + 0.05, LID_TOP_T + 4.0, z_top0 - 1.0)

    # --- 2) Outside disc — split at mid-axes + mouth + chute-out wall ---
    outside = plate.cut(disc_mask)
    # East of x=0 (wide-mouth axis)
    _add("Lid_Top_Out_NE", outside.common(_box_mask(0.0, xr, 0.0, yt)), out_c)
    _add("Lid_Top_Out_SE", outside.common(_box_mask(0.0, xr, yb, 0.0)), out_c)
    # West strip outside chute-out wall (square W ↔ chute) — covers ~9h pocket
    _add("Lid_Top_Out_W", outside.common(_box_mask(xl, x_out, yb, yt)), out_c, min_vol=3.0)
    # Between chute-out and center, split at mouth wall
    _add(
        "Lid_Top_Out_NW",
        outside.common(_box_mask(x_out, 0.0, y_mouth, yt)),
        out_c,
        min_vol=3.0,
    )
    _add(
        "Lid_Top_Out_NWm",
        outside.common(_box_mask(x_out, 0.0, 0.0, y_mouth)),
        out_c,
        min_vol=2.0,
    )
    # Out_SW -> chute X-band vs rest; chute split at Lid_Wall_Chute_End (y_exit)
    out_sw = outside.common(_box_mask(x_out, 0.0, yb, 0.0))
    y_end = float(plan["y_exit"])
    sw_chute = out_sw.common(_box_mask(x_out, x_in, yb, 0.0))
    _add(
        "Lid_Top_Out_SW_Chute_Above",
        sw_chute.common(_box_mask(x_out, x_in, y_end, 0.0)),
        out_c,
        min_vol=1.0,
    )
    _add(
        "Lid_Top_Out_SW_Chute_Below",
        sw_chute.common(_box_mask(x_out, x_in, yb, y_end)),
        out_c,
        min_vol=1.0,
    )
    _add(
        "Lid_Top_Out_SW_Rest",
        out_sw.common(_box_mask(x_in, 0.0, yb, 0.0)),
        out_c,
        min_vol=2.0,
    )

    # --- 3) Over disc: split at funnel / chute / mouth / rim walls ---
    over = plate.common(disc_mask)

    funnel_m = None
    chute_m = None
    rim_m = None
    try:
        funnel_m = _prism_from_xy(funnel_xy, z_top0 - 1.0, LID_TOP_T + 2.0)
    except Exception:
        pass
    try:
        chute_m = _prism_from_xy(chute_xy, z_top0 - 1.0, LID_TOP_T + 2.0)
    except Exception:
        pass
    try:
        rim_m = _prism_from_xy(lid_rim_pocket_xy(plan), z_top0 - 1.0, LID_TOP_T + 2.0)
    except Exception:
        pass

    if roof_funnel and funnel_m is not None:
        _add("Lid_Top_Funnel_Roof", over.common(funnel_m), roof_c, min_vol=5.0)
    if roof_chute and chute_m is not None:
        _add("Lid_Top_Chute_Roof", over.common(chute_m), roof_c, min_vol=3.0)
    if rim_m is not None:
        _add("Lid_Top_Rim_Pocket", over.common(rim_m), rim_c, min_vol=3.0)

    # Remainder over disc (not funnel / chute / rim) — split at mouth + chute-in
    rem = over
    for m in (funnel_m, chute_m, rim_m):
        if m is not None:
            try:
                rem = rem.cut(m)
            except Exception:
                pass
    rem = rem.removeSplitter()

    _add(
        "Lid_Top_Deck_N",
        rem.common(_box_mask(-r_disc - 2.0, r_disc + 2.0, y_mouth, r_disc + 2.0)),
        top_c,
    )
    south = rem.common(_box_mask(-r_disc - 2.0, r_disc + 2.0, -r_disc - 2.0, y_mouth))
    # Deck_S_Hub -> split trái (−X) / phải (+X) at mid-axis
    south_hub = south.common(_box_mask(x_in, r_disc + 2.0, -r_disc - 2.0, y_mouth))
    _add(
        "Lid_Top_Deck_S_Hub_L",
        south_hub.common(_box_mask(x_in, 0.0, -r_disc - 2.0, y_mouth)),
        top_c,
    )
    _add(
        "Lid_Top_Deck_S_Hub_R",
        south_hub.common(_box_mask(0.0, r_disc + 2.0, -r_disc - 2.0, y_mouth)),
        top_c,
    )
    _add(
        "Lid_Top_Deck_S_Rim",
        south.common(_box_mask(-r_disc - 2.0, x_in, -r_disc - 2.0, y_mouth)),
        top_c,
    )

    vol_sum = sum(sh.Volume for _, sh, _ in parts)
    print(
        "Lid_Top: sealed split-at-walls | plate=%.0f sum=%.0f (%.1f%%) | %s"
        % (
            plate_vol,
            vol_sum,
            100.0 * vol_sum / plate_vol if plate_vol > 1 else 0.0,
            ", ".join(n for n, _, _ in parts),
        )
    )
    return parts


def make_disc_access_lid_parts(z_disc: float) -> list[tuple[str, Part.Shape, tuple]]:
    """
    Disc_Access_Lid wall + adjuster children (Lid_Top is nested separately).

      Walls over disc start at disc top + disc_clear (0.5 mm).
      Lid_Wall_Sq_*     — closed square outer walls
      Lid_Wall_*        — funnel / chute / mouth / wide
      Lid_Wall_Chute_End — full-height barrier at chute south edge (blocks pills)
      Width_Adjust_Bar / Height_Adjust_Bar
    """
    plan = _lid_plan_points()
    z_wall0 = _lid_z_underside(z_disc)

    wall_c = (0.55, 0.60, 0.68)
    sq_c = (0.45, 0.50, 0.58)
    end_c = (0.75, 0.25, 0.25)  # red-ish — chute end barrier
    width_c = (0.55, 0.20, 0.65)
    height_c = (0.95, 0.55, 0.15)

    xl, xr = float(plan["box_xl"]), float(plan["box_xr"])
    yb, yt = float(plan["box_yb"]), float(plan["box_yt"])

    wall_specs = [
        ("Lid_Wall_Arc_In", plan["arc_in"]),
        ("Lid_Wall_Arc_Out", _arc_out_pts_wide_tip(plan)),
        ("Lid_Wall_Chute_In", [plan["n_in"], plan["e_in"]]),
        ("Lid_Wall_Chute_Out", [plan["n_out"], plan["e_out"]]),
        ("Lid_Wall_Wide", [plan["w_in"], plan["w_out"]]),
        ("Lid_Wall_Mouth", [plan["n_in"], plan["n_out"]]),
        # Closed square — fill missing edges
        ("Lid_Wall_Sq_E", [(xr, yb), (xr, yt)]),
        ("Lid_Wall_Sq_N", [(xr, yt), (xl, yt)]),
        ("Lid_Wall_Sq_W", [(xl, yt), (xl, yb)]),
        ("Lid_Wall_Sq_S", [(xl, yb), (xr, yb)]),
    ]
    # Expand chute slightly — punch circular arcs where they enter the straight channel
    chute_xy = [plan["n_in"], plan["e_in"], plan["e_out"], plan["n_out"]]
    pad = 0.5
    x_lo = min(p[0] for p in chute_xy) - pad
    x_hi = max(p[0] for p in chute_xy) + pad
    y_lo = min(p[1] for p in chute_xy) - pad
    y_hi = max(p[1] for p in chute_xy) + pad
    # Open south of mouth only (keep mouth wall); cut arcs that spill into chute
    y_mouth = float(plan["y_mouth"])
    chute_cut_xy = [
        (x_hi, y_mouth - 0.1),
        (x_hi, y_lo),
        (x_lo, y_lo),
        (x_lo, y_mouth - 0.1),
    ]
    chute_arc_cutter = None
    try:
        chute_arc_cutter = _prism_from_xy(
            chute_cut_xy, z_wall0 - 1.0, LID_WALL_H + 2.0
        )
    except Exception:
        pass

    wall_parts: list[tuple[str, Part.Shape, tuple]] = []
    for name, pts in wall_specs:
        col = sq_c if name.startswith("Lid_Wall_Sq_") else wall_c
        w = _wall_along_poly(pts, LID_WALL_T, LID_WALL_H, z_wall0)
        if w is None:
            continue
        if name in ("Lid_Wall_Arc_In", "Lid_Wall_Arc_Out") and chute_arc_cutter is not None:
            try:
                w = w.cut(chute_arc_cutter).removeSplitter()
                w = _fuse_significant_solids(w, min_vol=1.0)
            except Exception:
                pass
        if w is not None and w.Solids:
            wall_parts.append((name, w, col))

    # Sealed rim arc OUTSIDE Ø20 cm disc — SOUTHERN arc:
    # right chute edge ∩ rim (−Y) -> wide-mouth outer (+X)
    rim_cfg = _LID_CFG["plan"]["funnel_chamber"].get("rim_seal_wall", {})
    if bool(rim_cfg.get("enabled", True)):
        try:
            from box_settings import lid_rim_seal_angles

            deg0, deg1, r_in, r_out = lid_rim_seal_angles(plan)
            rim_seg = _annular_sector(r_in, r_out, deg0, deg1, z_wall0, LID_WALL_H)
            # Safety: carve any accidental intrusion into disc cylinder
            rim_seg = rim_seg.cut(_cyl_z(DISC_D, LID_WALL_H + 4.0, z_wall0 - 1.0))
            rim_kept = _fuse_significant_solids(rim_seg.removeSplitter(), min_vol=5.0)
            if rim_kept is not None and rim_kept.Solids:
                rim_name = str(rim_cfg.get("name", "Lid_Wall_Rim_Arc"))
                rim_c = (0.35, 0.55, 0.45)
                wall_parts.append((rim_name, rim_kept, rim_c))
                print(
                    "%s: south rim wall T=%.1f | r=[%.2f,%.2f] | ang=%.1f->%.1f° CCW | outside disc"
                    % (rim_name, r_out - r_in, r_in, r_out, deg0, deg1)
                )
        except Exception as exc:
            print("Lid_Wall_Rim_Arc skipped:", exc)

    # Chute south edge barrier: underside -> top face of lid (full stack)
    chute_cfg = _LID_CFG["plan"].get("chute", {})
    if bool(chute_cfg.get("end_barrier", True)):
        h_spec = chute_cfg.get("end_barrier_height", "stack_height")
        h_end = LID_STACK_H if h_spec == "stack_height" else float(h_spec)
        # Span full chute width + wall half on each side so no corner leak
        e_in = plan["e_in"]
        e_out = plan["e_out"]
        x0 = min(float(e_in[0]), float(e_out[0])) - LID_WALL_T / 2.0
        x1 = max(float(e_in[0]), float(e_out[0])) + LID_WALL_T / 2.0
        y_end = 0.5 * (float(e_in[1]) + float(e_out[1]))
        barrier = Part.makeBox(x1 - x0, LID_WALL_T, h_end)
        barrier.translate(App.Vector(x0, y_end - LID_WALL_T / 2.0, z_wall0))
        wall_parts.append(
            ("Lid_Wall_Chute_End", _keep_largest_solid(barrier.removeSplitter()), end_c)
        )
        print(
            "Lid_Wall_Chute_End: y=%.1f H=%.0f (underside->top) blocks chute exit"
            % (y_end, h_end)
        )

    width_bar = _prism_from_xy(plan["width_bar"], z_wall0, LID_WIDTH_BAR_H)
    height_bar = _prism_from_xy(plan["height_bar"], z_wall0, LID_HEIGHT_BAR_H)

    # Clip Z to lid stack (XY already clipped in lid_plan_xy when clip_to_lid_box)
    wb_cfg = _LID_CFG.get("width_bar", {})
    if bool(wb_cfg.get("clip_to_lid_box", True)) and width_bar is not None:
        try:
            lid_clip = Part.makeBox(xr - xl, yt - yb, LID_STACK_H)
            lid_clip.translate(App.Vector(xl, yb, z_wall0))
            before = float(width_bar.Volume)
            width_bar = width_bar.common(lid_clip).removeSplitter()
            width_bar = _keep_largest_solid(width_bar)
            after = float(width_bar.Volume) if width_bar is not None else 0.0
            print(
                "Width_Adjust_Bar: pose offset=(%.1f,%.1f) | clipped to lid | vol %.0f->%.0f"
                % (
                    float(wb_cfg.get("offset_x", 0.0)),
                    float(wb_cfg.get("offset_y", 0.0)),
                    before,
                    after,
                )
            )
        except Exception as exc:
            print("Width_Adjust_Bar clip skipped:", exc)

    # Coaxial leadscrew bore through bar (// Y) so nut can ride the screw
    drv = wb_cfg.get("drive", {})
    if (
        width_bar is not None
        and bool(drv.get("enabled", False))
        and str(drv.get("mechanism", "")) == "coaxial_leadscrew"
    ):
        try:
            cx, cy = plan.get("width_bar_center", (0.0, 0.0))
            xs = [p[0] for p in plan["width_bar"]]
            ys = [p[1] for p in plan["width_bar"]]
            y_lo, y_hi = min(ys), max(ys)
            screw_od = float(drv.get("leadscrew_od", 8.0))
            clear_r = float(drv.get("thread_clear_r", 0.40))
            z_sc = z_wall0 + 0.5 * LID_WIDTH_BAR_H
            bore = _cyl_along_xy(
                float(cx),
                y_lo - 2.0,
                z_sc,
                0.0,
                1.0,
                (y_hi - y_lo) + 4.0,
                screw_od / 2.0 + clear_r + 0.3,
            )
            width_bar = _keep_largest_solid(width_bar.cut(bore).removeSplitter())
        except Exception as exc:
            print("Width_Adjust_Bar screw bore skipped:", exc)

    # Cam/follower drive owns Height_Adjust_Bar — skip prism duplicate
    hdrv = _LID_CFG.get("height_bar", {}).get("drive", {})
    height_from_drive = bool(hdrv.get("enabled", False)) and str(
        hdrv.get("mechanism", "")
    ) in (
        "face_cam_follower",
        "fixed_screw_traveling_nut",
        "coaxial_leadscrew",
        "rack_pinion",
    )

    print(
        "Disc_Access_Lid: walls from disc+%.1fmm | square %.0fmm | H=%.0f"
        % (LID_DISC_CLEAR, float(plan["square_side"]), LID_WALL_H)
    )

    out: list[tuple[str, Part.Shape, tuple]] = []
    out.extend(wall_parts)
    if width_bar is not None and width_bar.Solids:
        out.append(("Width_Adjust_Bar", width_bar, width_c))
    if height_bar is not None and height_bar.Solids and not height_from_drive:
        out.append(("Height_Adjust_Bar", height_bar, height_c))
    return out


def _helical_thread_solid_z(
    major_r: float,
    minor_r: float,
    pitch: float,
    length: float,
    segs_per_turn: int = 20,
) -> Part.Shape:
    """
    External thread along +Z: core (minor_r) + helical trapezoid tooth to major_r.
    Helix + makePipe (+ makeSolid); segment fallback if needed.
    """
    if length < pitch * 0.5 or major_r <= minor_r + 0.05:
        return Part.makeCylinder(max(minor_r, 0.5), max(length, 0.5))
    core = Part.makeCylinder(minor_r, length)
    tip_hw = 0.12 * pitch
    root_hw = 0.32 * pitch
    hr = 0.5 * (major_r + minor_r)
    try:
        helix = Part.makeHelix(pitch, max(pitch * 0.5, length - 0.05), hr, 0.0, False)
        # Profile in plane ⊥ helix tangent at start (~⊥Y): trapezoid in XZ
        pts = [
            App.Vector(minor_r, 0.0, -root_hw),
            App.Vector(major_r, 0.0, -tip_hw),
            App.Vector(major_r, 0.0, tip_hw),
            App.Vector(minor_r, 0.0, root_hw),
            App.Vector(minor_r, 0.0, -root_hw),
        ]
        profile = Part.makePolygon(pts)
        pipe = Part.Wire([helix]).makePipe(profile)
        if pipe is None or pipe.isNull():
            raise RuntimeError("null pipe")
        if not pipe.Solids:
            pipe = Part.makeSolid(pipe)
        if float(pipe.Volume) < 0.0:
            pipe = pipe.reversed()
        return _keep_largest_solid(_safe_refine(core.fuse(pipe)))
    except Exception as exc:
        print("helix makePipe fallback (%s)" % exc)
    segs = max(8, min(int(segs_per_turn), 12))
    seg_h = pitch / float(segs)
    n = max(1, int(math.ceil(length / seg_h)))
    dr = major_r - minor_r
    tooth = None
    step = max(1, n // 120)
    for i in range(0, n, step):
        z = i * seg_h
        if z >= length - 0.02:
            break
        ang = (i * 360.0) / float(segs)
        h_use = min(seg_h * step * 1.15, length - z)
        w = root_hw * 2.0
        box = Part.makeBox(dr + 0.05, w, h_use)
        box.translate(App.Vector(minor_r - 0.02, -w / 2.0, z))
        box.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), ang)
        tooth = box if tooth is None else tooth.fuse(box)
    if tooth is None:
        return _keep_largest_solid(core)
    return _keep_largest_solid(_safe_refine(core.fuse(tooth)))


def _thread_solid_along_y(
    x: float,
    y0: float,
    z: float,
    length: float,
    major_d: float,
    pitch: float,
    depth: float,
    segs_per_turn: int = 20,
    radial_extra: float = 0.0,
) -> Part.Shape:
    """Leadscrew (or oversized nut cutter) along +Y at (x, z)."""
    major_r = major_d / 2.0 + radial_extra
    minor_r = max(0.6, major_r - depth)
    local = _helical_thread_solid_z(major_r, minor_r, pitch, length, segs_per_turn)
    # +Z -> +Y
    local.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), -90.0)
    local.translate(App.Vector(x, y0, z))
    return _keep_largest_solid(local)


def make_width_adjust_drive_parts(z_disc: float) -> list[tuple[str, Part.Shape, tuple]]:
    """
    Printable coaxial width drive:

      Width_Lead_Screw  — FDM helix male thread + smooth journals + collar flange
      Width_Knob        — fused to north journal (turn by hand)
      Width_Nut         — matching female helix (clearance for FDM)
      Width_Rail        — anti-rotate U-channel + end bushings
      Width_Retainer_Base / _Cap — clamp collar to Lid_Top underside (axial lock)

    Turning the knob rotates the screw; nut+bar translate ±Y. Axial force on the
    screw is taken by the collar trapped in the retainer, so the knob stays on the lid.
    """
    drv = _LID_CFG.get("width_bar", {}).get("drive", {})
    if not bool(drv.get("enabled", False)):
        return []
    mech = str(drv.get("mechanism", "coaxial_leadscrew"))
    if mech != "coaxial_leadscrew":
        print("Width_Adjust_Drive: skip unsupported mechanism=%s" % mech)
        return []

    plan = _lid_plan_points()
    z_wall0 = _lid_z_underside(z_disc)
    z_top0 = z_wall0 + LID_WALL_H  # Lid_Top underside
    xs = [p[0] for p in plan["width_bar"]]
    ys = [p[1] for p in plan["width_bar"]]
    x_a, x_b = min(xs), max(xs)
    y_lo, y_hi = min(ys), max(ys)
    cx = 0.5 * (x_a + x_b) + float(drv.get("offset_x", 0.0))
    cy = 0.5 * (y_lo + y_hi) + float(drv.get("offset_y", 0.0))
    bar_w = x_b - x_a
    bar_h = LID_WIDTH_BAR_H
    z_sc = z_wall0 + 0.5 * bar_h

    knob_od = float(drv.get("knob_od", 28.0))
    knob_h = float(drv.get("knob_h", 14.0))
    grip_od = float(drv.get("knob_grip_od", 22.0))
    screw_od = float(drv.get("leadscrew_od", 8.0))
    pitch = float(drv.get("leadscrew_pitch", 3.0))
    depth = float(drv.get("thread_depth", 1.1))
    clear_r = float(drv.get("thread_clear_r", 0.40))
    segs = int(drv.get("segs_per_turn", 20))
    nut_l = float(drv.get("nut_l", 18.0))
    nut_w = float(drv.get("nut_w", 14.0))
    nut_h = float(drv.get("nut_h", 12.0))
    wall = float(drv.get("rail_wall", 2.0))
    clear = float(drv.get("rail_clear", 0.4))
    overhang = float(drv.get("rail_overhang", 3.0))
    collar_od = float(drv.get("collar_od", 16.0))
    collar_t = float(drv.get("collar_t", 2.8))
    journal_od = float(drv.get("journal_od", screw_od))
    ret_wall = float(drv.get("retainer_wall", 3.0))
    pad_t = float(drv.get("retainer_pad_t", 4.0))
    m3_d = float(drv.get("retainer_screw_d", 3.2))
    m3_span = float(drv.get("retainer_screw_span", 22.0))

    knob_c = (0.45, 0.25, 0.55)
    screw_c = (0.55, 0.58, 0.62)
    nut_c = (0.70, 0.45, 0.20)
    rail_c = (0.35, 0.55, 0.50)
    ret_c = (0.25, 0.45, 0.70)

    parts: list[tuple[str, Part.Shape, tuple]] = []

    # --- Axial layout along +Y ---
    # south journal | threaded | north journal in rail bushing | collar | hub | knob
    y_south_j0 = y_lo - 10.0
    south_j_len = 6.0
    y_th0 = y_south_j0 + south_j_len
    th_len = max(float(drv.get("leadscrew_len", 90.0)), (y_hi - y_lo) + 8.0)
    y_th1 = y_th0 + th_len
    north_j_len = 5.0
    y_nj0 = y_th1
    y_collar0 = y_nj0 + north_j_len
    y_hub0 = y_collar0 + collar_t
    hub_len = 4.0
    y_knob0 = y_hub0 + hub_len
    # smooth journal under knob face bearing against retainer

    # Lead screw: journals + helical male thread + collar
    south_j = _cyl_along_xy(
        cx, y_south_j0, z_sc, 0.0, 1.0, south_j_len + 0.5, journal_od / 2.0
    )
    threaded = _thread_solid_along_y(
        cx, y_th0, z_sc, th_len, screw_od, pitch, depth, segs, radial_extra=0.0
    )
    north_j = _cyl_along_xy(
        cx, y_nj0 - 0.3, z_sc, 0.0, 1.0, north_j_len + collar_t + hub_len + 1.0,
        journal_od / 2.0,
    )
    collar = _cyl_along_xy(cx, y_collar0, z_sc, 0.0, 1.0, collar_t, collar_od / 2.0)
    screw = south_j.fuse(threaded).fuse(north_j).fuse(collar)
    parts.append(("Width_Lead_Screw", _keep_largest_solid(_safe_refine(screw)), screw_c))

    # Knob fused to north end (print as one with screw, or glue on D-flat later)
    knob = _cyl_along_xy(cx, y_knob0, z_sc, 0.0, 1.0, knob_h * 0.35, knob_od / 2.0)
    grip = _cyl_along_xy(cx, y_knob0, z_sc, 0.0, 1.0, knob_h, grip_od / 2.0)
    knob = knob.fuse(grip)
    for i in range(8):
        a = math.radians(i * 45.0)
        fx = cx + (grip_od / 2.0 - 0.4) * math.cos(a)
        fz = z_sc + (grip_od / 2.0 - 0.4) * math.sin(a)
        flute = _cyl_along_xy(fx, y_knob0 - 0.5, fz, 0.0, 1.0, knob_h + 1.0, 2.2)
        knob = knob.cut(flute)
    hub = _cyl_along_xy(cx, y_hub0, z_sc, 0.0, 1.0, hub_len + 0.5, journal_od / 2.0 + 0.6)
    knob = knob.fuse(hub)
    parts.append(("Width_Knob", _keep_largest_solid(_safe_refine(knob)), knob_c))

    # Nut with matching female thread (cut oversized male solid from blank)
    nut = Part.makeBox(nut_w, nut_l, nut_h)
    nut.translate(App.Vector(cx - nut_w / 2.0, cy - nut_l / 2.0, z_sc - nut_h / 2.0))
    cutter = _thread_solid_along_y(
        cx,
        cy - nut_l / 2.0 - 1.0,
        z_sc,
        nut_l + 2.0,
        screw_od,
        pitch,
        depth,
        segs,
        radial_extra=clear_r,
    )
    nut = nut.cut(cutter)
    flange = Part.makeBox(max(nut_w, bar_w + 2.0), nut_l * 0.55, 2.0)
    flange.translate(
        App.Vector(
            cx - max(nut_w, bar_w + 2.0) / 2.0,
            cy - nut_l * 0.275,
            z_wall0 + bar_h,
        )
    )
    nut = nut.fuse(flange)
    parts.append(("Width_Nut", _keep_largest_solid(_safe_refine(nut)), nut_c))

    # Anti-rotate rail + end bushings (smooth journal clearance)
    inner_w = bar_w + 2.0 * clear
    outer_w = inner_w + 2.0 * wall
    rail_len = (y_hi - y_lo) + 8.0
    y_rail0 = y_lo - 4.0
    z_floor0 = z_wall0 - wall
    outer = Part.makeBox(outer_w, rail_len, bar_h + wall + 1.0)
    outer.translate(App.Vector(cx - outer_w / 2.0, y_rail0, z_floor0))
    cavity = Part.makeBox(inner_w, rail_len + 2.0, bar_h + clear + 2.0)
    cavity.translate(App.Vector(cx - inner_w / 2.0, y_rail0 - 1.0, z_wall0))
    rail = outer.cut(cavity)
    lip_gap = max(2.0, screw_od + 1.5)
    lip_w = max(0.8, (inner_w - lip_gap) / 2.0)
    for sign in (-1.0, 1.0):
        lip = Part.makeBox(lip_w, rail_len, overhang)
        if sign < 0:
            lx = cx - inner_w / 2.0
        else:
            lx = cx + inner_w / 2.0 - lip_w
        lip.translate(App.Vector(lx, y_rail0, z_wall0 + bar_h + clear - 0.2))
        rail = rail.fuse(lip)
    j_clear = journal_od / 2.0 + 0.35
    for yb, jy0 in (
        (y_rail0 - 4.0, y_south_j0 - 0.5),
        (y_rail0 + rail_len, y_nj0 - 0.5),
    ):
        boss = Part.makeBox(outer_w, 5.0, bar_h + wall)
        boss.translate(App.Vector(cx - outer_w / 2.0, yb, z_floor0))
        journal = _cyl_along_xy(cx, jy0, z_sc, 0.0, 1.0, 8.0, j_clear)
        boss = boss.cut(journal)
        rail = rail.fuse(boss)
    parts.append(("Width_Rail", _keep_largest_solid(_safe_refine(rail)), rail_c))

    # --- Retainer clamp on Lid_Top underside: traps collar -> knob cannot pull out ---
    # Pocket: journal bore + collar groove. Cap screws on with 2× M3.
    ret_w = max(collar_od + 2.0 * ret_wall, m3_span + 10.0)
    ret_h = max(collar_od + 2.0 * ret_wall, bar_h + 6.0)
    groove_clear = 0.35
    # Base sits under lid, open toward −Z so screw drops in from below, then cap closes
    y_ret0 = y_collar0 - ret_wall
    ret_len = collar_t + 2.0 * ret_wall + hub_len * 0.5
    z_ret0 = z_sc - ret_h / 2.0
    base = Part.makeBox(ret_w, ret_len, ret_h * 0.55)
    base.translate(App.Vector(cx - ret_w / 2.0, y_ret0, z_ret0))
    # Collar groove + journal slot (open bottom)
    groove = _cyl_along_xy(
        cx,
        y_collar0 - groove_clear,
        z_sc,
        0.0,
        1.0,
        collar_t + 2.0 * groove_clear,
        collar_od / 2.0 + groove_clear,
    )
    jslot = _cyl_along_xy(
        cx, y_ret0 - 1.0, z_sc, 0.0, 1.0, ret_len + 2.0, journal_od / 2.0 + 0.4
    )
    # Bottom access opening so one-piece screw+collar can drop in before capping
    access = Part.makeBox(ret_w + 2.0, ret_len + 2.0, ret_h * 0.35)
    access.translate(App.Vector(cx - ret_w / 2.0 - 1.0, y_ret0 - 1.0, z_ret0 - 0.5))
    base = base.cut(groove).cut(jslot).cut(access)
    # Pad up to lid underside (glue / M3 into Lid_Top)
    pad_z1 = z_top0
    pad_z0 = pad_z1 - pad_t
    pad = Part.makeBox(ret_w, ret_len, pad_t)
    pad.translate(App.Vector(cx - ret_w / 2.0, y_ret0, pad_z0))
    # Stem connecting base to pad
    stem = Part.makeBox(ret_w * 0.45, ret_len, max(1.0, pad_z0 - (z_ret0 + ret_h * 0.55)))
    stem.translate(
        App.Vector(cx - ret_w * 0.225, y_ret0, z_ret0 + ret_h * 0.55 - 0.1)
    )
    base = base.fuse(pad).fuse(stem)
    for sx in (-0.5 * m3_span, 0.5 * m3_span):
        hole = _cyl_z(m3_d, pad_t + ret_h + 8.0, z_ret0 - 2.0, cx + sx, y_ret0 + ret_len * 0.5)
        base = base.cut(hole)
    parts.append(
        ("Width_Retainer_Base", _keep_largest_solid(_safe_refine(base)), ret_c)
    )

    # Cap: mirrors lower half, traps collar; two M3 through
    cap = Part.makeBox(ret_w, ret_len, ret_h * 0.5)
    cap.translate(App.Vector(cx - ret_w / 2.0, y_ret0, z_sc - ret_h * 0.05))
    cap = cap.cut(groove).cut(jslot)
    for sx in (-0.5 * m3_span, 0.5 * m3_span):
        hole = _cyl_z(m3_d, ret_h + 4.0, z_sc - ret_h * 0.2, cx + sx, y_ret0 + ret_len * 0.5)
        cap = cap.cut(hole)
    # Countersink cue on outer face
    for sx in (-0.5 * m3_span, 0.5 * m3_span):
        cs = _cyl_z(6.0, 1.8, z_sc + ret_h * 0.35 - 1.8, cx + sx, y_ret0 + ret_len * 0.5)
        cap = cap.cut(cs)
    parts.append(
        ("Width_Retainer_Cap", _keep_largest_solid(_safe_refine(cap)), ret_c)
    )

    print(
        "Width_Adjust_Drive: FDM helix D%.0fx%.0f clear=%.2f | "
        "collar D%.0f captive in lid retainer | knob // Y"
        % (screw_od, pitch, clear_r, collar_od)
    )
    return parts


def _thread_solid_along_z(
    x: float,
    y: float,
    z0: float,
    length: float,
    major_d: float,
    pitch: float,
    depth: float,
    segs_per_turn: int = 20,
    radial_extra: float = 0.0,
) -> Part.Shape:
    """Leadscrew (or oversized nut cutter) along +Z at (x, y)."""
    major_r = major_d / 2.0 + radial_extra
    minor_r = max(0.6, major_r - depth)
    local = _helical_thread_solid_z(major_r, minor_r, pitch, length, segs_per_turn)
    local.translate(App.Vector(x, y, z0))
    return _keep_largest_solid(local)


def make_height_adjust_drive_parts(z_disc: float) -> list[tuple[str, Part.Shape, tuple]]:
    """
    Height_Adjust — Spur rack & pinion (see height_adjust_z.py).

      Height_Knob + Height_Pinion + Height_Shaft — rotate about Y (⊥ Z travel)
      Height_Friction_Washer — friction hold
      Height_Bearing_L/R — shaft supports
      Height_Adjust_Bar (follower + rack) — +/-Z; ~π·m·z mm/turn
      Height_Guide_Rail_* — anti-rotate
      Height_Bottom_Stop, Height_Scale_*
    """
    from height_adjust_z import build_height_adjust_z_parts

    drv = _LID_CFG.get("height_bar", {}).get("drive", {})
    if not bool(drv.get("enabled", False)):
        return []
    mech = str(drv.get("mechanism", "rack_pinion"))
    if mech not in (
        "rack_pinion",
        "face_cam_follower",
        "fixed_screw_traveling_nut",
        "coaxial_leadscrew",
    ):
        print("Height_Adjust_Drive: skip unsupported mechanism=%s" % mech)
        return []

    plan = _lid_plan_points()
    z_wall0 = _lid_z_underside(z_disc)
    xs = [p[0] for p in plan["height_bar"]]
    ys = [p[1] for p in plan["height_bar"]]
    x_a, x_b = min(xs), max(xs)
    y_a, y_b = min(ys), max(ys)
    cx, cy = plan.get("height_drive_xy", (0.5 * (x_a + x_b), 0.5 * (y_a + y_b)))
    cx, cy = float(cx), float(cy)

    cfg = dict(drv)
    cfg["bar_thickness"] = max(8.0, x_b - x_a)
    cfg["bar_length_y"] = max(20.0, y_b - y_a)
    cfg["bar_height"] = float(_LID_CFG.get("height_bar", {}).get("height", 12.0))

    raw = build_height_adjust_z_parts(
        cx=cx,
        cy=cy,
        z_zero=z_wall0,
        cfg=cfg,
        include_demo_wall=False,
    )
    rename = {
        "HA_Pinion_Shaft": "Height_Pinion_Shaft",
        "HA_Bearing_Rail_S": "Height_Bearing_Rail_S",
        "HA_Bearing_Cap_S": "Height_Bearing_Cap_S",
        "HA_Bearing_Rail_N": "Height_Bearing_Rail_N",
        "HA_Bearing_Cap_N": "Height_Bearing_Cap_N",
        "HA_Knob": "Height_Knob",
        "HA_Friction_Washer": "Height_Friction_Washer",
        "HA_Follower": "Height_Adjust_Bar",
        "HA_Bottom_Stop": "Height_Bottom_Stop",
    }
    out: list[tuple[str, Part.Shape, tuple]] = []
    for n, sh, col in raw:
        if n.startswith("HA_Scale_"):
            out.append((n.replace("HA_Scale_", "Height_Scale_"), sh, col))
        else:
            out.append((rename.get(n, n), sh, col))
    return out


def make_exit_press_guide_parts(z_disc: float) -> list[tuple[str, Part.Shape, tuple]]:
    """
    Exit_Press_Guide — ép viên vào khe thoát hoặc cho trượt vòng tiếp.

      Press_Mount       — giá cố định sát thành ngoài, phía thượng nguồn khe
      Press_Hinge       — khớp / trụ lò xo (minh họa đàn hồi)
      Press_Finger_Leaf — lá mỏng hướng vào miệng khe (ép single-file)
      Press_Tip_Pad     — đầu mềm tiếp xúc viên
      Press_Bypass_Rail — thành lệch trong: viên không vào khe -> đi vòng lại

    Giả định đĩa quay CCW (nhìn từ trên): viên theo vành -> miệng khe.
    """
    z0 = z_disc + DISC_T
    r_rim = (DISC_D + 0.5) / 2.0
    a_mouth = math.degrees(math.atan2(float(EXIT_Y), -r_rim))
    a_mount = a_mouth - 34.0  # upstream of mouth
    a_tip = a_mouth - 6.0

    mount_c = (0.55, 0.58, 0.62)
    leaf_c = (0.35, 0.55, 0.75)
    tip_c = (0.85, 0.45, 0.15)  # soft pad look
    bypass_c = (0.2, 0.65, 0.55)

    # Mount boss on outer-guide bore face
    r_m = r_rim + 1.5
    mx = r_m * math.cos(math.radians(a_mount))
    my = r_m * math.sin(math.radians(a_mount))
    mount = Part.makeBox(14.0, 18.0, PRESS_FINGER_H + 6.0)
    mount.translate(App.Vector(-7.0, -9.0, z0))
    mount.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), a_mount + 90.0)
    mount.translate(App.Vector(mx, my, 0.0))

    # Hinge pin (vertical) — spring/compliance cue
    hx = (r_rim - 1.0) * math.cos(math.radians(a_mount))
    hy = (r_rim - 1.0) * math.sin(math.radians(a_mount))
    hinge = Part.makeCylinder(2.5, PRESS_FINGER_H + 4.0)
    hinge.translate(App.Vector(hx, hy, z0 - 1.0))

    # Finger leaf: mount -> tip, lightly inside rim, tapered
    r_t = r_rim - 2.5
    tx = r_t * math.cos(math.radians(a_tip))
    ty = r_t * math.sin(math.radians(a_tip))
    dx, dy = tx - hx, ty - hy
    flen = math.hypot(dx, dy)
    ux, uy = dx / flen, dy / flen
    # slight inward bias so tip presses toward gap mouth, not wall
    nx, ny = -uy, ux  # left of travel (toward center if CCW along rim)
    # check toward origin
    if (hx + nx) ** 2 + (hy + ny) ** 2 > hx * hx + hy * hy:
        nx, ny = -nx, -ny

    leaf = Part.makeBox(flen, PRESS_FINGER_T, PRESS_FINGER_H)
    leaf.translate(App.Vector(0.0, -PRESS_FINGER_T / 2.0, z0 + 0.4))
    leaf.rotate(
        App.Vector(0, 0, 0),
        App.Vector(0, 0, 1),
        math.degrees(math.atan2(uy, ux)),
    )
    leaf.translate(App.Vector(hx, hy, 0.0))
    # taper: cut outer corner so tip is thinner (slip-past friendly)
    taper = Part.makeBox(flen * 0.45, PRESS_FINGER_T + 2.0, PRESS_FINGER_H + 2.0)
    taper.translate(App.Vector(flen * 0.55, -PRESS_FINGER_T / 2.0 - 1.0, z0 - 0.5))
    taper.rotate(
        App.Vector(0, 0, 0),
        App.Vector(0, 0, 1),
        math.degrees(math.atan2(uy, ux)),
    )
    taper.translate(App.Vector(hx + 1.2 * nx, hy + 1.2 * ny, 0.0))
    leaf = leaf.cut(taper)

    # Soft tip pad at end of finger
    tip = Part.makeSphere(PRESS_TIP_R)
    tip.translate(App.Vector(tx + 1.0 * nx, ty + 1.0 * ny, z0 + PRESS_TIP_R + 0.3))

    # Bypass rail: short inner fence — overflow slides inside finger -> recirculate
    r_b0 = r_rim - PRESS_BYPASS_DR - 4.0
    r_b1 = r_rim - PRESS_BYPASS_DR + 2.0
    bypass = _annular_sector(
        r_b0, r_b1, a_mount - 5.0, a_mouth + 8.0, z0, 6.0
    )
    # lead-in chamfer block at upstream end (helps pills peel inward)
    a_in = math.radians(a_mount - 2.0)
    lead = Part.makeBox(10.0, 5.0, 5.0)
    lead.translate(App.Vector(0.0, -2.5, z0))
    lead.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), a_mount + 40.0)
    lead.translate(
        App.Vector(
            (r_b1 - 1.0) * math.cos(a_in),
            (r_b1 - 1.0) * math.sin(a_in),
            0.0,
        )
    )

    # Throat funnel wall: narrow channel ~GATE_GAP toward exit (outer side of finger)
    funnel_w = GATE_GAP + 1.5
    funnel = Part.makeBox(22.0, 3.0, PRESS_FINGER_H)
    # place just outside tip, guiding into gap
    a_f = math.radians(a_mouth - 2.0)
    fx = (r_rim - 1.0) * math.cos(a_f)
    fy = (r_rim - 1.0) * math.sin(a_f)
    funnel.translate(App.Vector(0.0, -1.5, z0 + 0.3))
    funnel.rotate(
        App.Vector(0, 0, 0),
        App.Vector(0, 0, 1),
        a_mouth - 90.0,
    )
    funnel.translate(App.Vector(fx, fy, 0.0))

    print(
        "Exit_Press_Guide: mouth@%.0f deg mount@%.0f deg | finger->gap | bypass r=%.0f | "
        "GATE_GAP=%.1f"
        % (a_mouth, a_mount, (r_b0 + r_b1) / 2.0, GATE_GAP)
    )
    return [
        ("Press_Mount", _keep_largest_solid(mount.removeSplitter()), mount_c),
        ("Press_Hinge", hinge.removeSplitter(), mount_c),
        ("Press_Finger_Leaf", _keep_largest_solid(leaf.removeSplitter()), leaf_c),
        ("Press_Tip_Pad", tip.removeSplitter(), tip_c),
        (
            "Press_Bypass_Rail",
            _keep_largest_solid(bypass.fuse(lead).removeSplitter()),
            bypass_c,
        ),
        ("Press_Funnel_Wall", funnel.removeSplitter(), leaf_c),
    ]


def make_clear_exit_cover_parts(z_disc: float) -> list[tuple[str, Part.Shape, tuple]]:
    c = (0.7, 0.85, 0.95)
    z0 = z_disc + DISC_T + 1
    cover = Part.makeBox(70, GATE_GAP + 16, 2.5)
    cover.translate(App.Vector(-DISC_D / 2 - 25, -(GATE_GAP + 16) / 2, z0 + 18))
    w1 = Part.makeBox(70, 2, 16)
    w1.translate(App.Vector(-DISC_D / 2 - 25, GATE_GAP / 2 + 4, z0 + 2))
    w2 = Part.makeBox(70, 2, 16)
    w2.translate(App.Vector(-DISC_D / 2 - 25, -GATE_GAP / 2 - 6, z0 + 2))
    return [
        ("Clear_Cover_Top", cover, c),
        ("Clear_Cover_Wall_A", w1, c),
        ("Clear_Cover_Wall_B", w2, c),
    ]


def make_separator_tab_parts(z_disc: float) -> list[tuple[str, Part.Shape, tuple]]:
    blade = Part.makeBox(35, 6, 8)
    blade.translate(App.Vector(-DISC_D / 2 + 25, -3, z_disc + DISC_T + 2))
    return [("Separator_Blade", blade, (0.15, 0.15, 0.15))]


def make_outlet_chute_parts(z_disc: float) -> list[tuple[str, Part.Shape, tuple]]:
    c = (0.45, 0.45, 0.48)
    z0 = z_disc + DISC_T
    chute = Part.makeBox(30, 28, 40)
    chute.translate(App.Vector(-DISC_D / 2 - 55, -14, z0 - 15))
    hollow = Part.makeBox(24, 22, 38)
    hollow.translate(App.Vector(-DISC_D / 2 - 52, -11, z0 - 14))
    body = chute.cut(hollow)
    return [("Chute_Body", _keep_largest_solid(body.removeSplitter()), c)]


def make_sensor_fork_parts(z_disc: float) -> list[tuple[str, Part.Shape, tuple]]:
    c = (0.05, 0.05, 0.05)
    z0 = z_disc + DISC_T + 3
    x0 = -DISC_D / 2 - 35
    left = Part.makeBox(8, 3, 20)
    left.translate(App.Vector(x0, GATE_GAP / 2 + 2, z0))
    right = Part.makeBox(8, 3, 20)
    right.translate(App.Vector(x0, -GATE_GAP / 2 - 5, z0))
    top = Part.makeBox(8, GATE_GAP + 10, 3)
    top.translate(App.Vector(x0, -GATE_GAP / 2 - 5, z0 + 17))
    return [
        ("Sensor_Arm_L", left, c),
        ("Sensor_Arm_R", right, c),
        ("Sensor_Bridge", top, c),
    ]


def make_collection_drawer_parts() -> list[tuple[str, Part.Shape, tuple]]:
    c = (0.75, 0.85, 0.9)
    d = Part.makeBox(95, 65, 40)
    d.translate(App.Vector(-DISC_D / 2 - 40, BOX_D / 2 - 75, 28))
    inn = Part.makeBox(87, 55, 32)
    inn.translate(App.Vector(-DISC_D / 2 - 36, BOX_D / 2 - 68, 34))
    return [("Drawer_Shell", _keep_largest_solid(d.cut(inn).removeSplitter()), c)]


def make_control_panel_parts() -> list[tuple[str, Part.Shape, tuple]]:
    c = (0.15, 0.18, 0.35)
    panel = Part.makeBox(95, 6, 70)
    panel.translate(App.Vector(15, -BOX_D / 2 - 2, BOX_H - 75))
    disp = Part.makeBox(40, 4, 18)
    disp.translate(App.Vector(25, -BOX_D / 2 - 1, BOX_H - 55))
    return [("Panel_Bezel", _keep_largest_solid(panel.cut(disp).removeSplitter()), c)]


def add_part(doc, name, shape, color, transparency=0):
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    vo = getattr(obj, "ViewObject", None)
    if vo is not None:
        vo.ShapeColor = color
        if transparency:
            vo.Transparency = transparency
    return obj


def add_group(doc, name, children, use_part=True):
    """
    Parent folder in the FreeCAD tree; children stay editable solids.
    App::Part  -> assembly (has Placement; move whole group)
    App::DocumentObjectGroup -> simple tree folder
    """
    typ = "App::Part" if use_part else "App::DocumentObjectGroup"
    grp = doc.addObject(typ, name)
    kids = [c for c in children if c is not None]
    if hasattr(grp, "addObjects"):
        grp.addObjects(kids)
    else:
        grp.Group = kids
    return grp


def _placement_copy(pl: App.Placement) -> App.Placement:
    return App.Placement(App.Vector(pl.Base), App.Rotation(pl.Rotation))


def _placement_is_identity(pl: App.Placement, tol: float = 1e-6) -> bool:
    b = pl.Base
    if abs(b.x) > tol or abs(b.y) > tol or abs(b.z) > tol:
        return False
    # Identity rotation ≈ angle 0
    try:
        ang = abs(pl.Rotation.Angle)
    except Exception:
        return True
    return ang < 1e-6 or abs(ang - 2.0 * math.pi) < 1e-6


def capture_open_document_state() -> tuple[
    dict[str, App.Placement], dict[str, bool], set[str], set[str]
]:
    """Read Placement + Visibility from any currently open FreeCAD docs (user may have moved/hidden)."""
    placements: dict[str, App.Placement] = {}
    visibility: dict[str, bool] = {}
    part_names: set[str] = set()
    all_names: set[str] = set()
    for doc_name in list(App.listDocuments().keys()):
        doc = App.getDocument(doc_name)
        for obj in doc.Objects:
            all_names.add(obj.Name)
            if obj.TypeId == "App::Part":
                part_names.add(obj.Name)
            if hasattr(obj, "Placement"):
                placements[obj.Name] = _placement_copy(obj.Placement)
            vo = getattr(obj, "ViewObject", None)
            if vo is not None and hasattr(vo, "Visibility"):
                visibility[obj.Name] = bool(vo.Visibility)
    return placements, visibility, part_names, all_names


def load_state_from_fcstd(
    path: Path,
) -> tuple[dict[str, App.Placement], dict[str, bool], set[str], set[str]]:
    """
    Parse last-saved FCStd so rebuild can keep user Placement / Visibility.
    Source of truth = this .FCStd only (never a sidecar JSON).
    Returns (placements, visibility, App::Part names, all object names).
    """
    placements: dict[str, App.Placement] = {}
    visibility: dict[str, bool] = {}
    part_names: set[str] = set()
    all_names: set[str] = set()
    if not path.is_file():
        return placements, visibility, part_names, all_names
    try:
        with zipfile.ZipFile(path, "r") as zf:
            names = set(zf.namelist())
            if "Document.xml" in names:
                xml = zf.read("Document.xml").decode("utf-8", errors="replace")
                for t, n in re.findall(
                    r'<Object type="([^"]+)" name="([^"]+)"', xml
                ):
                    all_names.add(n)
                    if t == "App::Part":
                        part_names.add(n)
                for m in re.finditer(
                    r'<Object\b[^>]*\bname="([^"]+)"[^>]*>.*?</Object>',
                    xml,
                    flags=re.DOTALL,
                ):
                    oname = m.group(1)
                    all_names.add(oname)
                    block = m.group(0)
                    pm = re.search(
                        r'<Property name="Placement"[^>]*>\s*<PropertyPlacement\s+([^/]+)/>',
                        block,
                    )
                    if not pm:
                        continue
                    attrs = dict(re.findall(r'(\w+)="([^"]*)"', pm.group(1)))
                    try:
                        px = float(attrs.get("Px", 0))
                        py = float(attrs.get("Py", 0))
                        pz = float(attrs.get("Pz", 0))
                        q0 = float(attrs.get("Q0", 0))
                        q1 = float(attrs.get("Q1", 0))
                        q2 = float(attrs.get("Q2", 0))
                        q3 = float(attrs.get("Q3", 1))
                    except ValueError:
                        continue
                    placements[oname] = App.Placement(
                        App.Vector(px, py, pz),
                        App.Rotation(q0, q1, q2, q3),
                    )
            if "GuiDocument.xml" in names:
                gxml = zf.read("GuiDocument.xml").decode("utf-8", errors="replace")
                for m in re.finditer(
                    r'<ViewProvider\b[^>]*\bname="([^"]+)"[^>]*>.*?</ViewProvider>',
                    gxml,
                    flags=re.DOTALL,
                ):
                    oname = m.group(1)
                    vm = re.search(
                        r'<Property name="Visibility"[^>]*>\s*<Bool value="(true|false)"/>',
                        m.group(0),
                    )
                    if vm:
                        visibility[oname] = vm.group(1) == "true"
    except Exception as exc:
        print("load_state_from_fcstd: skip (%s)" % exc)
    return placements, visibility, part_names, all_names


def apply_preserved_state(
    doc,
    placements: dict[str, App.Placement],
    visibility: dict[str, bool],
    prior_part_names: set[str] | None = None,
) -> None:
    """
    Re-apply user Placement / Visibility after geometry rebuild.

    Placement: only for assemblies the user typically Transform's as a group,
    and only if they were already App::Part in the previous FCStd.
    Children are authored in world coordinates — do not apply leftover
    Part::Feature Placement (e.g. motor) onto new App::Part parents.
    """
    # Geometry of these parents is world-posed in children; parent Placement
    # is the user's Transform offset relative to that design pose.
    # Exit_Guide_Tray Placement is free — Transform in GUI; restored each rebuild
    allow_placement = {"Exit_Guide_Tray", "Gap_Lining_Up", "Disc_Access_Lid"}
    prior = prior_part_names or set()
    moved = []
    for name, pl in placements.items():
        obj = doc.getObject(name)
        if obj is None or not hasattr(obj, "Placement"):
            continue
        if obj.TypeId != "App::Part":
            continue
        if name not in allow_placement or name not in prior:
            continue
        if _placement_is_identity(pl):
            continue
        obj.Placement = _placement_copy(pl)
        b = pl.Base
        moved.append("%s->(%.2f,%.2f,%.2f)" % (name, b.x, b.y, b.z))
    hidden = []
    for name, vis in visibility.items():
        obj = doc.getObject(name)
        if obj is None:
            continue
        vo = getattr(obj, "ViewObject", None)
        if vo is None or not hasattr(vo, "Visibility"):
            continue
        vo.Visibility = vis
        if not vis:
            hidden.append(name)
    if moved:
        print("Preserved Placement: " + "; ".join(moved))
    else:
        print("Preserved Placement: (none)")
    if hidden:
        print("Preserved hidden: " + ", ".join(hidden))


def main() -> None:
    # 1) Live open docs (same FreeCAD session) win over disk
    # 2) Else last-saved FCStd — user may have Transform'd then saved / agent Ctrl+S
    live_pl, live_vis, live_parts, live_names = capture_open_document_state()
    disk_pl, disk_vis, disk_parts, disk_names = load_state_from_fcstd(FCSTD)
    placements = {**disk_pl, **live_pl}
    visibility = {**disk_vis, **live_vis}
    prior_parts = disk_parts | live_parts
    # Objects present in last save / open doc — deleted assemblies are not rebuilt
    prior_names = disk_names | live_names | set(placements.keys())
    if live_pl:
        print("Captured state from open document(s): %d objects" % len(live_pl))
    elif disk_pl:
        print("Captured state from FCStd on disk: %d objects" % len(disk_pl))

    def _keep_assembly(name: str) -> bool:
        """Respect user deletions in FCStd: do not recreate missing top-level groups."""
        if not prior_names:
            return True
        return name in prior_names

    for name in list(App.listDocuments().keys()):
        App.closeDocument(name)

    doc = App.newDocument("Rx4_Manual_Gate")

    z_disc = TOP_Z + BOX_T + 1.0
    face_z = SHELF_Z - 8.0 - COUPLER_L
    z_coupler = face_z + BOSS_H + 2.0
    z_shaft0 = z_coupler + 5.0
    shaft_len = (z_disc + DISC_T + HUB_H) - z_shaft0 + 2.0

    assemblies: list[tuple[str, list, int]] = [
        ("L_Bracket_Mount_Frame", make_housing_mount_parts(face_z), 35),
        ("Hole_Align_Pins", make_hole_align_pin_parts(face_z), 0),
        ("JGB37_520_Motor", make_motor_parts(), 0),
        ("Flexible_Coupler", make_coupler_parts(z_coupler), 0),
        ("Disc_Shaft", make_drive_shaft_parts(z_shaft0, shaft_len), 0),
        ("Bearing_Upper", make_bearing_parts("Bearing_Upper", TOP_Z - 1), 0),
        (
            "Bearing_Lower",
            make_bearing_parts("Bearing_Lower", SHELF_Z + (BOX_T - BEARING_H) / 2),
            0,
        ),
        ("Turntable_Disc", make_disc_parts(z_disc), 0),
        ("Center_Hub", make_center_hub_parts(z_disc), 0),
        ("Outer_Guide_Arc", make_outer_guide_parts(z_disc), 0),
        # Disc_Access_Lid built below (nested Lid_Top)
        ("Gap_Lining_Up", make_lining_up_gap_parts(z_disc), 0),
        ("Exit_Press_Guide", make_exit_press_guide_parts(z_disc), 0),
        ("Clear_Exit_Cover", make_clear_exit_cover_parts(z_disc), 60),
        ("Separator_Tab", make_separator_tab_parts(z_disc), 0),
        ("Outlet_Chute", make_outlet_chute_parts(z_disc), 0),
        ("IR_Sensor_Fork", make_sensor_fork_parts(z_disc), 0),
        ("Collection_Drawer", make_collection_drawer_parts(), 50),
        ("Control_Panel", make_control_panel_parts(), 0),
    ]

    counts = []
    skipped = []
    for parent, specs, tr in assemblies:
        if not _keep_assembly(parent):
            skipped.append(parent)
            continue
        kids = [
            add_part(doc, n, sh, col, transparency=tr) for n, sh, col in specs
        ]
        add_group(doc, parent, kids)
        counts.append("%s(%d)" % (parent, len(kids)))

    # Disc_Access_Lid: Top + Bottom + solid annulus fill + walls/bars
    if _keep_assembly("Disc_Access_Lid"):
        lid_top_objs = []
        hub_kids: list = []
        sw_chute_kids: list = []
        sw_rest = None
        for n, sh, col in make_lid_top_parts(z_disc):
            tr = 0 if n == "Lid_Top_Arc_Corner" else 25
            obj = add_part(doc, n, sh, col, transparency=tr)
            if n.startswith("Lid_Top_Deck_S_Hub_"):
                hub_kids.append(obj)
            elif n.startswith("Lid_Top_Out_SW_Chute_"):
                sw_chute_kids.append(obj)
            elif n == "Lid_Top_Out_SW_Rest":
                sw_rest = obj
            else:
                lid_top_objs.append(obj)
        if hub_kids:
            lid_top_objs.append(add_group(doc, "Lid_Top_Deck_S_Hub", hub_kids))
        sw_kids: list = []
        if sw_chute_kids:
            sw_kids.append(add_group(doc, "Lid_Top_Out_SW_Chute", sw_chute_kids))
        if sw_rest is not None:
            sw_kids.append(sw_rest)
        if sw_kids:
            lid_top_objs.append(add_group(doc, "Lid_Top_Out_SW", sw_kids))
        lid_top_grp = add_group(doc, "Lid_Top", lid_top_objs)
        lid_kids = [lid_top_grp]
        lid_bot_objs = [
            add_part(doc, n, sh, col, transparency=25)
            for n, sh, col in make_lid_bottom_parts(z_disc)
        ]
        if lid_bot_objs:
            lid_kids.append(add_group(doc, "Lid_Bottom", lid_bot_objs))
        lid_fill_objs = [
            add_part(doc, n, sh, col, transparency=20)
            for n, sh, col in make_lid_fill_parts(z_disc)
        ]
        if lid_fill_objs:
            lid_kids.append(add_group(doc, "Lid_Fill", lid_fill_objs))
        lid_rest = [
            add_part(doc, n, sh, col, transparency=25)
            for n, sh, col in make_disc_access_lid_parts(z_disc)
        ]
        drive_objs = []
        if _keep_assembly("Width_Adjust_Drive") or _keep_assembly("Width_Lead_Screw"):
            drive_objs = [
                add_part(doc, n, sh, col, transparency=15)
                for n, sh, col in make_width_adjust_drive_parts(z_disc)
            ]
            if drive_objs:
                lid_rest.append(add_group(doc, "Width_Adjust_Drive", drive_objs))
        # Height_Adjust_Drive (settings-gated; new feature always built when enabled)
        h_drive_objs = []
        if bool(_LID_CFG.get("height_bar", {}).get("drive", {}).get("enabled", False)):
            h_drive_objs = [
                add_part(doc, n, sh, col, transparency=15)
                for n, sh, col in make_height_adjust_drive_parts(z_disc)
            ]
            if h_drive_objs:
                lid_rest.append(add_group(doc, "Height_Adjust_Drive", h_drive_objs))
        add_group(doc, "Disc_Access_Lid", lid_kids + lid_rest)
        counts.append(
            "Disc_Access_Lid(Top %d + Bottom %d + Fill %d + rest %d + w_drive %d + h_drive %d)"
            % (
                len(lid_top_objs),
                len(lid_bot_objs),
                len(lid_fill_objs),
                len(lid_rest) - (1 if drive_objs else 0) - (1 if h_drive_objs else 0),
                len(drive_objs),
                len(h_drive_objs),
            )
        )
    else:
        skipped.append("Disc_Access_Lid")
        lid_top_objs = []
        lid_top_grp = None

    # Exit_Guide_Tray: nested Exit_Tray_Floor (basic solids) + walls
    if _keep_assembly("Exit_Guide_Tray"):
        floor_objs = [
            add_part(doc, n, sh, col, transparency=55)
            for n, sh, col in make_exit_tray_floor_basic_parts(z_disc)
        ]
        floor_grp = add_group(doc, "Exit_Tray_Floor", floor_objs)
        wall_objs = [
            add_part(doc, n, sh, col, transparency=55)
            for n, sh, col in make_exit_guide_tray_parts(z_disc)
        ]
        add_group(doc, "Exit_Guide_Tray", [floor_grp] + wall_objs)
        counts.append(
            "Exit_Guide_Tray(Floor %d + walls %d)" % (len(floor_objs), len(wall_objs))
        )
    else:
        skipped.append("Exit_Guide_Tray")

    if skipped:
        print("Skipped deleted assemblies: " + ", ".join(skipped))

    print("Assemblies -> basic children: " + ", ".join(counts))
    print("GATE_GAP=%.1fmm | Placement restore = App::Part only" % GATE_GAP)

    apply_preserved_state(doc, placements, visibility, prior_parts)

    # Disc_Access_Lid: children authored with wall bottoms at disc_top + disc_clear.
    # Parent Pz must be 0 so Lid_Wall_Arc_* underside stays 0.5 mm above the disc.
    # (Old FCStd had Pz=-3 which sank walls into the disc.)
    lid_grp = doc.getObject("Disc_Access_Lid")
    if lid_grp is not None and hasattr(lid_grp, "Placement"):
        pl = lid_grp.Placement
        if abs(float(pl.Base.z)) > 1e-6:
            print(
                "Disc_Access_Lid: Pz %.3f -> 0 (Lid_Wall bottom = disc+%.1f mm)"
                % (pl.Base.z, LID_DISC_CLEAR)
            )
            pl.Base = App.Vector(pl.Base.x, pl.Base.y, 0.0)
            lid_grp.Placement = pl

    # Force-show full sealed Lid_Top (user may have hidden older children)
    if lid_top_grp is not None:
        for obj in lid_top_objs + [lid_top_grp, doc.getObject("Disc_Access_Lid")]:
            if obj is None:
                continue
            vo = getattr(obj, "ViewObject", None)
            if vo is not None and hasattr(vo, "Visibility"):
                vo.Visibility = True

    doc.recompute()
    doc.saveAs(str(FCSTD))
    print(f"Saved: {FCSTD}")
    print(
        "Lid clearance: wall bottoms at disc_top+%.1f mm (Disc_Access_Lid Pz=0)"
        % LID_DISC_CLEAR
    )

    if App.GuiUp and Gui is not None:
        Gui.ActiveDocument = Gui.getDocument(doc.Name)
        Gui.activeDocument().activeView().viewIsometric()
        Gui.SendMsgToActiveView("ViewFit")
        Gui.updateGui()
        print("Shown in GUI")
    else:
        App.closeDocument(doc.Name)


main()
