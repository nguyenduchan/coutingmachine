"""
Multi-outlet rotary screw feeder — CountingMachine
CadQuery parametric model for Bambu Lab P1S + motion simulation.

Design intent (ref: vibratory multi-track feeders / multi-outlet screw feeders):
  - Bowl-style hopper inspired by commercial vibratory bowl feeders
  - Rotary indexing disc with pockets
  - N synchronized outlets (default 4) so each index step releases N screws
  - Throughput ≈ outlet_count × (rpm × pocket_count / 60) / (pocket_count/outlet_count)
    With pocket_count % outlet_count == 0, every step feeds all outlets in parallel.

Motion joints for simulation:
  - revolute Z: drive_hub + rotary_disc
  - fixed: base, bowl, cover, outlet_chutes[], sensor_brackets[]
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math

import cadquery as cq


@dataclass
class Params:
    # Screw envelope (M3–M4 class; adjust for real fastener)
    screw_head_d: float = 6.5
    screw_head_h: float = 2.5
    screw_shank_d: float = 3.2
    screw_shank_l: float = 12.0
    pocket_clearance: float = 0.6

    # Multi-outlet (key for counting speed)
    outlet_count: int = 4  # 2, 3, 4, or 6 typical
    pocket_count: int = 12  # must be multiple of outlet_count

    # Disc
    disc_od: float = 140.0
    disc_id: float = 28.0
    disc_thickness: float = 6.0
    pocket_radial: float = 52.0

    # Base / bowl (bowl aesthetic like industrial vibratory feeders)
    base_od: float = 168.0
    base_thickness: float = 8.0
    bowl_od_top: float = 150.0
    bowl_od_bot: float = 118.0
    bowl_h: float = 70.0
    bowl_wall: float = 2.8
    cover_h: float = 10.0

    # Outlets
    outlet_w: float = 10.0
    outlet_depth: float = 32.0
    outlet_tube_len: float = 18.0
    sensor_slot_w: float = 8.0
    sensor_slot_h: float = 12.0

    # Drive
    shaft_d: float = 5.2
    hub_flat: float = 5.0
    bearing_bore: float = 16.2
    mount_hole_d: float = 3.4

    # Print / mesh
    fn: int = 96

    def __post_init__(self) -> None:
        if self.outlet_count < 2:
            raise ValueError("outlet_count must be >= 2 for multi-outlet counting")
        if self.pocket_count % self.outlet_count != 0:
            raise ValueError(
                f"pocket_count ({self.pocket_count}) must be multiple of "
                f"outlet_count ({self.outlet_count}) so outlets fire together"
            )

    @property
    def pocket_w(self) -> float:
        return self.screw_head_d + 2 * self.pocket_clearance

    @property
    def pocket_l(self) -> float:
        return self.screw_head_d + self.screw_shank_l * 0.35 + self.pocket_clearance

    @property
    def index_angle_deg(self) -> float:
        return 360.0 / self.pocket_count

    @property
    def outlet_angles_deg(self) -> list[float]:
        return [i * 360.0 / self.outlet_count for i in range(self.outlet_count)]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cyl(d: float, h: float) -> cq.Workplane:
    return cq.Workplane("XY").circle(d / 2).extrude(h)


def _bolt_circle(wp: cq.Workplane, pcd: float, n: int, d: float) -> cq.Workplane:
    pts = [
        (math.cos(math.radians(i * 360 / n)) * pcd / 2,
         math.sin(math.radians(i * 360 / n)) * pcd / 2)
        for i in range(n)
    ]
    return wp.pushPoints(pts).hole(d)


# ---------------------------------------------------------------------------
# Parts
# ---------------------------------------------------------------------------

def make_rotary_disc(p: Params) -> cq.Workplane:
    disc = (
        cq.Workplane("XY")
        .circle(p.disc_od / 2)
        .extrude(p.disc_thickness)
        .faces(">Z").workplane()
        .circle(p.disc_id / 2)
        .cutThruAll()
    )

    # Key slots for drive hub (4 tabs)
    for a in (0, 90, 180, 270):
        slot = (
            cq.Workplane("XY")
            .transformed(rotate=(0, 0, a))
            .center(p.disc_id / 2 - 1, 0)
            .rect(4, 6)
            .extrude(p.disc_thickness + 0.2)
        )
        disc = disc.cut(slot)

    # Pockets — elongated slot (head clearance) oriented tangentially
    pw, pl = p.pocket_w, p.pocket_l
    shank_d = p.screw_shank_d + 2 * p.pocket_clearance
    for i in range(p.pocket_count):
        a = i * 360.0 / p.pocket_count
        # Main pocket slot (length along radial tangent)
        pocket = (
            cq.Workplane("XY")
            .transformed(
                offset=(
                    p.pocket_radial * math.cos(math.radians(a)),
                    p.pocket_radial * math.sin(math.radians(a)),
                    -0.05,
                ),
                rotate=(0, 0, a + 90),
            )
            .slot2D(pl, pw)
            .extrude(p.disc_thickness + 0.2)
        )
        # Narrow through-cut so shank can drop at outlet window
        slot = (
            cq.Workplane("XY")
            .transformed(
                offset=(
                    p.pocket_radial * math.cos(math.radians(a)),
                    p.pocket_radial * math.sin(math.radians(a)),
                    -0.05,
                ),
                rotate=(0, 0, a + 90),
            )
            .slot2D(pl * 1.05, shank_d)
            .extrude(p.disc_thickness + 0.2)
        )
        disc = disc.cut(pocket).cut(slot)

    # Lightening holes
    for i in range(12):
        a = 15 + i * 30
        hx = 36 * math.cos(math.radians(a))
        hy = 36 * math.sin(math.radians(a))
        disc = disc.faces(">Z").workplane().center(hx, hy).hole(8)

    # Stiffening ribs on top
    ribs = cq.Workplane("XY")
    for a in range(0, 360, 60):
        rib = (
            cq.Workplane("XY")
            .transformed(rotate=(0, 0, a))
            .center((p.disc_id + p.disc_od) / 4, 0)
            .rect((p.disc_od - p.disc_id) / 2 - 4, 2.4)
            .extrude(1.2)
            .translate((0, 0, p.disc_thickness))
        )
        disc = disc.union(rib)

    return disc


def make_drive_hub(p: Params) -> cq.Workplane:
    h = p.disc_thickness + 12
    hub = (
        cq.Workplane("XY")
        .circle((p.disc_id + 10) / 2)
        .extrude(3)
        .faces(">Z").workplane()
        .circle((p.disc_id - 0.4) / 2)
        .extrude(h - 3)
    )
    for a in (0, 90, 180, 270):
        tab = (
            cq.Workplane("XY")
            .transformed(rotate=(0, 0, a), offset=(0, 0, 3))
            .center(p.disc_id / 2 - 1.2, 0)
            .rect(3.6, 5.6)
            .extrude(p.disc_thickness)
        )
        hub = hub.union(tab)

    # Shaft bore + D-flat for NEMA17
    hub = hub.cut(_cyl(p.shaft_d, h + 1))
    flat = (
        cq.Workplane("XY")
        .center(p.shaft_d / 2 + 0.8, 0)
        .rect(3.5, p.hub_flat)
        .extrude(h + 1)
    )
    hub = hub.cut(flat)

    # M3 set-screw along +X at z = h-5
    ss = (
        cq.Workplane("YZ")
        .circle(1.4)
        .extrude(p.disc_id)
        .translate((0, 0, h - 5))
    )
    hub = hub.cut(ss)
    return hub


def make_base_plate(p: Params) -> cq.Workplane:
    base = (
        cq.Workplane("XY")
        .circle(p.base_od / 2)
        .extrude(p.base_thickness)
    )
    # Wall seat ring
    ring = (
        cq.Workplane("XY")
        .circle(p.base_od / 2)
        .circle(p.base_od / 2 - 3.5)
        .extrude(4)
        .translate((0, 0, p.base_thickness))
    )
    base = base.union(ring)

    # Center bearing bore
    base = base.faces(">Z").workplane().hole(p.bearing_bore)

    # Drop windows + outlet bosses at each outlet angle
    for a in p.outlet_angles_deg:
        rad = math.radians(a)
        cx = p.pocket_radial * math.cos(rad)
        cy = p.pocket_radial * math.sin(rad)
        # Drop window under pocket
        win = (
            cq.Workplane("XY")
            .transformed(offset=(cx, cy, -0.05), rotate=(0, 0, a))
            .slot2D(p.pocket_w + 10, p.pocket_w + 1)
            .extrude(p.base_thickness + 4.2)
        )
        base = base.cut(win)

        # Outlet boss on rim
        bx = (p.base_od / 2 - p.outlet_depth / 2 - 2) * math.cos(rad)
        by = (p.base_od / 2 - p.outlet_depth / 2 - 2) * math.sin(rad)
        boss = (
            cq.Workplane("XY")
            .transformed(offset=(bx, by, p.base_thickness / 2), rotate=(0, 0, a))
            .box(p.outlet_depth, p.outlet_w + 8, p.base_thickness, centered=(True, True, True))
        )
        base = base.union(boss)
        # Channel through boss toward rim
        chan = (
            cq.Workplane("XY")
            .transformed(offset=(bx, by, p.base_thickness / 2), rotate=(0, 0, a))
            .box(p.outlet_depth + 6, p.outlet_w, p.base_thickness + 2, centered=(True, True, True))
        )
        base = base.cut(chan)

    # Mount holes (feet / motor plate)
    for a in (45, 135, 225, 315):
        hx = (p.base_od / 2 - 10) * math.cos(math.radians(a))
        hy = (p.base_od / 2 - 10) * math.sin(math.radians(a))
        base = base.faces(">Z").workplane().center(hx, hy).hole(p.mount_hole_d)

    # Bowl / cover bolt circle
    for i in range(6):
        a = i * 60
        hx = (p.base_od - 14) / 2 * math.cos(math.radians(a))
        hy = (p.base_od - 14) / 2 * math.sin(math.radians(a))
        base = base.faces(">Z").workplane().center(hx, hy).hole(p.mount_hole_d)

    return base


def make_bowl(p: Params) -> cq.Workplane:
    """Bowl-style hopper (form factor similar to vibratory bowl feeders)."""
    shell = (
        cq.Workplane("XZ")
        .moveTo(p.bowl_od_bot / 2, 0)
        .lineTo(p.bowl_od_top / 2, p.bowl_h)
        .lineTo(p.bowl_od_top / 2 - p.bowl_wall, p.bowl_h)
        .lineTo(p.bowl_od_bot / 2 - p.bowl_wall, 0)
        .close()
        .revolve(360)
    )
    flange = (
        cq.Workplane("XY")
        .circle((p.bowl_od_bot + 16) / 2)
        .circle(p.bowl_od_bot / 2 - p.bowl_wall)
        .extrude(4)
    )
    bowl = shell.union(flange)

    # Open bottom onto disc
    bowl = bowl.cut(cq.Workplane("XY").circle((p.disc_od - 8) / 2).extrude(8))

    # Flange bolt holes
    for i in range(6):
        a = math.radians(i * 60)
        hx = (p.bowl_od_bot + 8) / 2 * math.cos(a)
        hy = (p.bowl_od_bot + 8) / 2 * math.sin(a)
        hole = _cyl(p.mount_hole_d, 6).translate((hx, hy, -0.5))
        bowl = bowl.cut(hole)

    # Side fill window (+X)
    fill = (
        cq.Workplane("YZ")
        .circle(14)
        .extrude(30)
        .translate((p.bowl_od_top / 2 - 20, 0, p.bowl_h - 22))
    )
    bowl = bowl.cut(fill)
    return bowl


def make_cover(p: Params) -> cq.Workplane:
    cover = (
        cq.Workplane("XY")
        .circle((p.disc_od + 8) / 2)
        .circle((p.disc_od - 12) / 2)
        .extrude(p.cover_h)
    )
    # Open sectors above each outlet so screws can drop freely
    for a in p.outlet_angles_deg:
        rad = math.radians(a)
        cx = p.pocket_radial * math.cos(rad)
        cy = p.pocket_radial * math.sin(rad)
        cut = (
            cq.Workplane("XY")
            .transformed(offset=(cx, cy, -0.05), rotate=(0, 0, a))
            .box(42, p.outlet_w + 8, p.cover_h + 0.2, centered=(True, True, False))
        )
        cover = cover.cut(cut)

    # Bolt holes matching base
    for i in range(6):
        a = i * 60
        hx = (p.base_od - 14) / 2 * math.cos(math.radians(a))
        hy = (p.base_od - 14) / 2 * math.sin(math.radians(a))
        # only if hole is in material ring
        r = math.hypot(hx, hy)
        if (p.disc_od - 12) / 2 < r < (p.disc_od + 8) / 2:
            cover = cover.faces(">Z").workplane().center(hx, hy).hole(p.mount_hole_d)

    return cover


def make_outlet_chute(p: Params) -> cq.Workplane:
    """Single printable chute with optical-sensor slot for counting."""
    body = (
        cq.Workplane("XY")
        .box(p.outlet_depth + 6, p.outlet_w + 12, 18, centered=(False, False, False))
    )
    channel = (
        cq.Workplane("XY")
        .transformed(offset=(3, 6, 4))
        .box(p.outlet_depth + 22, p.outlet_w, 12, centered=(False, False, False))
    )
    body = body.cut(channel)

    tube_od = p.outlet_w + 6
    tube = (
        cq.Workplane("YZ")
        .circle(tube_od / 2)
        .extrude(p.outlet_tube_len)
        .translate((p.outlet_depth + 2, (p.outlet_w + 12) / 2, 9))
    )
    tube_bore = (
        cq.Workplane("YZ")
        .circle(p.outlet_w / 2)
        .extrude(p.outlet_tube_len + 2)
        .translate((p.outlet_depth + 2, (p.outlet_w + 12) / 2, 9))
    )
    body = body.union(tube).cut(tube_bore)

    # Sensor slot (fork opto / IR) across channel
    sensor = (
        cq.Workplane("XY")
        .transformed(offset=(p.outlet_depth * 0.55 - p.sensor_slot_w / 2, -0.5, 3))
        .box(p.sensor_slot_w, p.outlet_w + 14, p.sensor_slot_h, centered=(False, False, False))
    )
    body = body.cut(sensor)

    for y in (3.0, p.outlet_w + 9.0):
        body = body.cut(_cyl(3.2, 20).translate((8, y, -0.5)))
    return body


def make_brush_arm(p: Params) -> cq.Workplane:
    arm = (
        cq.Workplane("XY")
        .box(28, 10, 6, centered=(False, False, False))
        .union(
            cq.Workplane("XY")
            .transformed(offset=(0, 3, 6))
            .box(28, 4, 8, centered=(False, False, False))
        )
    )
    slot = (
        cq.Workplane("XY")
        .transformed(offset=(2, 3.5, 8))
        .box(24, 3, 7, centered=(False, False, False))
    )
    arm = arm.cut(slot)
    for x in (6.0, 22.0):
        arm = arm.cut(_cyl(3.2, 8).translate((x, 5, -0.5)))
    return arm


def place_outlet_chute(chute: cq.Workplane, p: Params, angle_deg: float) -> cq.Workplane:
    """Place chute on rim at outlet angle (local +X chute → world radial out)."""
    # Chute local: extends +X from origin of its bbox corner design
    # Position so entry sits at base rim, channel radial outward
    r = p.base_od / 2 - p.outlet_depth - 4
    rad = math.radians(angle_deg)
    # Local origin of chute is corner; shift to centerline
    y_off = -(p.outlet_w + 12) / 2
    placed = (
        chute
        .translate((r, y_off, -2))
        .rotate((0, 0, 0), (0, 0, 1), angle_deg)
    )
    return placed


def make_assembly(
    p: Params,
    disc_angle_deg: float = 0.0,
    explode: float = 0.0,
    include_chutes: bool = True,
) -> dict[str, cq.Workplane]:
    ez = explode * 30.0
    parts: dict[str, cq.Workplane] = {}

    parts["base_plate"] = make_base_plate(p)
    parts["drive_hub"] = make_drive_hub(p).translate((0, 0, p.base_thickness - 2 - ez * 0.3))
    parts["rotary_disc"] = (
        make_rotary_disc(p)
        .rotate((0, 0, 0), (0, 0, 1), disc_angle_deg)
        .translate((0, 0, p.base_thickness + 0.5 + ez))
    )
    parts["cover"] = make_cover(p).translate((0, 0, p.base_thickness + p.disc_thickness + 0.2 + ez))
    parts["bowl"] = make_bowl(p).translate((0, 0, p.base_thickness + p.disc_thickness + 1 + ez * 1.5))

    if include_chutes:
        chute = make_outlet_chute(p)
        for i, a in enumerate(p.outlet_angles_deg):
            parts[f"outlet_chute_{i}"] = place_outlet_chute(chute, p, a).translate(
                (0, 0, -ez * 0.5)
            )

    # One brush between outlets
    brush_a = p.outlet_angles_deg[0] + (180.0 / p.outlet_count)
    brush = (
        make_brush_arm(p)
        .translate((p.disc_od / 2 - 20, -5, p.base_thickness + p.disc_thickness + 8 + ez))
        .rotate((0, 0, 0), (0, 0, 1), brush_a)
    )
    parts["brush_arm"] = brush
    return parts


def combine_parts(parts: dict[str, cq.Workplane]) -> cq.Workplane:
    it = iter(parts.values())
    asm = next(it)
    for solid in it:
        asm = asm.union(solid)
    return asm


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_all(out_dir: Path, p: Params | None = None) -> Params:
    p = p or Params()
    out_dir = Path(out_dir)
    stl_dir = out_dir / "stl_cq"
    step_dir = out_dir / "step_cq"
    stl_dir.mkdir(parents=True, exist_ok=True)
    step_dir.mkdir(parents=True, exist_ok=True)

    builders = {
        "base_plate": make_base_plate,
        "rotary_disc": make_rotary_disc,
        "drive_hub": make_drive_hub,
        "bowl": make_bowl,
        "cover": make_cover,
        "outlet_chute": make_outlet_chute,
        "brush_arm": make_brush_arm,
    }

    print(f"Params: outlets={p.outlet_count}, pockets={p.pocket_count}, "
          f"index={p.index_angle_deg}°, parallel_feed={p.outlet_count}/step")

    for name, fn in builders.items():
        print(f"  building {name} ...")
        solid = fn(p)
        cq.exporters.export(solid, str(stl_dir / f"{name}.stl"))
        cq.exporters.export(solid, str(step_dir / f"{name}.step"))
        print(f"    -> {name}.stl / .step")

    # Duplicate chute note: print outlet_count copies of outlet_chute.stl
    asm_parts = make_assembly(p, disc_angle_deg=0, explode=0)
    asm = combine_parts(asm_parts)
    cq.exporters.export(asm, str(stl_dir / "assembly_reference.stl"))
    cq.exporters.export(asm, str(step_dir / "assembly_reference.step"))
    print("  -> assembly_reference")

    exploded_parts = make_assembly(p, disc_angle_deg=15, explode=1.0)
    exploded = combine_parts(exploded_parts)
    cq.exporters.export(exploded, str(stl_dir / "assembly_exploded.stl"))
    cq.exporters.export(exploded, str(step_dir / "assembly_exploded.step"))
    print("  -> assembly_exploded")

    # Metadata for simulation
    meta = out_dir / "sim_joints_cq.json"
    meta.write_text(
        _sim_json(p),
        encoding="utf-8",
    )
    print(f"Wrote {meta}")
    return p


def _sim_json(p: Params) -> str:
    import json

    data = {
        "units": "mm",
        "outlet_count": p.outlet_count,
        "pocket_count": p.pocket_count,
        "index_angle_deg": p.index_angle_deg,
        "screws_per_index": p.outlet_count,
        "outlet_angles_deg": p.outlet_angles_deg,
        "revolute_joints": [
            {
                "name": "disc_drive",
                "parts": ["drive_hub", "rotary_disc"],
                "axis": [0, 0, 1],
                "origin_mm": [0, 0, p.base_thickness],
            }
        ],
        "fixed_parts": [
            "base_plate",
            "bowl",
            "cover",
            "brush_arm",
            *[f"outlet_chute_{i}" for i in range(p.outlet_count)],
        ],
        "sensors": [
            {
                "name": f"count_ir_{i}",
                "outlet_index": i,
                "angle_deg": a,
                "note": "optical fork on outlet_chute sensor slot",
            }
            for i, a in enumerate(p.outlet_angles_deg)
        ],
        "reference": "https://www.youtube.com/shorts/V1ai93n3C1I",
        "notes": (
            "Multi-outlet parallel discharge multiplies counting throughput. "
            "Industrial vibratory bowls use multi-track exits similarly; "
            "this design uses a rotary disc with synchronized drop windows."
        ),
    }
    return json.dumps(data, indent=2)


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    export_all(root, Params(outlet_count=4, pocket_count=12))
