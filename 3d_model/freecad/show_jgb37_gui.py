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
from pathlib import Path

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
DISC_D = 200.0
DISC_T = 5.0
DRIVE_SHAFT_D = 6.0
BEARING_OD, BEARING_ID, BEARING_H = 19.0, 6.0, 6.0  # 626ZZ
COUPLER_OD, COUPLER_L = 18.0, 25.0
HUB_D, HUB_H = 36.0, 12.0

# Housing: taller so JGB37 sits fully inside (motor/bracket pose unchanged)
BOX_W, BOX_D = 280.0, 260.0
BOX_T = 4.0
# Keep SAME placement rule as before: face_z = SHELF_Z - 8 - COUPLER_L
# Raise shelf so motor body (below face) clears floor.
MOTOR_BODY_LEN = GB_L + CAN_L + REAR_BOSS_H + TERM_L  # ~58.7
SHELF_Z = BOX_T + MOTOR_BODY_LEN + COUPLER_L + 8.0 + 12.0  # ~108
BOX_H = SHELF_Z + 75.0
TOP_Z = BOX_H
SPAN = TOP_Z - SHELF_Z
FACE_Z = SHELF_Z - 8.0 - COUPLER_L  # identical formula as previous place_motor_vertical

# Manual gate: knob on raised tower LEFT of disc; single-file channel to -X
GATE_GAP = 11.0
KNOB_D, KNOB_H = 32.0, 16.0


def _cyl_z(d: float, h: float, z0: float, x=0.0, y=0.0) -> Part.Shape:
    c = Part.makeCylinder(d / 2, h)
    c.translate(App.Vector(x, y, z0))
    return c


def make_box_frame() -> Part.Shape:
    """
    Rx-4 style body: shell, circular well for disc, internal bearing shelf,
    front opening for collection drawer.
    """
    ox = -BOX_W / 2 + 15
    oy = -BOX_D / 2
    outer = Part.makeBox(BOX_W, BOX_D, BOX_H)
    outer.translate(App.Vector(ox, oy, 0))

    inner = Part.makeBox(BOX_W - 2 * BOX_T, BOX_D - 2 * BOX_T, BOX_H - BOX_T + 1)
    inner.translate(App.Vector(ox + BOX_T, oy + BOX_T, BOX_T))
    shell = outer.cut(inner)

    lid = Part.makeBox(BOX_W, BOX_D, BOX_T)
    lid.translate(App.Vector(ox, oy, TOP_Z))
    lid = lid.cut(_cyl_z(DISC_D + 8, BOX_T + 2, TOP_Z - 1))
    notch = Part.makeBox(40, 50, BOX_T + 2)
    notch.translate(App.Vector(-DISC_D / 2 - 35, -25, TOP_Z - 1))
    lid = lid.cut(notch)

    shelf = Part.makeBox(BOX_W - 2 * BOX_T - 4, BOX_D - 2 * BOX_T - 4, BOX_T)
    shelf.translate(App.Vector(ox + BOX_T + 2, oy + BOX_T + 2, SHELF_Z))
    shelf = shelf.cut(_cyl_z(BEARING_OD + 0.3, BOX_T + 1, SHELF_Z - 0.5))

    drawer_cut = Part.makeBox(100, 25, 55)
    drawer_cut.translate(App.Vector(-DISC_D / 2 - 30, oy + BOX_D - BOX_T - 5, 25))
    shell = shell.cut(drawer_cut)

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
    solids = list(shape.Solids)
    if len(solids) <= 1:
        return shape
    solids.sort(key=lambda s: s.Volume, reverse=True)
    return solids[0]


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
        + ", ".join("Ø%.1f@(%.2f,%.2f)" % (d, x, y) for x, y, d in motor_face_holes_world())
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
            print("WARN hole i=%d Ø%.1f dist=%.3f expected~%.3f" % (i, d, dist, d / 2.0))
    print(
        "Housing+mount ONE solid | motor holes verify=%s (PCD31 Ø3/Ø4, no lid vents)"
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


def make_outer_guide_arc(z_disc: float) -> Part.Shape:
    """
    Partial black curved baffle on far side of disc (NOT full ring).
    From video: arc along +X / +Y perimeter, opposite exit.
    """
    z0 = z_disc
    h = 22.0
    t = 4.0
    outer = _cyl_z(DISC_D + 2 * t, h, z0)
    inner = _cyl_z(DISC_D + 0.5, h + 1, z0 - 0.5)
    ring = outer.cut(inner)
    # Keep only ~150° arc on +X side (away from -X exit)
    cut = Part.makeBox(DISC_D + 40, DISC_D + 40, h + 2)
    cut.translate(App.Vector(-(DISC_D + 40), -(DISC_D + 20), z0 - 1))
    return ring.cut(cut)


def make_manual_gate_assembly(z_disc: float):
    """
    Manual Gate (video): raised white tower + black knurled knob on TOP.
    Knob moves radial gate → sets single-file gap into clear channel (-X).
    """
    z0 = z_disc + DISC_T
    # Raised white housing (tower) near exit, slightly +Y of channel
    tower = Part.makeBox(55, 45, 48)
    tower.translate(App.Vector(-DISC_D / 2 - 15, 15, z0))
    # Hollow underside over disc
    under = Part.makeBox(40, 35, 20)
    under.translate(App.Vector(-DISC_D / 2 - 5, 18, z0 - 1))
    tower = tower.cut(under)

    # Black knurled knob on TOP of tower
    kx, ky = -DISC_D / 2 + 10, 35
    knob = _cyl_z(KNOB_D, KNOB_H, z0 + 48, kx, ky)
    for i in range(10):
        a = math.radians(i * 36)
        fx = kx + (KNOB_D / 2 - 0.8) * math.cos(a)
        fy = ky + (KNOB_D / 2 - 0.8) * math.sin(a)
        knob = knob.cut(_cyl_z(2.8, KNOB_H + 1, z0 + 47.5, fx, fy))

    # Vertical adjust shaft
    screw = _cyl_z(5.0, 55, z0 + 5, kx, ky)

    # Sliding gate leaf — creates GATE_GAP channel along -X exit
    gate = Part.makeBox(3.0, 55.0, 18.0)
    gate.translate(App.Vector(-GATE_GAP / 2 - 3, -20, z0 + 1))
    # Fixed guide opposite
    guide = Part.makeBox(3.0, 55.0, 18.0)
    guide.translate(App.Vector(GATE_GAP / 2, -20, z0 + 1))
    # Rotate channel to -X: currently along Y; need along -X from rim
    # Rebuild gate at exit on -X side
    gate = Part.makeBox(50.0, 3.0, 18.0)
    gate.translate(App.Vector(-DISC_D / 2 - 5, GATE_GAP / 2, z0 + 1))
    guide = Part.makeBox(50.0, 3.0, 18.0)
    guide.translate(App.Vector(-DISC_D / 2 - 5, -GATE_GAP / 2 - 3, z0 + 1))

    body = tower.fuse(gate).fuse(guide)
    return body, knob, screw


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


def add_part(doc, name, shape, color, transparency=0):
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    vo = getattr(obj, "ViewObject", None)
    if vo is not None:
        vo.ShapeColor = color
        if transparency:
            vo.Transparency = transparency
    return obj


def main() -> None:
    for name in list(App.listDocuments().keys()):
        App.closeDocument(name)

    doc = App.newDocument("Rx4_Manual_Gate")

    z_disc = TOP_Z + BOX_T + 1.0
    face_z = SHELF_Z - 8.0 - COUPLER_L
    z_coupler = face_z + BOSS_H + 2.0
    z_shaft0 = z_coupler + 5.0
    shaft_len = (z_disc + DISC_T + HUB_H) - z_shaft0 + 2.0

    motor_p = place_motor_vertical(make_motor())
    # Mount grown into housing — single printable / molded body
    frame = make_housing_with_mount(face_z)
    align_pins = make_hole_align_pins(face_z)

    brg_u = make_bearing(TOP_Z - 1)
    brg_l = make_bearing(SHELF_Z + (BOX_T - BEARING_H) / 2)
    coupler = make_coupler(z_coupler)
    shaft = make_drive_shaft(z_shaft0, shaft_len)
    disc = make_disc(z_disc)
    hub = make_center_hub(z_disc)
    guide = make_outer_guide_arc(z_disc)
    gate_body, knob, screw = make_manual_gate_assembly(z_disc)
    clear = make_clear_exit_cover(z_disc)
    sep = make_separator_tab(z_disc)
    chute = make_outlet_chute(z_disc)
    sensor = make_sensor_fork(z_disc)
    drawer = make_collection_drawer()
    panel = make_control_panel()

    mbb = motor_p.BoundBox
    print(
        f"Box H={BOX_H:.0f} | motor Z=[{mbb.ZMin:.1f},{mbb.ZMax:.1f}] "
        f"inside={'YES' if mbb.ZMin >= BOX_T - 0.05 else 'NO'} | "
        f"Housing+mount=ONE continuous solid"
    )

    add_part(
        doc,
        "L_Bracket_Mount_Frame",
        frame,
        (0.85, 0.88, 0.86),
        transparency=35,
    )  # housing + mount = one solid
    add_part(doc, "Hole_Align_Pins", align_pins, (1.0, 0.15, 0.05))  # must pass through motor+flange
    add_part(doc, "JGB37_520_Motor", motor_p, (0.75, 0.75, 0.78))
    add_part(doc, "Flexible_Coupler", coupler, (0.85, 0.55, 0.15))
    add_part(doc, "Disc_Shaft", shaft, (0.55, 0.55, 0.6))
    add_part(doc, "Bearing_Upper", brg_u, (0.15, 0.45, 0.85))
    add_part(doc, "Bearing_Lower", brg_l, (0.15, 0.45, 0.85))
    add_part(doc, "Turntable_Disc", disc, (0.95, 0.95, 0.95))
    add_part(doc, "Center_Hub", hub, (0.08, 0.08, 0.08))
    add_part(doc, "Outer_Guide_Arc", guide, (0.12, 0.12, 0.14))
    add_part(doc, "Manual_Gate_Tower", gate_body, (0.92, 0.92, 0.93))
    add_part(doc, "Gap_Knob_TOP", knob, (0.05, 0.05, 0.05))
    add_part(doc, "Gap_Screw", screw, (0.55, 0.55, 0.58))
    add_part(doc, "Clear_Exit_Cover", clear, (0.7, 0.85, 0.95), transparency=60)
    add_part(doc, "Separator_Tab", sep, (0.15, 0.15, 0.15))
    add_part(doc, "Outlet_Chute", chute, (0.45, 0.45, 0.48))
    add_part(doc, "IR_Sensor_Fork", sensor, (0.05, 0.05, 0.05))
    add_part(doc, "Collection_Drawer", drawer, (0.75, 0.85, 0.9), transparency=50)
    add_part(doc, "Control_Panel", panel, (0.15, 0.18, 0.35))

    doc.recompute()
    doc.saveAs(str(FCSTD))
    print(f"Saved: {FCSTD}")

    if App.GuiUp and Gui is not None:
        Gui.ActiveDocument = Gui.getDocument(doc.Name)
        Gui.activeDocument().activeView().viewIsometric()
        Gui.SendMsgToActiveView("ViewFit")
        Gui.updateGui()
        print("Shown in GUI")
    else:
        App.closeDocument(doc.Name)


main()
