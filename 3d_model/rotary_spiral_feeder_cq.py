"""
Rotary spiral disc feeder — CountingMachine (CadQuery)

CONSTRAINT: pure ROTARY drive only — NO vibration / NO vibratory bowl.

Mechanism:
  MOVING  : conical disc + helical flight(s) — Archimedes screw in a bowl
            + drive_hub on Ø6 mm D-shaft (geared DC)
  FIXED   : base (motor face + 626ZZ + frame feet), bowl, outlet ring, lid
            + optional motor_clamp / frame_riser

Drive motor (purchased):
  GB37 / JGB37-520 class — 24V (đồng bộ nguồn PLC FX3U-24MT), ~30 RPM,
  CENTER Ø6 mm D-shaft, 6×M3 PCD31
  Do NOT use eccentric/offset-shaft variants.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import math

import cadquery as cq


@dataclass
class Params:
    # Envelope (Bambu P1S friendly)
    bowl_id: float = 120.0
    bowl_od: float = 132.0
    bowl_h: float = 85.0
    wall_t: float = 2.8

    # Rotor / helix
    rotor_cone_h: float = 18.0
    rotor_hub_d: float = 36.0
    spiral_turns: float = 2.25
    spiral_start_z: float = 6.0
    spiral_end_z: float = 72.0
    flight_w: float = 11.0
    flight_t: float = 3.0
    flight_clearance: float = 1.0
    n_flights: int = 2

    # Multi-outlet counting ring (top)
    outlet_count: int = 4
    outlet_w: float = 10.0
    outlet_h: float = 14.0
    outlet_depth: float = 28.0
    sensor_slot_w: float = 8.0

    # ---- Geared DC motor: GB37 / JGB37-520 class (CENTER shaft), 24V ----
    # Same 24V rail as Mitsubishi FX3U-24MT. Drive via relay/MOSFET — not direct Y output.
    # Recommend: 24V, 30 RPM, metal gear, Ø6 mm D-shaft CENTERED (not eccentric).
    motor_name: str = "GB37-24V-30RPM"
    motor_voltage_v: float = 24.0
    plc_model: str = "FX3U-24MT"
    motor_body_d: float = 37.0
    motor_gearbox_l: float = 29.0
    motor_can_l: float = 30.0
    motor_shaft_d: float = 6.0
    motor_shaft_l: float = 15.0
    motor_shaft_flat: float = 5.4          # across flat of D
    motor_mount_pcd: float = 31.0          # 6x M3 on hex, neighbor spacing 15.5
    motor_mount_n: int = 6
    motor_mount_hole_d: float = 3.2        # clearance for M3 into gearbox (screw ≤3mm deep)
    motor_boss_d: float = 12.0             # face pilot boss around shaft (typical)

    # Bearing under disc (takes radial load off gearbox): 626ZZ = 6x19x6
    bearing_id: float = 6.0
    bearing_od: float = 19.0
    bearing_h: float = 6.0
    bearing_seat_clear: float = 0.25

    # Base / frame
    base_od: float = 160.0
    base_t: float = 10.0
    mount_hole_d: float = 3.4
    disc_key_d: float = 28.0
    frame_hole_d: float = 5.5              # M5 to machine deck
    frame_span: float = 130.0              # square bolt pattern on frame
    frame_foot_t: float = 8.0

    def __post_init__(self) -> None:
        if self.outlet_count < 2:
            raise ValueError("outlet_count >= 2")
        if self.n_flights < 1:
            raise ValueError("n_flights >= 1")

    @property
    def spiral_r(self) -> float:
        return self.bowl_id / 2 - self.flight_clearance - self.flight_w / 2

    @property
    def spiral_pitch(self) -> float:
        rise = self.spiral_end_z - self.spiral_start_z
        return rise / self.spiral_turns

    @property
    def outlet_angles_deg(self) -> list[float]:
        return [i * 360.0 / self.outlet_count for i in range(self.outlet_count)]

    @property
    def shaft_bore(self) -> float:
        return self.motor_shaft_d + 0.25  # print clearance on D-shaft


def _cyl(d: float, h: float) -> cq.Workplane:
    return cq.Workplane("XY").circle(d / 2).extrude(h)


# ---------------------------------------------------------------------------
# MOVING parts
# ---------------------------------------------------------------------------

def make_spiral_flight(p: Params, start_angle_deg: float = 0.0) -> cq.Workplane:
    """One helical flight swept along an outer race radius."""
    pitch = p.spiral_pitch
    height = p.spiral_end_z - p.spiral_start_z
    r = p.spiral_r
    z0 = p.spiral_start_z

    wire = cq.Wire.makeHelix(
        pitch=pitch,
        height=height,
        radius=r,
        center=cq.Vector(0, 0, z0),
        dir=cq.Vector(0, 0, 1),
        lefthand=False,
    )
    if start_angle_deg:
        wire = wire.rotate(
            cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), start_angle_deg
        )

    # Profile must sit on the helix start (radius r, z0), not at origin
    ang0 = math.radians(start_angle_deg)
    x0, y0 = r * math.cos(ang0), r * math.sin(ang0)
    profile = (
        cq.Workplane("XY")
        .transformed(offset=(x0, y0, z0), rotate=(0, 0, start_angle_deg))
        .rect(p.flight_w, p.flight_t)
    )
    return profile.sweep(wire, isFrenet=True)


def make_moving_rotor(p: Params) -> cq.Workplane:
    """
    Conical disc + multi-start spiral flights.
    This is the ONLY large rotating body (plus hub).
    """
    # Conical floor: revolve trapezoid
    cone = (
        cq.Workplane("XZ")
        .moveTo(p.disc_key_d / 2, 0)
        .lineTo(p.bowl_id / 2 - p.flight_clearance - 0.5, 0)
        .lineTo(p.rotor_hub_d / 2, p.rotor_cone_h)
        .lineTo(p.disc_key_d / 2, p.rotor_cone_h)
        .close()
        .revolve(360)
    )
    # Center hub boss
    boss = _cyl(p.rotor_hub_d, p.rotor_cone_h + 8)
    rotor = cone.union(boss)

    # Key bore for drive hub
    rotor = rotor.cut(_cyl(p.disc_key_d - 0.4, p.rotor_cone_h + 10))
    for a in (0, 90, 180, 270):
        slot = (
            cq.Workplane("XY")
            .transformed(rotate=(0, 0, a))
            .center(p.disc_key_d / 2 - 1, 0)
            .rect(4, 6)
            .extrude(p.rotor_cone_h + 10)
        )
        rotor = rotor.cut(slot)

    # Helical flights
    for i in range(p.n_flights):
        ang = i * (360.0 / p.n_flights)
        flight = make_spiral_flight(p, start_angle_deg=ang)
        rotor = rotor.union(flight)

    return rotor


def make_moving_drive_hub(p: Params) -> cq.Workplane:
    """
    Couples Ø6 mm D-shaft (geared DC) → keyed rotor.
    Flange sits on 626ZZ inner race; M3 set-screw on flat.
    """
    h = p.rotor_cone_h + 12
    flange_d = p.bearing_od + 10
    hub = (
        cq.Workplane("XY")
        .circle(flange_d / 2)
        .extrude(3)
        .faces(">Z").workplane()
        .circle((p.disc_key_d - 0.5) / 2)
        .extrude(h - 3)
    )
    for a in (0, 90, 180, 270):
        tab = (
            cq.Workplane("XY")
            .transformed(rotate=(0, 0, a), offset=(0, 0, 3))
            .center(p.disc_key_d / 2 - 1.2, 0)
            .rect(3.6, 5.6)
            .extrude(p.rotor_cone_h)
        )
        hub = hub.union(tab)

    # D-shaft bore
    hub = hub.cut(_cyl(p.shaft_bore, h + 1))
    # Flat pocket matching D-shaft flat (depth from bore wall)
    flat_cut = (
        cq.Workplane("XY")
        .center(p.motor_shaft_d / 2 - (p.motor_shaft_d - p.motor_shaft_flat) + 1.2, 0)
        .rect(3.2, p.motor_shaft_flat + 0.3)
        .extrude(h + 1)
    )
    hub = hub.cut(flat_cut)

    # M3 set-screw from +X onto flat
    ss = (
        cq.Workplane("YZ")
        .circle(1.5)
        .extrude(p.disc_key_d)
        .translate((0, 0, 8))
    )
    hub = hub.cut(ss)

    # Access / lightening on flange
    for a in (45, 135, 225, 315):
        hx = (flange_d / 2 - 5) * math.cos(math.radians(a))
        hy = (flange_d / 2 - 5) * math.sin(math.radians(a))
        hub = hub.cut(_cyl(3.2, 4).translate((hx, hy, -0.5)))
    return hub


def make_moving_shaft_collar(p: Params) -> cq.Workplane:
    """Optional lock collar under bearing (on shaft) — keeps hub from dropping."""
    c = (
        cq.Workplane("XY")
        .circle(12 / 2)
        .extrude(5)
        .faces(">Z").workplane()
        .hole(p.shaft_bore)
    )
    flat = (
        cq.Workplane("XY")
        .center(p.motor_shaft_d / 2 - (p.motor_shaft_d - p.motor_shaft_flat) + 1.0, 0)
        .rect(3.0, p.motor_shaft_flat + 0.3)
        .extrude(6)
    )
    c = c.cut(flat)
    ss = cq.Workplane("YZ").circle(1.5).extrude(14).translate((0, 0, 2.5))
    return c.cut(ss)


# ---------------------------------------------------------------------------
# FIXED parts
# ---------------------------------------------------------------------------

def make_fixed_bowl(p: Params) -> cq.Workplane:
    """
    Stationary outer cylinder — reaction wall for the spiral / rim feed.
    Bottom rim has OUTLET WINDOWS (one per outlet_count) so screws can leave
    the bowl into outlet_ring / chute — required for feed + simulation.
    """
    shell = (
        cq.Workplane("XY")
        .circle(p.bowl_od / 2)
        .circle(p.bowl_id / 2)
        .extrude(p.bowl_h)
    )
    # Bottom flange to bolt to base
    flange = (
        cq.Workplane("XY")
        .circle(p.base_od / 2 - 4)
        .circle(p.bowl_id / 2)
        .extrude(4)
    )
    bowl = shell.union(flange)

    for i in range(6):
        a = math.radians(i * 60)
        hx = (p.base_od / 2 - 12) * math.cos(a)
        hy = (p.base_od / 2 - 12) * math.sin(a)
        bowl = bowl.cut(_cyl(p.mount_hole_d, 6).translate((hx, hy, -0.5)))

    # Fill window mid-height
    fill = (
        cq.Workplane("YZ")
        .circle(16)
        .extrude(20)
        .translate((p.bowl_od / 2 - 12, 0, p.bowl_h * 0.45))
    )
    bowl = bowl.cut(fill)

    # Rim outlet windows (disc/spiral exit) — aligned with outlet_ring angles
    # Window near bottom so parts at disc height can leave into chute.
    win_h = max(16.0, p.outlet_h + 4)
    win_w = p.outlet_w + 6
    win_depth = (p.bowl_od - p.bowl_id) / 2 + 8
    for a in p.outlet_angles_deg:
        rad = math.radians(a)
        cx = ((p.bowl_id + p.bowl_od) / 4) * math.cos(rad)
        cy = ((p.bowl_id + p.bowl_od) / 4) * math.sin(rad)
        # Bottom of window at z≈4 (above flange), height win_h
        cut = (
            cq.Workplane("XY")
            .transformed(offset=(cx, cy, 4 + win_h / 2), rotate=(0, 0, a))
            .box(win_depth + 10, win_w, win_h, centered=(True, True, True))
        )
        bowl = bowl.cut(cut)

    return bowl


def make_fixed_base(p: Params) -> cq.Workplane:
    """
    Machine deck interface + motor face mount (from below) + 626ZZ seat.
    Top: bowl flange bolts. Bottom: geared DC motor M3 face pattern.
    Sides: 4 frame feet with M5 slots.
    """
    base = cq.Workplane("XY").circle(p.base_od / 2).extrude(p.base_t)

    # Bowl seat ring on top
    ring = (
        cq.Workplane("XY")
        .circle(p.base_od / 2)
        .circle(p.base_od / 2 - 4)
        .extrude(3)
        .translate((0, 0, p.base_t))
    )
    base = base.union(ring)

    # Bearing pocket from TOP (626ZZ)
    seat_d = p.bearing_od + p.bearing_seat_clear
    base = base.cut(
        _cyl(seat_d, p.bearing_h + 0.3).translate((0, 0, p.base_t - p.bearing_h))
    )
    # Shaft clearance through base
    base = base.cut(_cyl(p.motor_shaft_d + 1.5, p.base_t + 4))

    # Motor face pilot recess on BOTTOM (negative Z)
    boss_recess = (
        _cyl(p.motor_boss_d + 0.6, 2.0)
        .translate((0, 0, -2.0))
    )
    base = base.cut(boss_recess)

    # 6x M3 motor mount holes (PCD 31 mm) — through base for screws from above
    # into gearbox (max ~3 mm thread engagement in gearbox)
    for i in range(p.motor_mount_n):
        a = math.radians(i * 360.0 / p.motor_mount_n + 30)  # flat-to-flat hex orientation
        hx = (p.motor_mount_pcd / 2) * math.cos(a)
        hy = (p.motor_mount_pcd / 2) * math.sin(a)
        base = base.cut(
            _cyl(p.motor_mount_hole_d, p.base_t + 6).translate((hx, hy, -3))
        )
        # Countersink / screwdriver access from top
        base = base.cut(
            _cyl(6.2, 2.2).translate((hx, hy, p.base_t - 2.0))
        )

    # Bowl flange bolt circle
    for i in range(6):
        a = math.radians(i * 60)
        hx = (p.base_od / 2 - 14) * math.cos(a)
        hy = (p.base_od / 2 - 14) * math.sin(a)
        base = base.cut(
            _cyl(p.mount_hole_d, p.base_t + 6).translate((hx, hy, -0.5))
        )

    # Four frame feet (machine chassis mount)
    foot_w, foot_l = 28.0, 36.0
    for a_deg in (45, 135, 225, 315):
        a = math.radians(a_deg)
        fx = (p.frame_span / 2) * math.cos(a)
        fy = (p.frame_span / 2) * math.sin(a)
        foot = (
            cq.Workplane("XY")
            .transformed(offset=(fx, fy, -p.frame_foot_t / 2), rotate=(0, 0, a_deg))
            .box(foot_l, foot_w, p.frame_foot_t, centered=(True, True, True))
        )
        base = base.union(foot)
        # M5 slot (radial) for alignment on machine plate
        slot = (
            cq.Workplane("XY")
            .transformed(offset=(fx, fy, -p.frame_foot_t - 0.1), rotate=(0, 0, a_deg))
            .slot2D(14, p.frame_hole_d)
            .extrude(p.frame_foot_t + p.base_t)
        )
        base = base.cut(slot)

    return base


def make_fixed_motor_clamp(p: Params) -> cq.Workplane:
    """
    Underside clamp ring — sandwiches motor face to base for stiffness.
    Optional if base alone is thick enough; recommended for PETG print.
    """
    t = 4.0
    clamp = (
        cq.Workplane("XY")
        .circle((p.motor_body_d + 16) / 2)
        .circle((p.motor_boss_d + 1) / 2)
        .extrude(t)
    )
    # Motor body clearance pocket
    clamp = clamp.cut(
        _cyl(p.motor_body_d + 0.8, 1.2).translate((0, 0, t - 1.2))
    )
    for i in range(p.motor_mount_n):
        a = math.radians(i * 360.0 / p.motor_mount_n + 30)
        hx = (p.motor_mount_pcd / 2) * math.cos(a)
        hy = (p.motor_mount_pcd / 2) * math.sin(a)
        clamp = clamp.cut(_cyl(p.motor_mount_hole_d, t + 1).translate((hx, hy, -0.5)))
    # Wire exit notch
    notch = (
        cq.Workplane("XY")
        .transformed(offset=(p.motor_body_d / 2 + 2, 0, t / 2))
        .box(12, 10, t + 1, centered=(True, True, True))
    )
    return clamp.cut(notch)


def make_fixed_frame_riser(p: Params) -> cq.Workplane:
    """
    Optional tall post — bolts feeder feet to a lower machine deck
    when motor body needs clearance below the plate.
    Print 4 pcs.
    """
    w, d, h = 24.0, 24.0, 40.0
    post = cq.Workplane("XY").box(w, d, h, centered=(True, True, False))
    # Through M5
    post = post.cut(_cyl(p.frame_hole_d, h + 2).translate((0, 0, -1)))
    # Side nut trap
    trap = (
        cq.Workplane("XY")
        .transformed(offset=(0, d / 2 - 3, h / 2))
        .box(10, 6, 10, centered=(True, True, True))
    )
    return post.cut(trap)


def make_ref_geared_motor(p: Params) -> cq.Workplane:
    """
    Non-printed reference solid for assembly / BOM preview.
    Shaft points +Z; gearbox face at z=0.
    """
    gb = _cyl(p.motor_body_d, p.motor_gearbox_l).translate((0, 0, -p.motor_gearbox_l))
    can = (
        _cyl(p.motor_body_d - 4, p.motor_can_l)
        .translate((0, 0, -p.motor_gearbox_l - p.motor_can_l))
    )
    boss = _cyl(p.motor_boss_d, 1.5)
    shaft = _cyl(p.motor_shaft_d, p.motor_shaft_l).translate((0, 0, 1.5))
    # D-flat on shaft
    flat = (
        cq.Workplane("XY")
        .center(p.motor_shaft_d / 2 + 0.5, 0)
        .rect(2.0, p.motor_shaft_flat)
        .extrude(p.motor_shaft_l)
        .translate((0, 0, 1.5))
    )
    motor = gb.union(can).union(boss).union(shaft).cut(flat)
    return motor


def make_fixed_outlet_ring(p: Params) -> cq.Workplane:
    """
    Top stationary ring: captures parts at spiral exit and splits to N outlets.
    """
    h = 18.0
    ring = (
        cq.Workplane("XY")
        .circle(p.bowl_od / 2 + 6)
        .circle(p.bowl_id / 2 - 4)
        .extrude(h)
    )
    # Inner ledge to catch parts leaving the flight
    ledge = (
        cq.Workplane("XY")
        .circle(p.bowl_id / 2 + 0.2)
        .circle(p.bowl_id / 2 - p.flight_w - 2)
        .extrude(3)
    )
    ring = ring.union(ledge)

    for a in p.outlet_angles_deg:
        rad = math.radians(a)
        # Radial exit tunnel
        tunnel = (
            cq.Workplane("XY")
            .transformed(rotate=(0, 0, a), offset=(0, 0, 4))
            .center(p.bowl_od / 4, 0)
            .box(p.bowl_od / 2 + 10, p.outlet_w, p.outlet_h, centered=(True, True, False))
        )
        ring = ring.cut(tunnel)

        # External chute boss
        bx = (p.bowl_od / 2 + p.outlet_depth / 2 - 2) * math.cos(rad)
        by = (p.bowl_od / 2 + p.outlet_depth / 2 - 2) * math.sin(rad)
        boss = (
            cq.Workplane("XY")
            .transformed(offset=(bx, by, h / 2), rotate=(0, 0, a))
            .box(p.outlet_depth, p.outlet_w + 10, h, centered=(True, True, True))
        )
        ring = ring.union(boss)
        chan = (
            cq.Workplane("XY")
            .transformed(offset=(bx, by, h / 2 + 1), rotate=(0, 0, a))
            .box(p.outlet_depth + 4, p.outlet_w, p.outlet_h, centered=(True, True, True))
        )
        ring = ring.cut(chan)

        # Sensor slot on boss
        sens = (
            cq.Workplane("XY")
            .transformed(
                offset=(
                    (p.bowl_od / 2 + p.outlet_depth * 0.55) * math.cos(rad),
                    (p.bowl_od / 2 + p.outlet_depth * 0.55) * math.sin(rad),
                    3,
                ),
                rotate=(0, 0, a),
            )
            .box(p.sensor_slot_w, p.outlet_w + 14, 12, centered=(True, True, False))
        )
        ring = ring.cut(sens)

    # Bolt to bowl top
    for i in range(6):
        a = math.radians(i * 60)
        hx = (p.bowl_od / 2 + 1) * math.cos(a)
        hy = (p.bowl_od / 2 + 1) * math.sin(a)
        ring = ring.cut(_cyl(p.mount_hole_d, h + 1).translate((hx, hy, -0.5)))

    return ring


def make_fixed_lid(p: Params) -> cq.Workplane:
    """Light lid — keeps parts from jumping out while filling."""
    lid = (
        cq.Workplane("XY")
        .circle(p.bowl_od / 2 + 4)
        .extrude(3)
    )
    lid = lid.cut(_cyl(50, 4))  # fill opening
    for i in range(6):
        a = math.radians(i * 60)
        hx = (p.bowl_od / 2 - 2) * math.cos(a)
        hy = (p.bowl_od / 2 - 2) * math.sin(a)
        lid = lid.cut(_cyl(p.mount_hole_d, 4).translate((hx, hy, -0.5)))
    return lid


# ---------------------------------------------------------------------------
# Assembly helpers
# ---------------------------------------------------------------------------

def moving_parts(p: Params) -> dict[str, cq.Workplane]:
    return {
        "rotor_spiral": make_moving_rotor(p),
        "drive_hub": make_moving_drive_hub(p),
        "shaft_collar": make_moving_shaft_collar(p),
    }


def fixed_parts(p: Params) -> dict[str, cq.Workplane]:
    return {
        "base": make_fixed_base(p),
        "motor_clamp": make_fixed_motor_clamp(p),
        "frame_riser": make_fixed_frame_riser(p),
        "bowl": make_fixed_bowl(p),
        "outlet_ring": make_fixed_outlet_ring(p),
        "lid": make_fixed_lid(p),
    }


def assembly(p: Params, rotor_angle_deg: float = 0.0, explode: float = 0.0) -> dict[str, cq.Workplane]:
    """
    Stack (z up), motor below base:
      motor face @ z=0 underside → shaft through bearing → hub → rotor
    """
    ez = explode * 28.0
    parts: dict[str, cq.Workplane] = {}

    # Purchased motor reference (below base)
    parts["ref_motor"] = make_ref_geared_motor(p).translate((0, 0, -ez * 0.8))

    parts["motor_clamp"] = make_fixed_motor_clamp(p).translate(
        (0, 0, -4.0 - ez * 0.5)
    )
    parts["base"] = make_fixed_base(p)

    # Collar under bearing (on shaft inside/near bottom)
    parts["shaft_collar"] = make_moving_shaft_collar(p).translate(
        (0, 0, 1.5 + ez * 0.15)
    )

    # Hub flange on top of bearing
    parts["drive_hub"] = make_moving_drive_hub(p).translate(
        (0, 0, p.base_t - 1.0 + ez * 0.25)
    )
    parts["rotor_spiral"] = (
        make_moving_rotor(p)
        .rotate((0, 0, 0), (0, 0, 1), rotor_angle_deg)
        .translate((0, 0, p.base_t + 2.0 + ez))
    )
    parts["bowl"] = make_fixed_bowl(p).translate((0, 0, p.base_t + ez * 0.5))
    parts["outlet_ring"] = make_fixed_outlet_ring(p).translate(
        (0, 0, p.base_t + p.bowl_h - 4 + ez * 1.4)
    )
    parts["lid"] = make_fixed_lid(p).translate(
        (0, 0, p.base_t + p.bowl_h + 14 + ez * 2.0)
    )

    # One riser shown at +X for clarity (print 4)
    parts["frame_riser"] = make_fixed_frame_riser(p).translate(
        (p.frame_span / 2 + 20, 0, -p.frame_foot_t - 40 - ez * 0.3)
    )
    return parts


def combine(parts: dict[str, cq.Workplane], skip_prefix: str = "") -> cq.Workplane:
    items = [s for n, s in parts.items() if not (skip_prefix and n.startswith(skip_prefix))]
    it = iter(items)
    asm = next(it)
    for s in it:
        asm = asm.union(s)
    return asm


def export_all(out_dir: Path, p: Params | None = None) -> Params:
    p = p or Params()
    out_dir = Path(out_dir)
    mov = out_dir / "stl_cq" / "moving"
    fix = out_dir / "stl_cq" / "fixed"
    ref = out_dir / "stl_cq" / "reference"
    step_m = out_dir / "step_cq" / "moving"
    step_f = out_dir / "step_cq" / "fixed"
    step_r = out_dir / "step_cq" / "reference"
    for d in (mov, fix, ref, step_m, step_f, step_r):
        d.mkdir(parents=True, exist_ok=True)

    print(
        f"motor={p.motor_name}  spiral turns={p.spiral_turns}  "
        f"outlets={p.outlet_count}"
    )

    for name, solid in moving_parts(p).items():
        print(f"  MOVING {name}")
        cq.exporters.export(solid, str(mov / f"{name}.stl"))
        cq.exporters.export(solid, str(step_m / f"{name}.step"))

    for name, solid in fixed_parts(p).items():
        print(f"  FIXED  {name}")
        cq.exporters.export(solid, str(fix / f"{name}.stl"))
        cq.exporters.export(solid, str(step_f / f"{name}.step"))

    motor = make_ref_geared_motor(p)
    print("  REF    geared_motor")
    cq.exporters.export(motor, str(ref / "geared_motor_GB37_24V.stl"))
    cq.exporters.export(motor, str(step_r / "geared_motor_GB37_24V.step"))

    # Printable assembly without ref motor mesh fused (keep motor separate)
    asm_parts = {k: v for k, v in assembly(p, 0, 0).items() if k != "ref_motor"}
    asm = combine(asm_parts)
    cq.exporters.export(asm, str(out_dir / "stl_cq" / "assembly_spiral_reference.stl"))
    cq.exporters.export(asm, str(out_dir / "step_cq" / "assembly_spiral_reference.step"))

    # Full visual with motor
    full = combine(assembly(p, 0, 0))
    cq.exporters.export(full, str(out_dir / "stl_cq" / "assembly_with_motor_preview.stl"))

    exp = combine(assembly(p, 25, 1.0))
    cq.exporters.export(exp, str(out_dir / "stl_cq" / "assembly_spiral_exploded.stl"))

    meta = {
        "mechanism": "rotary_archimedes_spiral",
        "drive": "continuous_rotation_only",
        "vibration": False,
        "motor": {
            "recommended": p.motor_name,
            "class": "GB37 / JGB37-520 (center shaft)",
            "voltage_v": p.motor_voltage_v,
            "speed_rpm": 30,
            "shaft_d_mm": p.motor_shaft_d,
            "shaft_type": "D-shaft CENTERED (reject eccentric)",
            "mount": f"{p.motor_mount_n}x M3 on PCD {p.motor_mount_pcd} mm",
            "bearing": "626ZZ 6x19x6 under hub",
            "note_screws": "M3 into gearbox face max 3 mm deep",
            "plc": p.plc_model,
            "plc_drive": (
                "Share 24VDC PSU with FX3U-24MT. Switch motor with relay "
                "(e.g. OMRON G2R) or MOSFET module from PLC Y transistor output — "
                "do not power motor directly from Y."
            ),
        },
        "moving_parts": list(moving_parts(p).keys()),
        "fixed_parts": list(fixed_parts(p).keys()),
        "bom_hardware": [
            f"1x GB37 {int(p.motor_voltage_v)}V ~30RPM center D-shaft 6mm",
            "1x 24VDC PSU (shared with FX3U-24MT)",
            "1x relay or MOSFET motor driver (PLC Y → coil/input)",
            "1x 626ZZ bearing",
            "6x M3x8 (motor to base, engage gearbox ≤3mm)",
            "1x M3 set screw (drive hub)",
            "1x M3 set screw (shaft collar)",
            "4x M5 bolt+nut (frame feet)",
            "6x M3 (bowl to base)",
        ],
        "revolute_joint": {
            "name": "rotor_z",
            "parts": ["rotor_spiral", "drive_hub", "shaft_collar"],
            "axis": [0, 0, 1],
            "origin_mm": [0, 0, p.base_t],
        },
        "frame_mount": {
            "pattern": "4 feet at 45/135/225/315 deg",
            "span_mm": p.frame_span,
            "hole": "M5 slot",
            "optional": "frame_riser x4 if deck needs motor clearance",
        },
        "print_clearance_flight_to_bowl_mm": p.flight_clearance,
        "outlet_count": p.outlet_count,
        "outlet_angles_deg": p.outlet_angles_deg,
    }
    (out_dir / "sim_joints_spiral_cq.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    print("done")
    return p


if __name__ == "__main__":
    export_all(Path(__file__).resolve().parent, Params())
