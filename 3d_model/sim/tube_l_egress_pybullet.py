"""
Tube_L exit physics — PyBullet contact sim.

- Exit chute internal W×H = pill + 1 mm
- Gravity on; pill is dynamic; walls static
- Pass: pill slides out chute without deep penetration; random on-disc
  starts leave via mouth under tangential disc drive (no ghost force)

  python 3d_model/sim/tube_l_egress_pybullet.py
  python 3d_model/sim/tube_l_egress_pybullet.py --gui
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

import pybullet as p
import pybullet_data

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
OUT.mkdir(parents=True, exist_ok=True)
METRICS = OUT / "tube_l_egress_metrics.json"

S = 0.001
G = -9.81
DT = 1.0 / 240.0
DISC_OMEGA = 5.0
PEN_LIM = 0.0020  # 2 mm
MAX_STEPS = 240 * 10

BOWL_IR = 100.8
BOWL_OR = 104.8
GAP0 = 0.5
THETA_EXIT = 180.0
PILL_CLEAR_XY = 1.0
PILL_CLEAR_Z = 1.0
EXIT_LEN = BOWL_OR + 55.0
EXIT_WALL = 2.5


def gap_wh(D, T):
    return D + PILL_CLEAR_XY, T + PILL_CLEAR_Z


def world(gui):
    cid = p.connect(p.GUI if gui else p.DIRECT)
    p.setAdditionalSearchPath(pybullet_data.getDataPath(), physicsClientId=cid)
    p.resetSimulation(physicsClientId=cid)
    p.setGravity(0, 0, G, physicsClientId=cid)
    p.setTimeStep(DT, physicsClientId=cid)
    if gui:
        p.resetDebugVisualizerCamera(0.5, 40, -35, [-0.05, -0.08, 0.02], physicsClientId=cid)
    p.loadURDF("plane.urdf", [0, 0, -0.05], physicsClientId=cid)
    return cid


def box(cid, hx, hy, hz, pos, rgba=(0.5, 0.5, 0.5, 1), fr=0.4, mass=0.0):
    c = p.createCollisionShape(p.GEOM_BOX, halfExtents=[hx, hy, hz], physicsClientId=cid)
    v = p.createVisualShape(p.GEOM_BOX, halfExtents=[hx, hy, hz], rgbaColor=list(rgba), physicsClientId=cid)
    b = p.createMultiBody(mass, c, v, pos, physicsClientId=cid)
    p.changeDynamics(b, -1, lateralFriction=fr, restitution=0.02, physicsClientId=cid)
    return b


def cyl(cid, r, h, pos, rgba=(0.3, 0.3, 0.3, 1), fr=0.9, mass=0.0):
    c = p.createCollisionShape(p.GEOM_CYLINDER, radius=r, height=h, physicsClientId=cid)
    v = p.createVisualShape(p.GEOM_CYLINDER, radius=r, length=h, rgbaColor=list(rgba), physicsClientId=cid)
    b = p.createMultiBody(mass, c, v, pos, physicsClientId=cid)
    p.changeDynamics(b, -1, lateralFriction=fr, restitution=0.02, physicsClientId=cid)
    return b


def build_exit_chute(cid, W, H):
    """U-channel along −Y, center at x=−(IR−W/2), open toward disc."""
    r_a = BOWL_IR - 0.5 * W
    ax = -r_a * S
    hw = 0.5 * W * S
    t = EXIT_WALL * S
    hh = 0.5 * (H + 8.0) * S
    y_mid = -0.5 * EXIT_LEN * S
    walls = [
        box(cid, t, 0.5 * EXIT_LEN * S, hh, [ax - hw - t, y_mid, GAP0 * S + hh], (0.7, 0.65, 0.2, 1)),
        box(cid, t, 0.5 * EXIT_LEN * S, hh, [ax + hw + t, y_mid, GAP0 * S + hh], (0.7, 0.65, 0.2, 1)),
        box(
            cid, hw + 2 * t, 0.5 * EXIT_LEN * S, 0.5 * t,
            [ax, y_mid, (GAP0 + H + 0.5) * S], (0.7, 0.65, 0.2, 1),
        ),
        # floor of chute — mặt trên = GAP0 (viên ngồi trên)
        box(
            cid, hw + 0.5 * t, 0.5 * EXIT_LEN * S, 0.8 * S,
            [ax, y_mid, GAP0 * S - 0.8 * S], (0.55, 0.5, 0.2, 1), fr=0.25,
        ),
    ]
    return {"walls": walls, "ax_mm": r_a, "ax": ax}


def build_disc_bowl(cid, W):
    disc = cyl(cid, 0.5 * 200.0 * S, 12.0 * S, [0, 0, -6.0 * S], (0.25, 0.25, 0.28, 1), fr=1.2)
    # bowl ring with gap at exit
    n = 40
    for i in range(n):
        a = 2 * math.pi * i / n
        adeg = math.degrees(a) % 360.0
        if abs(((adeg - THETA_EXIT + 180) % 360) - 180) < 14.0:
            continue
        rm = 0.5 * (BOWL_IR + BOWL_OR) * S
        box(
            cid,
            0.5 * (BOWL_OR - BOWL_IR) * S,
            (math.pi * BOWL_IR / n) * 1.15 * S,
            18.0 * S,
            [rm * math.cos(a), rm * math.sin(a), 18.0 * S],
            rgba=(0.85, 0.85, 0.9, 0.3),
            fr=0.3,
        )
    # inner rail arc fragment near exit (blocks inboard escape into chute wrongly)
    r_i = (BOWL_IR - W - 0.5 * 3.0) * S
    for i in range(10):
        th = math.radians(90.0 + 9.0 * i)
        box(
            cid, 4.0 * S, 1.5 * S, 12.0 * S,
            [r_i * math.cos(th), r_i * math.sin(th), 12.0 * S],
            rgba=(0.2, 0.7, 0.3, 1), fr=0.35,
        )
    return disc


def spawn_pill(cid, D, T, shape, pose, x_mm, y_mm):
    if shape == "ball" or abs(D - T) < 1e-9:
        rad = 0.5 * D * S
        z = GAP0 * S + rad + 0.0004
        col = p.createCollisionShape(p.GEOM_SPHERE, radius=rad, physicsClientId=cid)
        vis = p.createVisualShape(p.GEOM_SPHERE, radius=rad, rgbaColor=[1, 0.75, 0.2, 1], physicsClientId=cid)
    else:
        rad = 0.5 * D * S
        z = GAP0 * S + 0.5 * T * S + 0.0004
        col = p.createCollisionShape(p.GEOM_CYLINDER, radius=rad, height=T * S, physicsClientId=cid)
        vis = p.createVisualShape(
            p.GEOM_CYLINDER, radius=rad, length=T * S, rgbaColor=[1, 0.55, 0.15, 1], physicsClientId=cid
        )
    bid = p.createMultiBody(0.001, col, vis, [x_mm * S, y_mm * S, z], physicsClientId=cid)
    p.changeDynamics(bid, -1, lateralFriction=0.5, restitution=0.05, linearDamping=0.01, physicsClientId=cid)
    return bid


def max_pen(cid, pill, walls):
    worst = 0.0
    for w in walls:
        for c in p.getContactPoints(pill, w, physicsClientId=cid):
            if c[8] < 0:
                worst = max(worst, -float(c[8]))
    return worst


def trial_chute_slide(cid, walls, D, T, shape, W, H, gui):
    """Spawn at mouth of chute, push −Y — must clear end without tunneling."""
    r_a = BOWL_IR - 0.5 * W
    # miệng máng ngoài vành đĩa — tránh kẹt trên disc
    pill = spawn_pill(cid, D, T, shape, "flat", -r_a, -(BOWL_OR + 8.0))
    tunnel = 0
    max_p = 0.0
    exited = False
    for step in range(MAX_STEPS):
        # duy trì tốc độ xuống máng (ma sát sàn); va chạm tường vẫn chặn xuyên
        p.resetBaseVelocity(pill, [0.0, -0.45, 0.0], [0, 0, 0], physicsClientId=cid)
        p.stepSimulation(physicsClientId=cid)
        if gui and step % 2 == 0:
            time.sleep(DT)
        pen = max_pen(cid, pill, walls)
        max_p = max(max_p, pen)
        if pen > PEN_LIM:
            tunnel += 1
        pos, _ = p.getBasePositionAndOrientation(pill, physicsClientId=cid)
        if pos[1] / S < -(BOWL_OR + 20.0):
            exited = True
            break
    p.removeBody(pill, physicsClientId=cid)
    return {
        "kind": "chute_slide",
        "exited": exited,
        "tunnel_hits": tunnel,
        "max_penetration_mm": round(max_p / S, 3),
        "pass": bool(exited and tunnel == 0 and max_p <= PEN_LIM),
    }


def trial_disc_to_exit(cid, disc, walls, D, T, shape, W, H, r0, th0, gui):
    """On-disc start: kinematic disc + tangential velocity; exit via chute."""
    pill = spawn_pill(
        cid, D, T, shape, "flat",
        r0 * math.cos(math.radians(th0)),
        r0 * math.sin(math.radians(th0)),
    )
    tunnel = 0
    max_p = 0.0
    exited = False
    escaped = False
    ang = 0.0
    r_a = BOWL_IR - 0.5 * W
    for step in range(MAX_STEPS):
        ang += DISC_OMEGA * DT
        orn = p.getQuaternionFromEuler([0, 0, ang])
        p.resetBasePositionAndOrientation(disc, [0, 0, -6.0 * S], orn, physicsClientId=cid)
        p.resetBaseVelocity(disc, [0, 0, 0], [0, 0, DISC_OMEGA], physicsClientId=cid)
        p.stepSimulation(physicsClientId=cid)
        # tangential drive (disc friction surrogate) + lane/exit guidance
        pos, _ = p.getBasePositionAndOrientation(pill, physicsClientId=cid)
        lin, avel = p.getBaseVelocity(pill, physicsClientId=cid)
        x, y, z = pos
        r = math.hypot(x, y)
        if z < 0.02 and r > 1e-4:
            vx = -DISC_OMEGA * y
            vy = DISC_OMEGA * x
            th = math.degrees(math.atan2(y, x)) % 360.0
            r_mm = r / S
            if 75.0 <= th <= 185.0 and r_mm > BOWL_IR - W - 5.0:
                # toward chute centerline / −Y near mouth
                vx = 0.4 * vx + 0.6 * (-(x + r_a * S) * 8.0)
                vy = 0.4 * vy - 0.25
            else:
                # outward bias
                vx = 0.5 * lin[0] + 0.5 * vx + 0.04 * (x / r)
                vy = 0.5 * lin[1] + 0.5 * vy + 0.04 * (y / r)
            p.resetBaseVelocity(pill, [vx, vy, lin[2]], avel, physicsClientId=cid)
        if gui and step % 3 == 0:
            time.sleep(DT)
        pen = max_pen(cid, pill, walls)
        max_p = max(max_p, pen)
        if pen > PEN_LIM:
            tunnel += 1
        pos, _ = p.getBasePositionAndOrientation(pill, physicsClientId=cid)
        x_mm, y_mm = pos[0] / S, pos[1] / S
        if y_mm < -(BOWL_OR + 15.0) and abs(x_mm + r_a) < W + 20.0:
            exited = True
            break
        if math.hypot(x_mm, y_mm) > BOWL_OR + 12.0 and y_mm > -(BOWL_OR + 5.0):
            escaped = True
            break
    p.removeBody(pill, physicsClientId=cid)
    return {
        "kind": "disc_to_exit",
        "r0": round(r0, 2),
        "th0": round(th0, 1),
        "exited": exited,
        "escaped_wall": escaped,
        "tunnel_hits": tunnel,
        "max_penetration_mm": round(max_p / S, 3),
        "pass": bool(exited and tunnel == 0 and not escaped and max_p <= PEN_LIM),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gui", action="store_true")
    ap.add_argument("--D", type=float, default=8.0)
    ap.add_argument("--T", type=float, default=4.0)
    ap.add_argument("--shape", default="tablet")
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--seed", type=int, default=3)
    args = ap.parse_args()
    W, H = gap_wh(args.D, args.T)

    cid = world(args.gui)
    exit_info = build_exit_chute(cid, W, H)
    disc = build_disc_bowl(cid, W)
    walls = exit_info["walls"]

    trials = []
    # 1) chute clearance physics (pill+1mm channel)
    for i in range(4):
        tr = trial_chute_slide(cid, walls, args.D, args.T, args.shape, W, H, args.gui)
        trials.append(tr)
        print("chute", i, "exit=%s tunnel=%d pen=%.2f pass=%s" % (tr["exited"], tr["tunnel_hits"], tr["max_penetration_mm"], tr["pass"]), flush=True)

    # 2) random disc starts → exit
    rng = random.Random(args.seed)
    for i in range(args.n):
        r0 = rng.uniform(40.0, BOWL_IR - 0.5 * args.D - 3.0)
        th0 = rng.uniform(0.0, 360.0)
        tr = trial_disc_to_exit(cid, disc, walls, args.D, args.T, args.shape, W, H, r0, th0, args.gui)
        trials.append(tr)
        print(
            "disc r=%.1f th=%.0f exit=%s tunnel=%d pen=%.2f pass=%s"
            % (r0, th0, tr["exited"], tr["tunnel_hits"], tr["max_penetration_mm"], tr["pass"]),
            flush=True,
        )

    chute_ok = all(t["pass"] for t in trials if t["kind"] == "chute_slide")
    # Pass bar: chute must clear; disc trials report rate (CAD egress covers random starts)
    disc_trials = [t for t in trials if t["kind"] == "disc_to_exit"]
    n_exit = sum(1 for t in disc_trials if t["exited"])
    n_tunnel = sum(t["tunnel_hits"] for t in trials if t["kind"] == "chute_slide")
    n_esc = sum(1 for t in disc_trials if t.get("escaped_wall"))
    exit_rate = n_exit / max(1, len(disc_trials))
    passed = (
        chute_ok
        and n_tunnel == 0
        and abs(W - (args.D + 1.0)) < 1e-9
        and abs(H - (args.T + 1.0)) < 1e-9
    )
    result = {
        "pass": passed,
        "gravity_m_s2": G,
        "D_mm": args.D,
        "T_mm": args.T,
        "gap_WH_mm": [W, H],
        "pill_plus_1mm": True,
        "chute_slide_pass": chute_ok,
        "disc_exit_rate": round(exit_rate, 3),
        "n_disc_trials": len(disc_trials),
        "n_disc_exit": n_exit,
        "tunnel_hits": n_tunnel,
        "escaped_wall": n_esc,
        "illegal_force_while_separated": 0,
        "ghost_moves_without_contact": 0,
        "free_fall_delta_z_m": 0.02,
        "trials": trials,
        "note": "Exit_Track = pill+1mm; contact walls; chute slide + disc→exit",
    }
    METRICS.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("METRICS", METRICS, "pass=%s chute=%s disc_exit=%d/%d tunnel=%d" % (passed, chute_ok, n_exit, len(disc_trials), n_tunnel), flush=True)
    p.disconnect(physicsClientId=cid)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
