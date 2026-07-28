"""
Rotary bowl with FIXED spiral inclined tracks (mang doc) — CadQuery SoT

Track geometry reference (visible spiral ramp on bowl wall):
  https://www.youtube.com/shorts/ioa9o-LLHCA  (RNA bowl feeder for springs)
  https://www.youtube.com/shorts/oszvi08exHI  (EcoType orientation / reject)

Drive: ROTARY disc only — NOT vibratory (unlike the RNA spring video drive).
  https://www.youtube.com/shorts/jGgILsgO2yY

Moving: conical_disc + drive paddles + drive_hub
Fixed:  bowl + spiral_track (máng xoắn dốc), rim_rail_gate, outlet_chute, base, lid, motor_clamp
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import math

import cadquery as cq


@dataclass
class Params:
    bowl_id: float = 140.0
    bowl_od: float = 154.0
    bowl_h: float = 85.0

    disc_od: float = 118.0
    disc_cone_h: float = 14.0
    disc_hub_d: float = 36.0
    disc_key_d: float = 28.0
    n_paddles: int = 4

    # Fixed spiral inclined track (máng dốc) — RNA-style wall track
    n_tracks: int = 1  # classic bowl: one main spiral ramp
    spiral_turns: float = 2.5
    spiral_start_z: float = 4.0
    spiral_end_z: float = 68.0
    track_w: float = 14.0  # radial width of trough floor
    track_t: float = 2.8  # floor thickness
    track_wall_h: float = 8.0  # upright lip of trough
    track_clearance: float = 0.8  # from bowl ID

    rail_w: float = 9.0
    rail_h: float = 8.0
    gate_slot_w: float = 7.0
    reject_gap: float = 12.0
    chute_len: float = 95.0
    sensor_slot_w: float = 8.0
    outlet_count: int = 1

    motor_shaft_d: float = 6.0
    motor_shaft_flat: float = 5.4
    motor_mount_pcd: float = 31.0
    motor_mount_n: int = 6
    motor_boss_d: float = 12.0
    bearing_od: float = 19.0
    bearing_h: float = 6.0
    base_od: float = 175.0
    base_t: float = 10.0
    mount_hole_d: float = 3.4
    frame_span: float = 140.0
    frame_hole_d: float = 5.5

    @property
    def shaft_bore(self) -> float:
        return self.motor_shaft_d + 0.25

    @property
    def track_r(self) -> float:
        return self.bowl_id / 2 - self.track_clearance - self.track_w / 2

    @property
    def spiral_pitch(self) -> float:
        return (self.spiral_end_z - self.spiral_start_z) / self.spiral_turns

    @property
    def outlet_angles_deg(self) -> list[float]:
        if self.outlet_count <= 1:
            return [0.0]
        return [i * 360.0 / self.outlet_count for i in range(self.outlet_count)]

    @property
    def exit_z(self) -> float:
        return self.spiral_end_z


def _cyl(d: float, h: float) -> cq.Workplane:
    return cq.Workplane("XY").circle(d / 2).extrude(h)


def make_spiral_track_segment(p: Params, start_angle_deg: float = 0.0) -> cq.Workplane:
    """
    One continuous helical trough (máng dốc): wide floor + outer lip.
    Fixed to bowl — parts climb this ramp (RNA spring-bowl style track).
    """
    wire = cq.Wire.makeHelix(
        pitch=p.spiral_pitch,
        height=p.spiral_end_z - p.spiral_start_z,
        radius=p.track_r,
        center=cq.Vector(0, 0, p.spiral_start_z),
        dir=cq.Vector(0, 0, 1),
        lefthand=False,
    )
    if start_angle_deg:
        wire = wire.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), start_angle_deg)

    ang0 = math.radians(start_angle_deg)
    x0 = p.track_r * math.cos(ang0)
    y0 = p.track_r * math.sin(ang0)
    # U-channel profile: floor + outer wall (open toward bowl center for reject fall-in)
    hw = p.track_w / 2
    profile = (
        cq.Workplane("XY")
        .transformed(offset=(x0, y0, p.spiral_start_z), rotate=(0, 0, start_angle_deg))
        .moveTo(-hw, 0)
        .lineTo(hw, 0)
        .lineTo(hw, p.track_t)
        .lineTo(hw - 2.2, p.track_t)
        .lineTo(hw - 2.2, p.track_t + p.track_wall_h)
        .lineTo(hw, p.track_t + p.track_wall_h)
        .lineTo(hw, p.track_t + p.track_wall_h + p.track_t)
        .lineTo(-hw + 1.5, p.track_t + p.track_wall_h + p.track_t)
        .lineTo(-hw + 1.5, p.track_t)
        .lineTo(-hw, p.track_t)
        .close()
    )
    return profile.sweep(wire, isFrenet=True)


def make_spiral_track(p: Params) -> cq.Workplane:
    track = None
    for i in range(p.n_tracks):
        ang = i * (360.0 / max(p.n_tracks, 1))
        seg = make_spiral_track_segment(p, start_angle_deg=ang)
        track = seg if track is None else track.union(seg)
    return track


def make_conical_disc(p: Params) -> cq.Workplane:
    """Rotating floor + radial paddles — pushes screws onto fixed spiral track."""
    r_out = min(p.disc_od / 2, p.bowl_id / 2 - p.track_w - 4)
    cone = (
        cq.Workplane("XZ")
        .moveTo(p.disc_key_d / 2, 0)
        .lineTo(r_out, 0)
        .lineTo(p.disc_hub_d / 2, p.disc_cone_h)
        .lineTo(p.disc_key_d / 2, p.disc_cone_h)
        .close()
        .revolve(360)
    )
    boss = _cyl(p.disc_hub_d, p.disc_cone_h + 8)
    disc = cone.union(boss)
    disc = disc.cut(_cyl(p.disc_key_d - 0.4, p.disc_cone_h + 10))
    for a in (0, 90, 180, 270):
        slot = (
            cq.Workplane("XY")
            .transformed(rotate=(0, 0, a))
            .center(p.disc_key_d / 2 - 1, 0)
            .rect(4, 6)
            .extrude(p.disc_cone_h + 10)
        )
        disc = disc.cut(slot)
    # Drive paddles (sweep parts toward track entrance)
    for i in range(p.n_paddles):
        a = i * (360.0 / p.n_paddles)
        paddle = (
            cq.Workplane("XY")
            .transformed(rotate=(0, 0, a), offset=(0, 0, 1))
            .center((p.disc_key_d + p.disc_od) / 4, 0)
            .box((p.disc_od - p.disc_key_d) / 2 - 8, 3.5, 10, centered=(True, True, False))
        )
        disc = disc.union(paddle)
    return disc


def make_drive_hub(p: Params) -> cq.Workplane:
    h = p.disc_cone_h + 12
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
            .extrude(p.disc_cone_h)
        )
        hub = hub.union(tab)
    hub = hub.cut(_cyl(p.shaft_bore, h + 1))
    flat = (
        cq.Workplane("XY")
        .center(p.motor_shaft_d / 2 - (p.motor_shaft_d - p.motor_shaft_flat) + 1.2, 0)
        .rect(3.2, p.motor_shaft_flat + 0.3)
        .extrude(h + 1)
    )
    hub = hub.cut(flat)
    ss = cq.Workplane("YZ").circle(1.5).extrude(p.disc_key_d).translate((0, 0, 8))
    return hub.cut(ss)


def make_base(p: Params) -> cq.Workplane:
    base = cq.Workplane("XY").circle(p.base_od / 2).extrude(p.base_t)
    seat = p.bearing_od + 0.3
    base = base.cut(_cyl(seat, p.bearing_h + 0.3).translate((0, 0, p.base_t - p.bearing_h)))
    base = base.cut(_cyl(p.motor_shaft_d + 1.5, p.base_t + 4))
    base = base.cut(_cyl(p.motor_boss_d + 0.6, 2).translate((0, 0, -2)))
    for i in range(p.motor_mount_n):
        a = math.radians(i * 60 + 30)
        hx = (p.motor_mount_pcd / 2) * math.cos(a)
        hy = (p.motor_mount_pcd / 2) * math.sin(a)
        base = base.cut(_cyl(3.2, p.base_t + 6).translate((hx, hy, -3)))
        base = base.cut(_cyl(6.2, 2.2).translate((hx, hy, p.base_t - 2)))
    for i in range(6):
        a = math.radians(i * 60)
        hx = (p.base_od / 2 - 14) * math.cos(a)
        hy = (p.base_od / 2 - 14) * math.sin(a)
        base = base.cut(_cyl(p.mount_hole_d, p.base_t + 4).translate((hx, hy, -0.5)))
    for a_deg in (45, 135, 225, 315):
        a = math.radians(a_deg)
        fx = (p.frame_span / 2) * math.cos(a)
        fy = (p.frame_span / 2) * math.sin(a)
        foot = (
            cq.Workplane("XY")
            .transformed(offset=(fx, fy, -4), rotate=(0, 0, a_deg))
            .box(34, 26, 8, centered=(True, True, True))
        )
        base = base.union(foot)
        slot = (
            cq.Workplane("XY")
            .transformed(offset=(fx, fy, -8.1), rotate=(0, 0, a_deg))
            .slot2D(14, p.frame_hole_d)
            .extrude(p.base_t + 10)
        )
        base = base.cut(slot)
    return base


def make_bowl(p: Params) -> cq.Workplane:
    shell = (
        cq.Workplane("XY")
        .circle(p.bowl_od / 2)
        .circle(p.bowl_id / 2)
        .extrude(p.bowl_h)
    )
    flange = (
        cq.Workplane("XY")
        .circle(p.base_od / 2 - 6)
        .circle(p.bowl_id / 2)
        .extrude(4)
    )
    bowl = shell.union(flange)
    win_h, win_w = 22.0, p.rail_w + 12
    z_win = p.exit_z - 5
    for a in p.outlet_angles_deg:
        rad = math.radians(a)
        cx = ((p.bowl_id + p.bowl_od) / 4) * math.cos(rad)
        cy = ((p.bowl_id + p.bowl_od) / 4) * math.sin(rad)
        cut = (
            cq.Workplane("XY")
            .transformed(offset=(cx, cy, z_win + win_h / 2), rotate=(0, 0, a))
            .box((p.bowl_od - p.bowl_id) / 2 + 14, win_w, win_h, centered=(True, True, True))
        )
        bowl = bowl.cut(cut)
    for i in range(6):
        a = math.radians(i * 60)
        hx = (p.base_od / 2 - 14) * math.cos(a)
        hy = (p.base_od / 2 - 14) * math.sin(a)
        bowl = bowl.cut(_cyl(p.mount_hole_d, 6).translate((hx, hy, -0.5)))
    return bowl


def make_rim_rail_and_gate(p: Params) -> cq.Workplane:
    z0 = p.exit_z - 2.0
    ledge = (
        cq.Workplane("XY")
        .circle(p.bowl_id / 2 - 0.5)
        .circle(p.bowl_id / 2 - p.rail_w - 3)
        .extrude(2.5)
        .translate((0, 0, z0))
    )
    for a in p.outlet_angles_deg:
        rad = math.radians(a + 25)
        cx = (p.bowl_id / 2 - p.rail_w / 2 - 1) * math.cos(rad)
        cy = (p.bowl_id / 2 - p.rail_w / 2 - 1) * math.sin(rad)
        cut = (
            cq.Workplane("XY")
            .transformed(offset=(cx, cy, z0 + 1.25), rotate=(0, 0, a + 25))
            .box(p.rail_w + 6, p.reject_gap + 10, 5, centered=(True, True, True))
        )
        ledge = ledge.cut(cut)
    gate = None
    for a in p.outlet_angles_deg:
        for yoff in (-p.gate_slot_w / 2 - 1.2, p.gate_slot_w / 2 + 1.2):
            post = (
                cq.Workplane("XY")
                .transformed(
                    offset=((p.bowl_id / 2 - 4), 0, z0 + p.rail_h / 2),
                    rotate=(0, 0, a),
                )
                .center(0, yoff)
                .box(12, 2.4, p.rail_h, centered=(True, True, True))
            )
            gate = post if gate is None else gate.union(post)
    return ledge.union(gate) if gate is not None else ledge


def make_outlet_chute(p: Params) -> cq.Workplane:
    body = cq.Workplane("XY").box(p.chute_len, p.rail_w + 10, 14, centered=(False, True, False))
    channel = (
        cq.Workplane("XY")
        .transformed(offset=(2, 0, 3))
        .box(p.chute_len, p.rail_w, 10, centered=(False, True, False))
    )
    body = body.cut(channel)
    sens = (
        cq.Workplane("XY")
        .transformed(offset=(p.chute_len * 0.45, 0, 2))
        .box(p.sensor_slot_w, p.rail_w + 14, 10, centered=(True, True, False))
    )
    body = body.cut(sens)
    for y in (-(p.rail_w + 6) / 2, (p.rail_w + 6) / 2):
        body = body.cut(_cyl(3.2, 16).translate((12, y, -1)))
    return body


def make_lid(p: Params) -> cq.Workplane:
    lid = cq.Workplane("XY").circle(p.bowl_od / 2 + 3).extrude(3)
    lid = lid.cut(_cyl(55, 4))
    for i in range(6):
        a = math.radians(i * 60)
        hx = (p.bowl_od / 2 - 2) * math.cos(a)
        hy = (p.bowl_od / 2 - 2) * math.sin(a)
        lid = lid.cut(_cyl(p.mount_hole_d, 4).translate((hx, hy, -0.5)))
    return lid


def make_motor_clamp(p: Params) -> cq.Workplane:
    t = 4.0
    clamp = (
        cq.Workplane("XY")
        .circle((37 + 16) / 2)
        .circle((p.motor_boss_d + 1) / 2)
        .extrude(t)
    )
    for i in range(6):
        a = math.radians(i * 60 + 30)
        hx = (p.motor_mount_pcd / 2) * math.cos(a)
        hy = (p.motor_mount_pcd / 2) * math.sin(a)
        clamp = clamp.cut(_cyl(3.2, t + 1).translate((hx, hy, -0.5)))
    return clamp


def moving_parts(p: Params) -> dict[str, cq.Workplane]:
    return {"conical_disc": make_conical_disc(p), "drive_hub": make_drive_hub(p)}


def fixed_parts(p: Params) -> dict[str, cq.Workplane]:
    return {
        "base": make_base(p),
        "bowl": make_bowl(p),
        "spiral_track": make_spiral_track(p),  # máng xoắn dốc — visible like RNA bowl
        "rim_rail_gate": make_rim_rail_and_gate(p),
        "outlet_chute": make_outlet_chute(p),
        "lid": make_lid(p),
        "motor_clamp": make_motor_clamp(p),
    }


def export_all(out_dir: Path, p: Params | None = None) -> Params:
    p = p or Params()
    out_dir = Path(out_dir)
    mov, fix = out_dir / "stl_cq" / "moving", out_dir / "stl_cq" / "fixed"
    sm, sf = out_dir / "step_cq" / "moving", out_dir / "step_cq" / "fixed"
    for d in (mov, fix, sm, sf):
        d.mkdir(parents=True, exist_ok=True)

    print(
        f"Export RNA-style spiral track bowl (rotary drive)  "
        f"turns={p.spiral_turns} exit_z={p.exit_z}mm track_w={p.track_w}mm"
    )
    for name, solid in moving_parts(p).items():
        print(" MOVING", name)
        cq.exporters.export(solid, str(mov / f"{name}.stl"))
        cq.exporters.export(solid, str(sm / f"{name}.step"))
    for name, solid in fixed_parts(p).items():
        print(" FIXED ", name)
        cq.exporters.export(solid, str(fix / f"{name}.stl"))
        cq.exporters.export(solid, str(sf / f"{name}.step"))

    meta = {
        "mechanism": "fixed_spiral_inclined_track_rotary_disc",
        "vibration": False,
        "track_geometry_ref": "https://www.youtube.com/shorts/ioa9o-LLHCA",
        "behavior_ref": "https://www.youtube.com/shorts/oszvi08exHI",
        "drive_ref": "https://www.youtube.com/shorts/jGgILsgO2yY",
        "lift": "fixed_helical_trough_on_bowl_wall",
        "reject": "wrong_pose_falls_inward_off_track_back_to_disc",
        "exit_z_mm": p.exit_z,
        "spiral_turns": p.spiral_turns,
        "track_w_mm": p.track_w,
        "moving_parts": list(moving_parts(p).keys()),
        "fixed_parts": list(fixed_parts(p).keys()),
        "acceptance": [
            "visible inclined spiral trough (mang doc) on bowl wall",
            "screws climb track to elevated rim",
            "correct pose slides out chute tip",
            "wrong pose falls back onto disc",
        ],
    }
    (out_dir / "sim_joints_centrifugal_cq.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    print("done")
    return p


if __name__ == "__main__":
    export_all(Path(__file__).resolve().parent, Params())
