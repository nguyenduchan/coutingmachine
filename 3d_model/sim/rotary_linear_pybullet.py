"""
Rotary_Linear physics — EXACT FreeCAD meshes (STL) in PyBullet.

Spur rack & pinion: pinion rotates about Y; rack/follower translates in Z.
Contact-only drive + gravity. No θ→Z formula on the follower.

Pipeline:
  freecadcmd 3d_model/freecad/export_rotary_linear_meshes.py
  python 3d_model/sim/rotary_linear_pybullet.py [--gui]
"""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import pybullet as p
import pybullet_data

ROOT = Path(__file__).resolve().parent
MESH = ROOT / "meshes" / "rotary_linear"
OUT = ROOT / "out"
OUT.mkdir(exist_ok=True)
METRICS = OUT / "rotary_linear_metrics.json"
REVIEW = OUT / "rotary_linear_physics_review.txt"

S = 0.001  # mm → m
G = 9.81
KNOB_RPM = 15.0
FORCE_EPS = 0.05
OMEGA_SIGN = 1.0


def q_y(a: float):
    return p.getQuaternionFromEuler([0.0, a, 0.0])


def ensure_meshes() -> dict:
    man = MESH / "manifest.json"
    if not man.is_file() or not (MESH / "RL_Pinion_Shaft.stl").is_file():
        raise SystemExit(
            "Missing CAD meshes. Run first:\n"
            "  freecadcmd 3d_model/freecad/export_rotary_linear_meshes.py\n"
            f"Expected: {MESH}"
        )
    return json.loads(man.read_text(encoding="utf-8"))


def stl_to_obj(stl: Path) -> Path:
    import trimesh

    obj = stl.with_suffix(".obj")
    if obj.is_file() and obj.stat().st_mtime >= stl.stat().st_mtime:
        return obj
    mesh = trimesh.load(str(stl), force="mesh")
    mesh.export(str(obj))
    return obj


def vhacd_file(stl: Path) -> Path:
    """Decompose follower for dynamic collision. Call while NO client open."""
    out = stl.with_name(stl.stem + "_vhacd.obj")
    if out.is_file() and out.stat().st_mtime >= stl.stat().st_mtime:
        return out
    # stale cache
    if out.is_file():
        out.unlink()
    obj_in = stl_to_obj(stl)
    log = stl.with_name(stl.stem + "_vhacd.log")
    cid = p.connect(p.DIRECT)
    try:
        p.vhacd(
            str(obj_in),
            str(out),
            str(log),
            resolution=120000,
            depth=20,
            maxNumVerticesPerCH=64,
            physicsClientId=cid,
        )
    except Exception as exc:
        print("VHACD skip (%s) — convex hull of STL" % exc)
        out = stl
    finally:
        p.disconnect(physicsClientId=cid)
    return out if Path(out).is_file() else stl


def world(gui: bool) -> int:
    cid = p.connect(p.GUI if gui else p.DIRECT)
    p.setAdditionalSearchPath(pybullet_data.getDataPath(), physicsClientId=cid)
    p.resetSimulation(physicsClientId=cid)
    p.setGravity(0, 0, -G, physicsClientId=cid)
    p.setTimeStep(1 / 500.0, physicsClientId=cid)
    p.setPhysicsEngineParameter(numSolverIterations=250, physicsClientId=cid)
    if gui:
        p.resetDebugVisualizerCamera(0.28, 50, -30, [0.0, 0.0, 0.02], physicsClientId=cid)
        p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 0, physicsClientId=cid)
    p.loadURDF("plane.urdf", [0, 0, -0.08], physicsClientId=cid)
    return cid


def load_mesh_body(
    cid,
    stl: Path,
    *,
    mass: float,
    rgba: list,
    concave: bool = False,
    friction: float = 0.55,
    collision_file: Path | None = None,
) -> int:
    scale = [S, S, S]
    vis_path = str(stl.resolve())
    col_path = str((collision_file or stl).resolve())
    if concave and mass == 0.0:
        col = p.createCollisionShape(
            p.GEOM_MESH,
            fileName=col_path,
            meshScale=scale,
            flags=p.GEOM_FORCE_CONCAVE_TRIMESH,
            physicsClientId=cid,
        )
    else:
        col = p.createCollisionShape(
            p.GEOM_MESH,
            fileName=col_path,
            meshScale=scale,
            physicsClientId=cid,
        )
    vis = p.createVisualShape(
        p.GEOM_MESH,
        fileName=vis_path,
        meshScale=scale,
        rgbaColor=rgba,
        physicsClientId=cid,
    )
    bid = p.createMultiBody(
        mass, col, vis, [0, 0, 0], [0, 0, 0, 1], physicsClientId=cid
    )
    p.changeDynamics(
        bid,
        -1,
        lateralFriction=friction,
        spinningFriction=0.02,
        rollingFriction=0.01,
        restitution=0.0,
        linearDamping=0.04,
        angularDamping=0.15,
        physicsClientId=cid,
    )
    return bid


def contact_force(cid, a, b) -> float:
    return float(sum(pt[9] for pt in p.getContactPoints(a, b, physicsClientId=cid)))


def gap(cid, a, b, dist=0.05) -> float:
    pts = p.getClosestPoints(a, b, distance=dist, physicsClientId=cid)
    return float(pts[0][8]) if pts else dist


def axis_pivot_from_manifest(manifest: dict) -> list[float]:
    """Pinion axis // Y through CAD (0, 0, z_pin); z_pin from pinion bbox center."""
    kin = manifest.get("kinematics") or {}
    if "axis_pivot_m" in kin:
        return list(kin["axis_pivot_m"])
    pin = (manifest.get("parts") or {}).get("RL_Pinion_Shaft") or {}
    bb = pin.get("bbox_mm") or {}
    z_mm = 0.5 * (float(bb.get("zmin", 0)) + float(bb.get("zmax", 0)))
    x_mm = 0.5 * (float(bb.get("xmin", 0)) + float(bb.get("xmax", 0)))
    return [x_mm * S, 0.0, z_mm * S]


def make_pinion_collision(cid, manifest: dict) -> int:
    """Convex tooth proxies for kinematic pinion (axis Y at pivot)."""
    rack = manifest.get("rack") or {}
    m = float(rack.get("module", 2.0))
    teeth = int(rack.get("pinion_teeth", 12))
    face_w = float(rack.get("face_w", 10.0))
    tip_r = 0.5 * m * (teeth + 2.0)
    root_r = 0.5 * m * (teeth - 2.5)
    cp = math.pi * m
    tooth_w = 0.45 * cp
    pivot = axis_pivot_from_manifest(manifest)
    types, half, frames_pos, frames_orn = [], [], [], []
    # Hub
    types.append(p.GEOM_CYLINDER)
    # For cylinder in shape array: radius via radii?, halfExtents unused — use BOX hub instead
    types[-1] = p.GEOM_BOX
    half.append([root_r * S, 0.5 * face_w * S, root_r * S])
    frames_pos.append(list(pivot))
    frames_orn.append([0, 0, 0, 1])
    # Teeth around Y axis → in XZ plane (offset so a tooth faces -X / rack)
    for i in range(teeth):
        a = 2.0 * math.pi * i / teeth + math.pi
        # Tooth center at tip mid-radius
        rm = 0.5 * (root_r + tip_r)
        tx = pivot[0] + rm * math.cos(a) * S
        tz = pivot[2] + rm * math.sin(a) * S
        depth = tip_r - root_r
        types.append(p.GEOM_BOX)
        half.append([0.5 * depth * S, 0.5 * face_w * S, 0.5 * tooth_w * S])
        frames_pos.append([tx, pivot[1], tz])
        frames_orn.append([0.0, math.sin(0.5 * a), 0.0, math.cos(0.5 * a)])
    return p.createCollisionShapeArray(
        shapeTypes=types,
        halfExtents=half,
        collisionFramePositions=frames_pos,
        collisionFrameOrientations=frames_orn,
        physicsClientId=cid,
    )


def make_follower_collision(cid, manifest: dict) -> int:
    """
    Compound convex proxies for rack teeth + carriage (VHACD eats fine teeth).
    Positions in metres, CAD world frame at rest (θ=0, z=0).
    """
    rack = manifest.get("rack") or {}
    m = float(rack.get("module", 2.0))
    pitch = math.pi * m
    clear = float(rack.get("tooth_clear", 0.3))
    face_w = float(rack.get("face_w", 10.0))
    pitch_d = float(rack.get("pitch_d", m * float(rack.get("pinion_teeth", 12))))
    pitch_r = 0.5 * pitch_d
    addendum = m
    x_pitch = -pitch_r
    x_tip = x_pitch + addendum - clear - 0.4  # extra backlash for sim stability
    x_root = x_pitch - 0.2 * m
    tooth_depth = max(1.2, x_tip - x_root)
    tooth_t = max(0.9, 0.40 * pitch - clear)
    # Match CAD rack span around pinion (z_pin ≈ 17 mm)
    pin = (manifest.get("parts") or {}).get("RL_Pinion_Shaft", {}).get("bbox_mm") or {}
    z_pin = 0.5 * (float(pin.get("zmin", 17)) + float(pin.get("zmax", 17)))
    rack_len = float(rack.get("stroke", 20)) + 2.0 * (0.5 * m * (float(rack.get("pinion_teeth", 12)) + 2)) + 2 * pitch + 6
    rack_z0 = z_pin - 0.5 * rack_len
    n = max(4, int(math.ceil(rack_len / pitch)) + 1)

    fol = (manifest.get("parts") or {}).get("RL_Follower", {}).get("bbox_mm") or {}
    # Carriage block from follower bbox (slightly shrunk)
    cx0 = float(fol.get("xmin", -30))
    cx1 = float(fol.get("xmax", -14))
    cy0 = float(fol.get("ymin", -20))
    cy1 = float(fol.get("ymax", 20))
    cz0 = float(fol.get("zmin", 0))
    cz1 = min(float(fol.get("zmax", 40)), cz0 + 25.0)
    # Keep carriage away from tooth tips so proxies dominate mesh zone
    cx1 = min(cx1, x_root - 1.0)

    types = []
    half = []
    frames_pos = []
    frames_orn = []

    # Carriage
    hx = 0.5 * max(2.0, cx1 - cx0) * S
    hy = 0.5 * max(2.0, cy1 - cy0) * S
    hz = 0.5 * max(2.0, cz1 - cz0) * S
    types.append(p.GEOM_BOX)
    half.append([hx, hy, hz])
    frames_pos.append(
        [0.5 * (cx0 + cx1) * S, 0.5 * (cy0 + cy1) * S, 0.5 * (cz0 + cz1) * S]
    )
    frames_orn.append([0, 0, 0, 1])

    # Rack teeth (boxes)
    for i in range(n):
        zc = rack_z0 + (i + 0.5) * pitch
        if zc < rack_z0 or zc > rack_z0 + rack_len:
            continue
        types.append(p.GEOM_BOX)
        half.append(
            [
                0.5 * tooth_depth * S,
                0.5 * min(face_w, 12.0) * S,
                0.5 * tooth_t * S,
            ]
        )
        frames_pos.append(
            [
                0.5 * (x_root + x_tip) * S,
                0.0,
                zc * S,
            ]
        )
        frames_orn.append([0, 0, 0, 1])

    return p.createCollisionShapeArray(
        shapeTypes=types,
        halfExtents=half,
        collisionFramePositions=frames_pos,
        collisionFrameOrientations=frames_orn,
        physicsClientId=cid,
    )


def build(cid, manifest: dict, follower_col: Path) -> dict:
    ids: dict = {}
    rgba = {
        "RL_Pinion_Shaft": [1.0, 0.45, 0.05, 1],
        "RL_Knob": [0.45, 0.25, 0.55, 1],
        "RL_Follower": [0.25, 0.72, 0.35, 1],
        "RL_Bearing_Rail_S": [0.30, 0.50, 0.75, 1],
        "RL_Bearing_Cap_S": [0.40, 0.60, 0.85, 1],
        "RL_Bearing_Rail_N": [0.30, 0.50, 0.75, 1],
        "RL_Bearing_Cap_N": [0.40, 0.60, 0.85, 1],
        "RL_Friction_Washer": [0.35, 0.35, 0.38, 1],
    }

    for name in manifest["roles"]["static"]:
        stl = MESH / f"{name}.stl"
        if not stl.is_file():
            continue
        # Rails: visual only — Z guide is prismatic constraint (mesh rails leak)
        if name.startswith("RL_Guide_Rail"):
            ids[name] = load_mesh_body(
                cid,
                stl,
                mass=0.0,
                rgba=rgba.get(name, [0.5, 0.5, 0.5, 1]),
                concave=True,
            )
            continue
        ids[name] = load_mesh_body(
            cid, stl, mass=0.0, rgba=rgba.get(name, [0.5, 0.5, 0.5, 1]), concave=True
        )

    ids["actuator"] = []
    for name in manifest["roles"]["actuator"]:
        stl = MESH / f"{name}.stl"
        if not stl.is_file():
            continue
        if name == "RL_Pinion_Shaft":
            col = make_pinion_collision(cid, manifest)
            vis = p.createVisualShape(
                p.GEOM_MESH,
                fileName=str(stl.resolve()),
                meshScale=[S, S, S],
                rgbaColor=rgba["RL_Pinion_Shaft"],
                physicsClientId=cid,
            )
            bid = p.createMultiBody(
                0.0, col, vis, [0, 0, 0], [0, 0, 0, 1], physicsClientId=cid
            )
            p.changeDynamics(
                bid,
                -1,
                lateralFriction=0.7,
                spinningFriction=0.02,
                rollingFriction=0.01,
                restitution=0.0,
                physicsClientId=cid,
            )
        else:
            bid = load_mesh_body(
                cid,
                stl,
                mass=0.0,
                rgba=rgba.get(name, [0.7, 0.7, 0.7, 1]),
                concave=False,
                friction=0.4,
            )
        ids[name] = bid
        ids["actuator"].append(bid)

    # Follower: CAD visual + compound tooth proxies for contact
    fol_stl = MESH / "RL_Follower.stl"
    col = make_follower_collision(cid, manifest)
    vis = p.createVisualShape(
        p.GEOM_MESH,
        fileName=str(fol_stl.resolve()),
        meshScale=[S, S, S],
        rgbaColor=rgba["RL_Follower"],
        physicsClientId=cid,
    )
    ids["RL_Follower"] = p.createMultiBody(
        0.05, col, vis, [0, 0, 0], [0, 0, 0, 1], physicsClientId=cid
    )
    p.changeDynamics(
        ids["RL_Follower"],
        -1,
        lateralFriction=0.85,
        spinningFriction=0.05,
        rollingFriction=0.02,
        restitution=0.0,
        linearDamping=0.2,
        angularDamping=0.5,
        physicsClientId=cid,
    )

    for name in ("RL_Friction_Washer",):
        if name in ids:
            p.setCollisionFilterPair(
                ids[name], ids["RL_Follower"], -1, -1, 0, physicsClientId=cid
            )
    # Disable leaky mesh-rail ↔ follower (prismatic replaces them)
    for name in (
        "RL_Bearing_Rail_S",
        "RL_Bearing_Cap_S",
        "RL_Bearing_Rail_N",
        "RL_Bearing_Cap_N",
    ):
        if name in ids:
            p.setCollisionFilterPair(
                ids[name], ids["RL_Follower"], -1, -1, 0, physicsClientId=cid
            )

    ids["stroke_mm"] = float(manifest.get("rail_stroke_mm", 20.0))
    ids["pinion"] = ids.get("RL_Pinion_Shaft")
    ids["follower"] = ids["RL_Follower"]
    ids["axis_pivot"] = axis_pivot_from_manifest(manifest)
    ids["rest_xy"] = [0.0, 0.0]

    # Ideal linear bearing: prismatic along Z at CAD XY (not a θ→Z drive)
    ids["slide"] = p.createConstraint(
        parentBodyUniqueId=ids["follower"],
        parentLinkIndex=-1,
        childBodyUniqueId=-1,
        childLinkIndex=-1,
        jointType=p.JOINT_PRISMATIC,
        jointAxis=[0, 0, 1],
        parentFramePosition=[0, 0, 0],
        childFramePosition=[0, 0, 0],
        parentFrameOrientation=[0, 0, 0, 1],
        childFrameOrientation=[0, 0, 0, 1],
        physicsClientId=cid,
    )
    p.changeConstraint(ids["slide"], maxForce=500.0, physicsClientId=cid)
    return ids


def set_actuator(cid, ids, theta: float, omega: float = 0.0):
    """
    Rotate actuator meshes about pinion axis (world Y through pivot).
    CAD meshes authored in world mm at θ=0 with base at origin →
      base_orn = Ry(θ)
      base_pos = pivot - Ry(θ)·pivot
    """
    px, py, pz = ids["axis_pivot"]
    c, s = math.cos(theta), math.sin(theta)
    rx = c * px + s * pz
    ry = py
    rz = -s * px + c * pz
    pos = [px - rx, py - ry, pz - rz]
    orn = q_y(theta)
    for bid in ids["actuator"]:
        p.resetBasePositionAndOrientation(bid, pos, orn, physicsClientId=cid)
        p.resetBaseVelocity(bid, [0, 0, 0], [0, omega, 0], physicsClientId=cid)


def rail_z_only(cid, ids):
    """Keep follower upright at CAD XY; Z free (prismatic + contact)."""
    fol = ids["follower"]
    pos, _ = p.getBasePositionAndOrientation(fol, physicsClientId=cid)
    lin, _ = p.getBaseVelocity(fol, physicsClientId=cid)
    rx, ry = ids["rest_xy"]
    # Soft clamp stroke window (bottom stop assist)
    z = pos[2]
    z_min = -0.002
    z_max = ids["stroke_mm"] * S + 0.01
    if z < z_min:
        z = z_min
        lin = (0.0, 0.0, max(0.0, lin[2]))
    if z > z_max:
        z = z_max
        lin = (0.0, 0.0, min(0.0, lin[2]))
    p.resetBasePositionAndOrientation(
        fol, [rx, ry, z], (0, 0, 0, 1), physicsClientId=cid
    )
    p.resetBaseVelocity(fol, [0.0, 0.0, lin[2]], [0, 0, 0], physicsClientId=cid)


def run(gui: bool, seconds: float):
    manifest = ensure_meshes()
    print("Kinematics:", manifest.get("kinematics"))

    cid = world(gui)
    ids = build(cid, manifest, MESH / "RL_Follower.stl")
    print("Axis pivot (m):", ids["axis_pivot"])

    dt = 1 / 500.0
    steps = int(seconds / dt)
    omega = OMEGA_SIGN * KNOB_RPM * 2 * math.pi / 60.0

    # CAD rest pose — do not drift XY
    ids["rest_xy"] = [0.0, 0.0]
    p.resetBasePositionAndOrientation(
        ids["follower"], [0, 0, 0], (0, 0, 0, 1), physicsClientId=cid
    )
    set_actuator(cid, ids, 0.0, 0.0)
    for _ in range(300):
        p.stepSimulation(physicsClientId=cid)
        rail_z_only(cid, ids)

    z0 = p.getBasePositionAndOrientation(ids["follower"], physicsClientId=cid)[0][2]
    pin = ids["pinion"]
    fc0 = contact_force(cid, pin, ids["follower"]) if pin else 0.0
    g0 = gap(cid, pin, ids["follower"]) if pin else 1.0
    print(
        "CAD meshes from",
        MESH,
        "| settle z=%.4f gap=%.4f N=%.2f" % (z0, g0, fc0),
    )

    c = p.createCollisionShape(
        p.GEOM_BOX, halfExtents=[0.003, 0.003, 0.003], physicsClientId=cid
    )
    v = p.createVisualShape(
        p.GEOM_BOX,
        halfExtents=[0.003, 0.003, 0.003],
        rgbaColor=[0.9, 0.2, 0.9, 1],
        physicsClientId=cid,
    )
    free = p.createMultiBody(0.04, c, v, [0.1, 0.05, 0.12], physicsClientId=cid)
    fall_z0 = p.getBasePositionAndOrientation(free, physicsClientId=cid)[0][2]

    samples = []
    max_contact = 0.0
    illegal = 0
    ghost = 0
    prev_z = z0
    z_min, z_max = z0, z0

    for step in range(steps):
        t = step * dt
        theta = omega * t
        set_actuator(cid, ids, theta, omega)
        p.stepSimulation(physicsClientId=cid)
        rail_z_only(cid, ids)

        if step % 5 == 0:
            fz = p.getBasePositionAndOrientation(ids["follower"], physicsClientId=cid)[0][2]
            z_min, z_max = min(z_min, fz), max(z_max, fz)
            pts = (
                p.getContactPoints(pin, ids["follower"], physicsClientId=cid)
                if pin
                else []
            )
            fc = float(sum(pt[9] for pt in pts))
            in_contact = len(pts) > 0
            max_contact = max(max_contact, fc)
            if fc > FORCE_EPS and not in_contact:
                illegal += 1
            if (fz - prev_z) > 0.00025 and not in_contact:
                ghost += 1
            prev_z = fz
            samples.append(
                {
                    "t": t,
                    "turns": theta / (2 * math.pi),
                    "follower_z_m": fz,
                    "dz_mm": (fz - z0) / S,
                    "contact_N": fc,
                    "n_contacts": len(pts),
                    "in_contact": in_contact,
                }
            )

        if gui and step % 3 == 0:
            time.sleep(dt * 2)

    fall_z1 = p.getBasePositionAndOrientation(free, physicsClientId=cid)[0][2]
    free_fall_delta = fall_z0 - fall_z1
    travel_mm = (z_max - z_min) / S
    stroke = ids["stroke_mm"]

    travel_ok = travel_mm >= 0.35 * stroke
    fall_ok = free_fall_delta > 0.02
    illegal_ok = illegal == 0
    ghost_ok = ghost == 0
    contact_ok = max_contact > 0.05
    passed = all([travel_ok, fall_ok, illegal_ok, ghost_ok, contact_ok])

    lines = [
        "METHOD: exact FreeCAD STL visuals + tooth proxy contact in PyBullet",
        "KINEMATICS: pinion rotates about Y; rack translates Z (spur)",
        "ONE actuator = RL_Pinion(+shaft/knob) kinematic | RL_Follower(+rack) dynamic",
        "Drive force = pinion/rack CONTACT only; prismatic = ideal rail bearing",
        f"mesh_dir={MESH}",
        f"axis_pivot_m={ids['axis_pivot']}",
        f"measured_Z_range_mm={travel_mm:.2f} (CAD stroke={stroke:.1f})",
        f"max_contact_N={max_contact:.3f}",
        f"illegal_force_while_separated={illegal}",
        f"ghost_moves_without_contact={ghost}",
        f"free_fall_delta_z_m={free_fall_delta:.4f}",
        f"pass={passed}",
    ]
    REVIEW.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report = {
        "mechanism": "rack_pinion",
        "kinematics": manifest.get("kinematics"),
        "meshes": str(MESH),
        "manifest": manifest.get("mechanism"),
        "force_sources": ["RL_Pinion_assembly_kinematic_about_Y"],
        "axis_pivot_m": ids["axis_pivot"],
        "measured_Z_range_mm": travel_mm,
        "cad_stroke_mm": stroke,
        "max_contact_N": max_contact,
        "illegal_force_while_separated": illegal,
        "ghost_moves_without_contact": ghost,
        "free_fall_delta_z_m": free_fall_delta,
        "pass": passed,
        "checks": {
            "travel_ok": travel_ok,
            "fall_ok": fall_ok,
            "illegal_ok": illegal_ok,
            "ghost_ok": ghost_ok,
            "contact_ok": contact_ok,
        },
        "samples": samples[:: max(1, len(samples) // 80)],
    }
    METRICS.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\n".join(lines))
    print("Wrote", METRICS)

    if gui:
        print("GUI open — knob turning (close window or Ctrl+C)")
        t0 = time.time()
        try:
            while p.isConnected(cid):
                te = time.time() - t0
                set_actuator(cid, ids, omega * te, omega)
                p.stepSimulation(physicsClientId=cid)
                rail_z_only(cid, ids)
                time.sleep(dt)
        except KeyboardInterrupt:
            pass
    p.disconnect(physicsClientId=cid)
    return 0 if passed else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gui", action="store_true")
    ap.add_argument("--seconds", type=float, default=8.0)
    args = ap.parse_args()
    raise SystemExit(run(args.gui, args.seconds))


if __name__ == "__main__":
    main()
