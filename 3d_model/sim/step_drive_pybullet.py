"""
Step-feeder drive — CONTACT force transmission + gravity (PyBullet).

Rules (user):
  1) Two bodies exchange force/moment ONLY while in contact (collision).
  2) No contact => no force between them.
  3) Gravity always pulls dynamic bodies down (g = -9.81).

NOT used for drive transmission: POINT2POINT / invisible joints across air gaps.
Motor shaft is a kinematic ACTUATOR (imposes motion). Followers are dynamic and
are lifted only by CONTACT with the eccentric cams; otherwise they fall.

Outputs:
  out/physics_review.txt
  out/step_drive_metrics.json
  frames_drive_phys/frame_XXXX.png

  python step_drive_pybullet.py --gui
"""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np
import pybullet as p
import pybullet_data

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
FRAMES = ROOT / "frames_drive_phys"
OUT.mkdir(exist_ok=True)
FRAMES.mkdir(exist_ok=True)
REVIEW = OUT / "physics_review.txt"
METRICS = OUT / "step_drive_metrics.json"

S = 0.01
G = 9.81
ECC = 1.2 * S
CAM_R = 1.4 * S
MOTOR_RPM = 20.0
SHAFT_Z = 4.0 * S
XA, XB = 3.5 * S, 6.5 * S
FOLLOW_HALF = [1.1 * S, 1.0 * S, 0.55 * S]


def q_y(a):
    return p.getQuaternionFromEuler([0, a, 0])


def q_x(a):
    return p.getQuaternionFromEuler([a, 0, 0])


def world(gui: bool) -> int:
    cid = p.connect(p.GUI if gui else p.DIRECT)
    p.setAdditionalSearchPath(pybullet_data.getDataPath(), physicsClientId=cid)
    p.resetSimulation(physicsClientId=cid)
    p.setGravity(0, 0, -G, physicsClientId=cid)  # ALWAYS on
    p.setTimeStep(1 / 500.0, physicsClientId=cid)
    p.setPhysicsEngineParameter(
        numSolverIterations=250,
        contactBreakingThreshold=0.001,
        physicsClientId=cid,
    )
    if gui:
        p.resetDebugVisualizerCamera(0.55, 50, -30, [0.05, 0.0, 0.05], physicsClientId=cid)
        p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 0, physicsClientId=cid)
    p.loadURDF("plane.urdf", [0, 0, -0.02], physicsClientId=cid)
    return cid


def static_box(cid, half, pos, rgba):
    c = p.createCollisionShape(p.GEOM_BOX, halfExtents=half, physicsClientId=cid)
    v = p.createVisualShape(p.GEOM_BOX, halfExtents=half, rgbaColor=list(rgba), physicsClientId=cid)
    return p.createMultiBody(0, c, v, pos, physicsClientId=cid)


def dyn_box(cid, half, pos, rgba, mass, friction=0.6):
    c = p.createCollisionShape(p.GEOM_BOX, halfExtents=half, physicsClientId=cid)
    v = p.createVisualShape(p.GEOM_BOX, halfExtents=half, rgbaColor=list(rgba), physicsClientId=cid)
    bid = p.createMultiBody(mass, c, v, pos, physicsClientId=cid)
    p.changeDynamics(
        bid,
        -1,
        lateralFriction=friction,
        spinningFriction=0.02,
        rollingFriction=0.01,
        restitution=0.0,
        linearDamping=0.01,
        angularDamping=0.05,
        physicsClientId=cid,
    )
    return bid


def dyn_cyl(cid, radius, height, pos, orn, rgba, mass, friction=0.45):
    c = p.createCollisionShape(p.GEOM_CYLINDER, radius=radius, height=height, physicsClientId=cid)
    v = p.createVisualShape(
        p.GEOM_CYLINDER, radius=radius, length=height, rgbaColor=list(rgba), physicsClientId=cid
    )
    bid = p.createMultiBody(mass, c, v, pos, orn, physicsClientId=cid)
    p.changeDynamics(bid, -1, lateralFriction=friction, restitution=0.0, physicsClientId=cid)
    return bid


def kin_cyl(cid, radius, height, pos, orn, rgba):
    """Mass 0 — pose set each step (motor actuator). Still participates in contacts."""
    c = p.createCollisionShape(p.GEOM_CYLINDER, radius=radius, height=height, physicsClientId=cid)
    v = p.createVisualShape(
        p.GEOM_CYLINDER, radius=radius, length=height, rgbaColor=list(rgba), physicsClientId=cid
    )
    return p.createMultiBody(0.0, c, v, pos, orn, physicsClientId=cid)


def contact_force(cid, a, b):
    """Total normal contact force between a and b. 0 if not touching."""
    pts = p.getContactPoints(a, b, physicsClientId=cid)
    return float(sum(pt[9] for pt in pts))  # normal force


def gap(cid, a, b):
    """Positive = separation; negative = penetration."""
    pts = p.getClosestPoints(a, b, distance=0.05, physicsClientId=cid)
    if not pts:
        return 0.05
    return float(pts[0][8])


def build(cid):
    ids = {}

    # Floor / frame
    static_box(cid, [12 * S, 5 * S, 0.2 * S], [5 * S, 0, 0.2 * S], (0.4, 0.42, 0.45, 1))
    # Motor housing (fixed) — does not spin
    static_box(cid, [2.0 * S, 1.85 * S, 1.85 * S], [-2.5 * S, 0, SHAFT_Z - 0.7 * S], (0.12, 0.12, 0.14, 1))
    static_box(cid, [1.3 * S, 1.85 * S, 1.85 * S], [-0.9 * S, 0, SHAFT_Z - 0.7 * S], (0.72, 0.74, 0.76, 1))

    # Vertical guide walls — CONTACT only constrains X (followers slide in Z under gravity/cam)
    for x in (XA, XB):
        for dx in (-1.35 * S, 1.35 * S):
            static_box(
                cid,
                [0.2 * S, 1.2 * S, 5 * S],
                [x + dx, 0, SHAFT_Z + 1.5 * S],
                (0.55, 0.57, 0.6, 1),
            )
        # Y fences
        for dy in (-1.25 * S, 1.25 * S):
            static_box(
                cid,
                [1.1 * S, 0.15 * S, 5 * S],
                [x, dy, SHAFT_Z + 1.5 * S],
                (0.55, 0.57, 0.6, 1),
            )

    # Shaft (kinematic actuator)
    ids["shaft"] = kin_cyl(
        cid, 0.28 * S, 12 * S, [4 * S, 0, SHAFT_Z], q_y(math.pi / 2), (0.8, 0.82, 0.85, 1)
    )

    def make_eccentric_cam(tag, x, phase_a, rgba):
        """
        Eccentric circular cam: geometric center offset by ECC from shaft axis.
        Pose updated with shaft angle each step (same rigid drive).
        Contact with follower transmits normal force only when touching.
        """
        # Rest angle 0: A at bottom (-ECC in Z), B opposite (+ECC)
        z0 = SHAFT_Z + (-ECC if phase_a else +ECC)
        cam = kin_cyl(cid, CAM_R, 1.0 * S, [x, 0, z0], q_y(math.pi / 2), rgba)
        ids[f"cam_{tag}"] = cam
        ids[f"cam_{tag}_x"] = x
        ids[f"cam_{tag}_phase"] = 0.0 if phase_a else math.pi
        return cam

    make_eccentric_cam("A", XA, True, (1.0, 0.45, 0.05, 1))
    make_eccentric_cam("B", XB, False, (0.05, 0.75, 0.95, 1))

    def make_follower(tag, x, cam_id, rgba_plate, plate_xs):
        """
        Dynamic follower rests ON cam (gravity). Lifted only by CONTACT.
        Plates are FIXED constraints (= bolted / same assembly, permanent contact).
        """
        # Place follower sitting on cam at rest: top of cam ≈ z0 + CAM_R
        phase = ids[f"cam_{tag}_phase"]
        z_cam = SHAFT_Z + ECC * math.cos(phase)  # at angle 0 after first set
        # At build time cam is at z0 already
        z0 = SHAFT_Z + (-ECC if tag == "A" else +ECC)
        z_follow = z0 + CAM_R + FOLLOW_HALF[2] + 0.0005  # slight clearance then settle
        follow = dyn_box(cid, FOLLOW_HALF, [x, 0, z_follow], (0.55, 0.55, 0.58, 1), mass=0.25, friction=0.35)
        ids[f"follow_{tag}"] = follow
        ids[f"follow_{tag}_cam"] = cam_id

        plates = []
        for i, dx in plate_xs:
            pl = dyn_box(
                cid,
                [0.2 * S, 1.8 * S, 1.0 * S],
                [x + dx, 0, z_follow - 1.1 * S],
                rgba_plate,
                mass=0.08,
                friction=0.5,
            )
            # Bolted = permanent contact/joint within one assembly (not drive transmission)
            cid_f = p.createConstraint(
                follow,
                -1,
                pl,
                -1,
                p.JOINT_FIXED,
                [0, 0, 0],
                [dx, 0, -1.1 * S],
                [0, 0, 0],
                physicsClientId=cid,
            )
            plates.append(pl)
            ids[f"_fix_plate_{i}"] = cid_f
        ids[f"plates_{tag}"] = plates
        return follow

    make_follower("A", XA, ids["cam_A"], (0.2, 0.85, 0.3, 1), [(0, 1.5 * S), (2, 3.0 * S)])
    make_follower("B", XB, ids["cam_B"], (0.15, 0.7, 0.25, 1), [(1, 1.5 * S), (3, 3.0 * S)])

    # --- Gravity demo: free block (no support) must fall ---
    ids["free_fall"] = dyn_box(
        cid, [0.5 * S, 0.5 * S, 0.5 * S], [11 * S, -2 * S, 8 * S], (0.9, 0.2, 0.9, 1), mass=0.2
    )

    # --- Contact demo: pusher (kinematic) hits free block; force only while contacting ---
    ids["pusher"] = kin_cyl(
        cid, 0.4 * S, 0.8 * S, [10 * S, 2.5 * S, 0.9 * S], q_y(math.pi / 2), (0.9, 0.85, 0.1, 1)
    )
    ids["pushed"] = dyn_box(
        cid, [0.45 * S, 0.45 * S, 0.45 * S], [12.5 * S, 2.5 * S, 0.9 * S], (0.2, 0.5, 1.0, 1), mass=0.15
    )
    # Small stand so pushed doesn't fall through before hit — actually on plane height
    # plane at -0.02, box half 0.45S → put z = 0.45S
    p.resetBasePositionAndOrientation(
        ids["pushed"], [12.5 * S, 2.5 * S, 0.5 * S], [0, 0, 0, 1], physicsClientId=cid
    )
    p.resetBasePositionAndOrientation(
        ids["pusher"], [10 * S, 2.5 * S, 0.5 * S], q_y(math.pi / 2), physicsClientId=cid
    )

    return ids


def set_drive_pose(cid, ids, angle):
    """Impose motor shaft + eccentric cam poses (actuator)."""
    # Shaft about X
    p.resetBasePositionAndOrientation(
        ids["shaft"], [4 * S, 0, SHAFT_Z], p.getQuaternionFromEuler([angle, math.pi / 2, 0]), physicsClientId=cid
    )
    for tag in ("A", "B"):
        x = ids[f"cam_{tag}_x"]
        phase = ids[f"cam_{tag}_phase"]
        th = angle + phase
        # Eccentric center orbits in YZ about shaft axis (rotation about X)
        y = ECC * math.sin(th)
        z = SHAFT_Z + ECC * math.cos(th)
        p.resetBasePositionAndOrientation(
            ids[f"cam_{tag}"],
            [x, y, z],
            p.getQuaternionFromEuler([angle, math.pi / 2, 0]),
            physicsClientId=cid,
        )


def set_pusher(cid, ids, t, period=1.2):
    """Move pusher in X; contacts blue block only when overlapping."""
    # Oscillate 10cm .. 13cm
    x = 10 * S + (1.5 * S) * (1 + math.sin(2 * math.pi * t / period))
    p.resetBasePositionAndOrientation(
        ids["pusher"], [x, 2.5 * S, 0.5 * S], q_y(math.pi / 2), physicsClientId=cid
    )


def capture(cid, path: Path, w=960, h=540):
    view = p.computeViewMatrixFromYawPitchRoll([0.06, 0.0, 0.05], 0.55, 45, -28, 0, 2)
    proj = p.computeProjectionMatrixFOV(55, w / h, 0.02, 2.0)
    _, _, rgb, _, _ = p.getCameraImage(w, h, view, proj, renderer=p.ER_TINY_RENDERER, physicsClientId=cid)
    arr = np.asarray(rgb, dtype=np.uint8).reshape(h, w, 4)
    from PIL import Image

    Image.fromarray(arr[:, :, :3]).save(path)


def run(gui: bool, seconds: float, save_frames: bool):
    for f in FRAMES.glob("frame_*.png"):
        f.unlink()

    cid = world(gui)
    ids = build(cid)

    lines = [
        "METHOD: contact force only + gravity",
        f"Gravity ALWAYS g=-{G} m/s^2",
        "Drive: kinematic eccentric cams (motor actuator)",
        "Followers/plates: DYNAMIC — lifted only by CONTACT normals with cams",
        "No P2P/joint force across air gap between cam and follower",
        "Bolted plates = FIXED to follower (permanent assembly contact)",
        "Demos: free_fall (gravity); pusher hits pushed (force only while contacting)",
        "",
    ]

    dt = 1 / 500.0
    steps = int(seconds / dt)
    omega = MOTOR_RPM * 2 * math.pi / 60.0
    every = max(1, int(0.05 / dt))
    fi = 0

    # time series
    samples = []
    fall_z0 = p.getBasePositionAndOrientation(ids["free_fall"], physicsClientId=cid)[0][2]

    set_drive_pose(cid, ids, 0.0)
    for _ in range(100):
        p.stepSimulation(physicsClientId=cid)

    for step in range(steps):
        t = step * dt
        ang = omega * t
        set_drive_pose(cid, ids, ang)
        set_pusher(cid, ids, t)
        p.stepSimulation(physicsClientId=cid)

        if step % 10 == 0:
            for tag in ("A", "B"):
                cam = ids[f"cam_{tag}"]
                fol = ids[f"follow_{tag}"]
                fn = contact_force(cid, cam, fol)
                gp = gap(cid, cam, fol)
                # Rule check: if clearly separated, force must be ~0
                samples.append(
                    {
                        "t": t,
                        "tag": tag,
                        "contact_N": fn,
                        "gap_m": gp,
                        "follow_z": p.getBasePositionAndOrientation(fol, physicsClientId=cid)[0][2],
                    }
                )
            pf = contact_force(cid, ids["pusher"], ids["pushed"])
            pg = gap(cid, ids["pusher"], ids["pushed"])
            samples.append({"t": t, "tag": "push", "contact_N": pf, "gap_m": pg})

        if save_frames and step % every == 0:
            capture(cid, FRAMES / f"frame_{fi:04d}.png")
            fi += 1

        if gui and step % 5 == 0:
            time.sleep(0.0005)

    # --- Analyze contact rule ---
    sep_with_force = 0
    touch_with_force = 0
    sep_ok = 0
    for s in samples:
        if s["tag"] == "push":
            continue
        if s["gap_m"] > 0.0015:  # >1.5 mm separated
            if s["contact_N"] > 0.05:
                sep_with_force += 1
            else:
                sep_ok += 1
        elif s["gap_m"] < 0.0005 and s["contact_N"] > 0.05:
            touch_with_force += 1

    # Push demo: max force when gap<=0 vs when separated
    push_sep_f = [s["contact_N"] for s in samples if s["tag"] == "push" and s["gap_m"] > 0.002]
    push_touch_f = [s["contact_N"] for s in samples if s["tag"] == "push" and s["gap_m"] < 0.0005]
    max_sep = max(push_sep_f) if push_sep_f else 0.0
    max_touch = max(push_touch_f) if push_touch_f else 0.0

    fall_z1 = p.getBasePositionAndOrientation(ids["free_fall"], physicsClientId=cid)[0][2]
    fell = (fall_z0 - fall_z1) > 0.03  # dropped >3 cm

    zA = [s["follow_z"] for s in samples if s["tag"] == "A"]
    zB = [s["follow_z"] for s in samples if s["tag"] == "B"]
    spanA = max(zA) - min(zA) if zA else 0
    spanB = max(zB) - min(zB) if zB else 0

    ok_contact_rule = sep_with_force == 0 and touch_with_force > 0
    ok_push = max_sep < 0.05 and max_touch > 0.2
    ok_gravity = fell
    ok_motion = spanA > 0.5 * ECC  # follower moves from cam contact

    lines += [
        f"Follower A Z span = {spanA*100:.2f} cm (cam contact lift)",
        f"Follower B Z span = {spanB*100:.2f} cm",
        f"Contact rule cam-follower: separated_samples_ok={sep_ok}, ILLEGAL_force_while_separated={sep_with_force}, touch_with_force={touch_with_force}",
        f"Push demo: max force when separated={max_sep:.3f} N, when touching={max_touch:.3f} N",
        f"Gravity free_fall: z0={fall_z0:.3f} -> z1={fall_z1:.3f} fell={fell}",
        f"PASS contact_rule={ok_contact_rule} push={ok_push} gravity={ok_gravity} lift={ok_motion}",
        "RESULT: " + ("PASS" if (ok_contact_rule and ok_push and ok_gravity and ok_motion) else "FAIL"),
    ]

    REVIEW.write_text("\n".join(lines), encoding="utf-8")
    METRICS.write_text(
        json.dumps(
            {
                "method": "pybullet_contact_only_plus_gravity",
                "gravity": -G,
                "follower_A_z_span_m": spanA,
                "follower_B_z_span_m": spanB,
                "illegal_force_while_separated": sep_with_force,
                "touch_with_force_samples": touch_with_force,
                "push_max_force_separated_N": max_sep,
                "push_max_force_touching_N": max_touch,
                "free_fall_delta_z_m": fall_z0 - fall_z1,
                "frames": fi,
                "pass": bool(ok_contact_rule and ok_push and ok_gravity and ok_motion),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print("\n".join(lines))
    print("Wrote", REVIEW)
    print("Wrote", METRICS)
    print("Frames", fi, FRAMES)

    if gui:
        print("GUI open — close window to exit")
        try:
            t = seconds
            while p.isConnected(physicsClientId=cid):
                t += dt
                set_drive_pose(cid, ids, omega * t)
                set_pusher(cid, ids, t)
                p.stepSimulation(physicsClientId=cid)
                time.sleep(1 / 300)
        except Exception:
            pass
    else:
        p.disconnect(physicsClientId=cid)

    return ok_contact_rule and ok_push and ok_gravity and ok_motion


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gui", action="store_true")
    ap.add_argument("--seconds", type=float, default=6.0)
    ap.add_argument("--no-frames", action="store_true")
    args = ap.parse_args()
    ok = run(gui=args.gui, seconds=args.seconds, save_frames=not args.no_frames)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
