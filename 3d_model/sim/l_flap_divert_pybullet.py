"""
L_Flap_Divert sim — aperture metering + yoke/pin flap drive (contact-only).

  Phase A (open 1→5): flap @ SMALL, aperture meters 5.5 mm lane
  Transit (5→~9): pin contact swings flap to LARGE
  Phase B (~9→21): flap @ LARGE, aperture meters 12 mm lane

  python 3d_model/sim/l_flap_divert_pybullet.py [--gui]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import pybullet as p
import pybullet_data

FREECAD = Path(__file__).resolve().parents[1] / "freecad"
sys.path.insert(0, str(FREECAD))
import l_flap_divert as CAD  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(parents=True, exist_ok=True)
METRICS = OUT / "l_flap_divert_metrics.json"

S = 0.001
G = 9.81
DT = 1.0 / 240.0


def M(*xyz):
    return [v * S for v in xyz]


def kin_box(cx, cy, cz, hx, hy, hz, rgba):
    col = p.createCollisionShape(p.GEOM_BOX, halfExtents=M(hx, hy, hz))
    vis = p.createVisualShape(p.GEOM_BOX, halfExtents=M(hx, hy, hz), rgbaColor=rgba)
    bid = p.createMultiBody(0, col, vis, M(cx, cy, cz))
    p.setCollisionFilterGroupMask(bid, -1, 1, 1)
    return bid


def make_cross_body(angle_deg: float):
    hub_z = CAD.ACT_Z0 + CAD.ACT_ARM_H / 2
    pin_half = CAD.DRIVE_PIN_D / 2
    pin_hh = 1.6
    pin_z_world = CAD.ACT_Z0 + CAD.ACT_ARM_H - 0.2 + pin_hh
    pin_dz = pin_z_world - hub_z
    half_h = CAD.ACT_ARM_H / 2
    half_w = CAD.ACT_ARM_W / 2
    half_a = CAD.ACT_ARM_A_L / 2
    half_b = CAD.ACT_ARM_B_L / 2

    # Include flap arms in collision so stop pads can catch them
    shape_types = [p.GEOM_BOX, p.GEOM_BOX, p.GEOM_BOX, p.GEOM_BOX]
    halfs = [
        M(1.2, 1.2, half_h),
        M(half_a, half_w, half_h),
        M(half_w, half_b, half_h),
        M(pin_half, pin_half, pin_hh),
    ]
    empty = [[], [], [], []]
    frames_pos = [
        [0, 0, 0],
        M(CAD.ACT_ARM_A_L / 2, 0, 0),
        M(0, CAD.ACT_ARM_B_L / 2, 0),
        M(0, -CAD.DRIVE_PIN_R, pin_dz),
    ]
    frames_orn = [[0, 0, 0, 1]] * 4

    col = p.createCollisionShapeArray(
        shapeTypes=shape_types,
        radii=empty,
        halfExtents=halfs,
        lengths=empty,
        collisionFramePositions=frames_pos,
        collisionFrameOrientations=frames_orn,
    )
    v_types = [p.GEOM_BOX] * 5
    v_halfs = [
        M(1.5, 1.5, half_h),
        M(half_a, half_w, half_h),
        M(half_w, half_b, half_h),
        M(half_w, max(0.4, (CAD.DRIVE_PIN_R - 0.5) / 2), half_h),
        M(pin_half, pin_half, pin_hh),
    ]
    v_empty = [[], [], [], [], []]
    v_pos = [
        [0, 0, 0],
        M(CAD.ACT_ARM_A_L / 2, 0, 0),
        M(0, CAD.ACT_ARM_B_L / 2, 0),
        M(0, -max(0.4, (CAD.DRIVE_PIN_R - 0.5) / 2), 0),
        M(0, -CAD.DRIVE_PIN_R, pin_dz),
    ]
    vis = p.createVisualShapeArray(
        shapeTypes=v_types,
        radii=v_empty,
        halfExtents=v_halfs,
        lengths=v_empty,
        visualFramePositions=v_pos,
        visualFrameOrientations=[[0, 0, 0, 1]] * 5,
        rgbaColors=[
            (0.25, 0.55, 0.9, 1),
            (0.95, 0.55, 0.15, 1),
            (0.2, 0.75, 0.95, 1),
            (0.95, 0.55, 0.15, 1),
            (0.95, 0.2, 0.2, 1),
        ],
    )

    body = p.createMultiBody(
        baseMass=0,
        baseCollisionShapeIndex=-1,
        baseVisualShapeIndex=-1,
        basePosition=[0, 0, 0],
        linkMasses=[0.045],
        linkCollisionShapeIndices=[col],
        linkVisualShapeIndices=[vis],
        linkPositions=[M(0, 0, hub_z)],
        linkOrientations=[[0, 0, 0, 1]],
        linkInertialFramePositions=[[0, 0, 0]],
        linkInertialFrameOrientations=[[0, 0, 0, 1]],
        linkParentIndices=[0],
        linkJointTypes=[p.JOINT_REVOLUTE],
        linkJointAxis=[[0, 0, 1]],
    )
    p.changeDynamics(
        body, 0,
        angularDamping=0.08, linearDamping=0.02, lateralFriction=0.95,
        spinningFriction=0.02, restitution=0.0, jointDamping=0.002,
    )
    p.resetJointState(body, 0, math.radians(angle_deg))
    return body


def slider_parts(open_mm: float):
    x_left = CAD.slider_x_left(open_mm)
    _xa, xb = CAD.lug_world_x(open_mm)
    bar_c = (x_left + CAD.SLIDER_LEN / 2, 0.0, CAD.SLIDER_Z0 + CAD.SLIDER_H / 2)
    bar_h = (CAD.SLIDER_LEN / 2, CAD.SLIDER_T / 2, CAD.SLIDER_H / 2)

    jaw_z0 = CAD.YOKE_H_Z0
    jaw_h = max(0.6, (CAD.SLIDER_Z0 + 0.2 - jaw_z0) / 2)
    jaw_cz = jaw_z0 + jaw_h
    jaw_cy = -CAD.DRIVE_PIN_R
    jaw_hy = CAD.LUG_DRIVE_T / 2
    jaws = [
        ((xb + CAD.LUG_DRIVE_W / 2, jaw_cy, jaw_cz), (CAD.LUG_DRIVE_W / 2, jaw_hy, jaw_h)),
    ]
    return bar_c, bar_h, jaws


def run(gui: bool) -> dict:
    p.connect(p.GUI if gui else p.DIRECT)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.resetSimulation()
    p.setGravity(0, 0, -G)
    p.setTimeStep(DT)
    p.setPhysicsEngineParameter(numSolverIterations=250, enableConeFriction=1)
    p.loadURDF("plane.urdf")
    kin_box(0, -10, CAD.FLOOR_T / 2, 40, 40, CAD.FLOOR_T / 2, (0.5, 0.52, 0.55, 0.3))

    # Hard angle stops as static blocks near flap arms (contact)
    kin_box(CAD.ARM_ROOT + CAD.ARM_LARGE_L, -0.5, CAD.L_Z0 + CAD.L_H / 2,
            1.0, 1.0, CAD.L_H / 3, (0.4, 0.4, 0.4, 1))
    kin_box(-0.5, CAD.ARM_ROOT + CAD.ARM_SMALL_L, CAD.L_Z0 + CAD.L_H / 2,
            1.0, 1.0, CAD.L_H / 3, (0.4, 0.4, 0.4, 1))

    probe_z0 = 0.08
    probe = p.createMultiBody(
        0.01,
        p.createCollisionShape(p.GEOM_SPHERE, radius=0.004),
        p.createVisualShape(p.GEOM_SPHERE, radius=0.004, rgbaColor=(0.2, 0.9, 0.3, 1)),
        [0.08, -0.06, probe_z0],
    )
    z_probe_start = p.getBasePositionAndOrientation(probe)[0][2]

    open0 = CAD.OPEN_SMALL_LO
    body = make_cross_body(CAD.flap_angle_for_open(open0))
    # Remove unreliable jointLimitForce — rely on stop pads + contact lugs
    p.changeDynamics(body, 0, angularDamping=0.08, jointDamping=0.002)

    bc, bh, jaws = slider_parts(open0)
    bar_id = kin_box(*bc, *bh, (0.55, 0.25, 0.7, 1))
    jaw_ids = [kin_box(*c, *h, (0.9, 0.15, 0.55, 1)) for c, h in jaws]

    def set_open(open_mm: float):
        bc, bh, jaws = slider_parts(open_mm)
        p.resetBasePositionAndOrientation(bar_id, M(*bc), [0, 0, 0, 1])
        for jid, (c, _h) in zip(jaw_ids, jaws):
            p.resetBasePositionAndOrientation(jid, M(*c), [0, 0, 0, 1])

    set_open(open0)
    for _ in range(100):
        p.stepSimulation()
    free_fall = max(0.0, z_probe_start - p.getBasePositionAndOrientation(probe)[0][2])

    lo, hi = CAD.OPEN_SMALL_LO, CAD.OPEN_LARGE_HI
    path = [lo + (hi - lo) * i / 200 for i in range(201)]
    path += [hi + (lo - hi) * i / 200 for i in range(201)]

    contacts = 0
    ghost = 0
    illegal = 0
    angles = []
    aperture_log = []
    prev_ang = p.getJointState(body, 0)[0]
    ang_at_small_end = None

    if gui:
        p.resetDebugVisualizerCamera(0.22, 30, -50, [0, 0.008, 0.015])

    for step, op in enumerate(path):
        set_open(op)
        for _ in range(5):
            p.stepSimulation()

        ang = p.getJointState(body, 0)[0]
        deg = math.degrees(ang)
        # Clamp runaway numerically for metrics if stop failed (still flag fail)
        n_c = sum(len(p.getContactPoints(jid, body)) for jid in jaw_ids)
        dang = abs(ang - prev_ang)
        in_transit = CAD.OPEN_TRANSIT_LO - 0.2 <= op <= CAD.OPEN_TRANSIT_HI + 0.2
        in_dwell = op < CAD.OPEN_TRANSIT_LO - 0.3 or op > CAD.OPEN_TRANSIT_HI + 0.5
        if n_c == 0 and dang > math.radians(0.5) and in_dwell and 1.5 < op < hi - 0.5:
            ghost += 1
        if n_c and in_transit:
            contacts += 1
        angles.append(deg)
        if step % 20 == 0:
            aperture_log.append(
                {"open": round(op, 2), **CAD.aperture_widths(op), "flap_deg": round(deg, 2)}
            )
        if ang_at_small_end is None and op >= CAD.OPEN_SMALL_HI - 0.05:
            ang_at_small_end = deg
        prev_ang = ang
        if gui and step % 2 == 0:
            time.sleep(DT * 0.2)

    amin, amax = min(angles), max(angles)
    delta = amax - amin

    w_lo = CAD.aperture_widths(CAD.OPEN_SMALL_LO)
    w_hi_s = CAD.aperture_widths(CAD.OPEN_SMALL_HI)
    w_lo_l = CAD.aperture_widths(CAD.OPEN_LARGE_LO)
    w_hi_l = CAD.aperture_widths(CAD.OPEN_LARGE_HI)
    aperture_ok = (
        w_lo["active"] == "SMALL"
        and w_hi_s["small_mm"] >= CAD.SMALL_GROOVE_W - 0.35
        and w_lo["small_mm"] < w_hi_s["small_mm"] - 0.8
        and w_hi_l["active"] == "LARGE"
        and w_hi_l["large_mm"] >= CAD.LARGE_GROOVE_W - 0.35
        and w_hi_l["large_mm"] > w_lo_l["large_mm"] + 2.0
        and w_hi_s["large_mm"] < 2.5
        and w_hi_l["small_mm"] < 2.5
    )

    large_reach = 60.0 <= amax <= 100.0
    no_overshoot = amax <= 100.0
    had = contacts > 8
    swung = delta > 45.0
    small_hold = ang_at_small_end is not None and ang_at_small_end < 15.0

    passed = bool(
        aperture_ok
        and small_hold
        and large_reach
        and no_overshoot
        and had
        and swung
        and ghost == 0
        and illegal == 0
        and free_fall > 0.0
    )

    metrics = {
        "pass": passed,
        "aperture_ok": aperture_ok,
        "aperture_small_band_mm": [w_lo["small_mm"], w_hi_s["small_mm"]],
        "aperture_large_band_mm": [w_lo_l["large_mm"], w_hi_l["large_mm"]],
        "small_hold_ok": small_hold,
        "ang_at_small_end_deg": None if ang_at_small_end is None else round(ang_at_small_end, 2),
        "had_lug_contact": had,
        "contact_steps_transit": contacts,
        "angle_min_deg": round(amin, 2),
        "angle_max_deg": round(amax, 2),
        "angle_delta_deg": round(delta, 2),
        "illegal_force_while_separated": illegal,
        "ghost_moves_without_contact": ghost,
        "gravity": -G,
        "free_fall_delta_z_m": round(free_fall, 5),
        "open_sweep_mm": [lo, round(hi, 3), lo],
        "open_bands": {
            "small": [CAD.OPEN_SMALL_LO, CAD.OPEN_SMALL_HI],
            "transit": [round(CAD.OPEN_TRANSIT_LO, 3), round(CAD.OPEN_TRANSIT_HI, 3)],
            "large": [round(CAD.OPEN_LARGE_LO, 3), round(CAD.OPEN_LARGE_HI, 3)],
        },
        "aperture_samples": aperture_log[:14],
        "mechanism": "aperture meters 5.5 then 12; short lugs contact-drive flap only in transit",
    }
    METRICS.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    print("Wrote", METRICS)

    if gui:
        try:
            while p.isConnected():
                time.sleep(0.05)
        except KeyboardInterrupt:
            pass
    p.disconnect()
    return metrics


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gui", action="store_true")
    args = ap.parse_args()
    run(args.gui)


if __name__ == "__main__":
    main()
